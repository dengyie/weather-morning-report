const { loadConfiguration } = require('../storage/configuration-store')
const { localDateKey, localTimeKey } = require('./time')
const { loadSchedulerState, saveSchedulerState } = require('./state-store')

const WORKER_LEASE_MS = 90 * 1000
const JOB_LEASE_MS = 5 * 60 * 1000
const RETRY_DELAYS_MS = [5, 15, 30, 60].map((minutes) => minutes * 60 * 1000)

const iso = (date) => date.toISOString()
const parseTime = (value) => new Date(value).getTime()

const nextJobId = (jobs) => `job-${jobs.reduce((max, job) => {
  const match = /^job-(\d+)$/.exec(job.id || '')
  return Math.max(max, match ? Number(match[1]) : 0)
}, 0) + 1}`

const findRecipient = (configuration, recipientId) => configuration.recipients
  .find((recipient) => recipient.id === recipientId && recipient.enabled !== false && !recipient.archivedAt)

const automaticDedupeKey = ({ recipient, schedule, localReportDate }) => `automatic:${recipient.id}:${schedule.id}:${schedule.reportType}:${localReportDate}`

const localScheduleKeys = (now, timezone) => {
  try {
    return {
      date: localDateKey(now, timezone),
      time: localTimeKey(now, timezone)
    }
  } catch (error) {
    if (error instanceof RangeError) return null
    throw error
  }
}

const redactSchedulerError = (message, secrets = []) => {
  let redacted = String(message || '')
  for (const secret of secrets.filter(Boolean)) {
    redacted = redacted.split(String(secret)).join('[redacted]')
  }
  return redacted.replace(/password=[^\s&]+/gi, 'password=[redacted]')
}

const statusCounts = (jobs) => {
  const counts = {
    pending: 0,
    running: 0,
    retrying: 0,
    sent: 0,
    skipped: 0,
    failed: 0,
    unknown: 0
  }
  for (const job of jobs) {
    if (job.status === 'delivery_result_unknown') counts.unknown += 1
    else if (Object.hasOwn(counts, job.status)) counts[job.status] += 1
  }
  return counts
}

const queueStatus = (paths, { now = new Date() } = {}) => {
  const state = loadSchedulerState(paths)
  const lease = state.workerLease
  const workerActive = Boolean(lease && parseTime(lease.expiresAt) > now.getTime())
  return {
    ...statusCounts(state.jobs),
    total: state.jobs.length,
    workerActive,
    workerInstanceId: workerActive ? lease.instanceId : null,
    workerHeartbeatAt: lease?.heartbeatAt || null
  }
}

const enqueueDueJobs = (paths, { now = new Date() } = {}) => {
  const configuration = loadConfiguration(paths)
  const state = loadSchedulerState(paths)
  let created = 0
  for (const schedule of configuration.schedules) {
    if (schedule.enabled === false || schedule.archivedAt) continue
    const recipient = findRecipient(configuration, schedule.recipientId)
    if (!recipient) continue
    const localKeys = localScheduleKeys(now, recipient.timezone)
    if (!localKeys || localKeys.time !== schedule.localSendTime) continue
    const localReportDate = localKeys.date
    const dedupeKey = automaticDedupeKey({ recipient, schedule, localReportDate })
    if (state.jobs.some((job) => job.dedupeKey === dedupeKey)) continue
    state.jobs.push({
      id: nextJobId(state.jobs),
      kind: 'automatic',
      status: 'pending',
      recipientId: recipient.id,
      scheduleId: schedule.id,
      reportType: schedule.reportType,
      sendPolicy: schedule.sendPolicy,
      localReportDate,
      dedupeKey,
      scheduledAt: iso(now),
      availableAt: iso(now),
      attemptCount: 0,
      leaseOwner: null,
      leaseExpiresAt: null,
      lastErrorCode: null,
      lastErrorMessage: null
    })
    created += 1
  }
  if (created) saveSchedulerState(paths, state)
  return created
}

const acquireWorkerLease = (paths, instanceId, { now = new Date() } = {}) => {
  const state = loadSchedulerState(paths)
  const lease = state.workerLease
  if (lease && lease.instanceId !== instanceId && parseTime(lease.expiresAt) > now.getTime()) {
    return false
  }
  state.workerLease = {
    instanceId,
    acquiredAt: lease?.instanceId === instanceId ? lease.acquiredAt : iso(now),
    heartbeatAt: iso(now),
    expiresAt: iso(new Date(now.getTime() + WORKER_LEASE_MS))
  }
  saveSchedulerState(paths, state)
  return true
}

const renewWorkerLease = (paths, instanceId, { now = new Date() } = {}) => {
  const state = loadSchedulerState(paths)
  const lease = state.workerLease
  if (!lease || lease.instanceId !== instanceId || parseTime(lease.expiresAt) <= now.getTime()) return false
  lease.heartbeatAt = iso(now)
  lease.expiresAt = iso(new Date(now.getTime() + WORKER_LEASE_MS))
  saveSchedulerState(paths, state)
  return true
}

const releaseWorkerLease = (paths, instanceId) => {
  const state = loadSchedulerState(paths)
  if (state.workerLease?.instanceId === instanceId) {
    state.workerLease = null
    saveSchedulerState(paths, state)
  }
}

const claimable = (job, now) => (
  (job.status === 'pending' || job.status === 'retrying') && parseTime(job.availableAt) <= now.getTime()
) || (
  job.status === 'running' && job.leaseExpiresAt && parseTime(job.leaseExpiresAt) <= now.getTime()
)

const claimJob = (paths, instanceId, { now = new Date() } = {}) => {
  const state = loadSchedulerState(paths)
  const job = state.jobs
    .filter((item) => claimable(item, now))
    .sort((left, right) => parseTime(left.availableAt) - parseTime(right.availableAt) || left.id.localeCompare(right.id))[0]
  if (!job) return null
  job.status = 'running'
  job.attemptCount = Number(job.attemptCount || 0) + 1
  job.leaseOwner = instanceId
  job.leaseExpiresAt = iso(new Date(now.getTime() + JOB_LEASE_MS))
  saveSchedulerState(paths, state)
  return { ...job }
}

const ownedJob = (state, jobId, instanceId, statuses) => {
  const job = state.jobs.find((item) => item.id === jobId)
  if (!job || job.leaseOwner !== instanceId || !statuses.includes(job.status)) {
    throw new Error('job is not owned by this worker')
  }
  return job
}

const beginDelivery = (paths, jobId, instanceId, { now = new Date() } = {}) => {
  const state = loadSchedulerState(paths)
  const job = ownedJob(state, jobId, instanceId, ['running'])
  job.status = 'dispatching'
  job.updatedAt = iso(now)
  saveSchedulerState(paths, state)
}

const completeJob = (paths, jobId, instanceId, { status = 'sent', now = new Date() } = {}) => {
  if (!['sent', 'skipped'].includes(status)) throw new Error('completed job status must be sent or skipped')
  const state = loadSchedulerState(paths)
  const job = ownedJob(state, jobId, instanceId, ['running', 'dispatching'])
  job.status = status
  job.leaseOwner = null
  job.leaseExpiresAt = null
  job.updatedAt = iso(now)
  saveSchedulerState(paths, state)
}

const failJob = (paths, jobId, instanceId, { errorCode, errorMessage, secrets = [], now = new Date() } = {}) => {
  const state = loadSchedulerState(paths)
  const job = ownedJob(state, jobId, instanceId, ['running', 'dispatching'])
  job.lastErrorCode = errorCode
  job.lastErrorMessage = redactSchedulerError(errorMessage, secrets)
  job.leaseOwner = null
  job.leaseExpiresAt = null
  if (job.status === 'dispatching') {
    job.status = 'delivery_result_unknown'
  } else {
    const retryIndex = Number(job.attemptCount || 1) - 1
    const delay = RETRY_DELAYS_MS[retryIndex]
    if (delay == null) {
      job.status = 'failed'
    } else {
      job.status = 'retrying'
      job.availableAt = iso(new Date(now.getTime() + delay))
    }
  }
  job.updatedAt = iso(now)
  saveSchedulerState(paths, state)
  return job.status
}

const failUncertainDeliveries = (paths, { now = new Date() } = {}) => {
  const state = loadSchedulerState(paths)
  let count = 0
  for (const job of state.jobs) {
    if (job.status === 'dispatching' && job.leaseExpiresAt && parseTime(job.leaseExpiresAt) <= now.getTime()) {
      job.status = 'delivery_result_unknown'
      job.lastErrorCode = 'delivery_result_unknown'
      job.lastErrorMessage = 'worker stopped after delivery began; automatic resend was suppressed'
      job.leaseOwner = null
      job.leaseExpiresAt = null
      job.updatedAt = iso(now)
      count += 1
    }
  }
  if (count) saveSchedulerState(paths, state)
  return count
}

module.exports = {
  JOB_LEASE_MS,
  RETRY_DELAYS_MS,
  WORKER_LEASE_MS,
  acquireWorkerLease,
  beginDelivery,
  claimJob,
  completeJob,
  enqueueDueJobs,
  failJob,
  failUncertainDeliveries,
  queueStatus,
  releaseWorkerLease,
  renewWorkerLease
}
