const { existsSync, mkdtempSync, rmSync } = require('node:fs')
const { tmpdir } = require('node:os')
const path = require('node:path')
const { test } = require('node:test')
const assert = require('node:assert/strict')

const { localDateKey, localTimeKey } = require('../service/scheduler/time')
const { createDefaultConfiguration } = require('../service/configuration/defaults')
const { saveConfiguration } = require('../service/storage/configuration-store')
const { createDefaultSchedulerState, loadSchedulerState, saveSchedulerState, schedulerStatePath } = require('../service/scheduler/state-store')
const {
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
} = require('../service/scheduler/queue')

const withTempServiceDirs = async (runner) => {
  const root = mkdtempSync(path.join(tmpdir(), 'wmr-scheduler-'))
  try {
    const paths = {
      dataDir: path.join(root, 'data'),
      cacheDir: path.join(root, 'cache'),
      logDir: path.join(root, 'logs')
    }
    await runner(paths)
  } finally {
    rmSync(root, { force: true, recursive: true })
  }
}

const seedScheduledConfiguration = (paths, overrides = {}) => {
  const configuration = createDefaultConfiguration()
  configuration.recipients = [{
    id: 'recipient-1',
    name: 'Alice',
    email: 'alice@example.com',
    locationName: 'Shanghai',
    locationQuery: 'Shanghai',
    timezone: overrides.timezone || 'Asia/Shanghai',
    language: 'zh-CN',
    emailTemplate: '1',
    enabled: true
  }]
  configuration.schedules = [{
    id: 'schedule-1',
    recipientId: 'recipient-1',
    localSendTime: overrides.localSendTime || '08:30',
    reportType: 'morning',
    sendPolicy: overrides.sendPolicy || 'always',
    enabled: true
  }]
  saveConfiguration(paths, configuration)
  return configuration
}

test('scheduler time helpers calculate local date and minute keys', () => {
  const now = new Date('2026-06-08T00:30:00.000Z')
  assert.equal(localDateKey(now, 'Asia/Shanghai'), '2026-06-08')
  assert.equal(localTimeKey(now, 'Asia/Shanghai'), '08:30')
  assert.equal(localDateKey(now, 'UTC'), '2026-06-08')
  assert.equal(localTimeKey(now, 'UTC'), '00:30')
})

test('scheduler state store loads defaults and writes bounded jobs', async () => {
  await withTempServiceDirs(async (paths) => {
    assert.deepEqual(loadSchedulerState(paths), createDefaultSchedulerState())
    const state = createDefaultSchedulerState()
    state.jobs = [{ id: 'job-1', status: 'pending' }]
    saveSchedulerState(paths, state)

    assert.equal(existsSync(schedulerStatePath(paths)), true)
    assert.deepEqual(loadSchedulerState(paths).jobs.map((job) => job.id), ['job-1'])
  })
})

test('enqueueDueJobs creates one automatic job per local date and suppresses duplicates', async () => {
  await withTempServiceDirs(async (paths) => {
    seedScheduledConfiguration(paths)
    const now = new Date('2026-06-08T00:30:00.000Z')

    assert.equal(enqueueDueJobs(paths, { now }), 1)
    assert.equal(enqueueDueJobs(paths, { now: new Date('2026-06-08T00:30:30.000Z') }), 0)

    const state = loadSchedulerState(paths)
    assert.equal(state.jobs.length, 1)
    assert.equal(state.jobs[0].kind, 'automatic')
    assert.equal(state.jobs[0].dedupeKey, 'automatic:recipient-1:schedule-1:morning:2026-06-08')
    assert.equal(state.jobs[0].localReportDate, '2026-06-08')
    assert.equal(queueStatus(paths, { now }).pending, 1)
  })
})

test('enqueueDueJobs does not backfill missed schedule minutes', async () => {
  await withTempServiceDirs(async (paths) => {
    seedScheduledConfiguration(paths)
    assert.equal(enqueueDueJobs(paths, { now: new Date('2026-06-08T00:32:00.000Z') }), 0)
    assert.equal(loadSchedulerState(paths).jobs.length, 0)
  })
})

test('enqueueDueJobs skips recipients with invalid timezones instead of crashing', async () => {
  await withTempServiceDirs(async (paths) => {
    seedScheduledConfiguration(paths, { timezone: 'Mars/Olympus' })

    assert.equal(enqueueDueJobs(paths, { now: new Date('2026-06-08T00:30:00.000Z') }), 0)
    assert.equal(loadSchedulerState(paths).jobs.length, 0)
  })
})

test('worker leases block active competitors and allow expired takeover', async () => {
  await withTempServiceDirs(async (paths) => {
    const now = new Date('2026-06-08T00:30:00.000Z')

    assert.equal(acquireWorkerLease(paths, 'worker-a', { now }), true)
    assert.equal(acquireWorkerLease(paths, 'worker-b', { now }), false)
    assert.equal(renewWorkerLease(paths, 'worker-a', { now: new Date('2026-06-08T00:31:00.000Z') }), true)
    assert.equal(acquireWorkerLease(paths, 'worker-b', { now: new Date('2026-06-08T00:34:00.000Z') }), true)
    assert.equal(renewWorkerLease(paths, 'worker-a', { now: new Date('2026-06-08T00:34:00.000Z') }), false)
    releaseWorkerLease(paths, 'worker-b')
    assert.equal(queueStatus(paths, { now }).workerActive, false)
  })
})

test('claimJob recovers expired running leases before delivery begins', async () => {
  await withTempServiceDirs(async (paths) => {
    seedScheduledConfiguration(paths)
    enqueueDueJobs(paths, { now: new Date('2026-06-08T00:30:00.000Z') })

    const first = claimJob(paths, 'worker-a', { now: new Date('2026-06-08T00:30:00.000Z') })
    assert.equal(first.id, 'job-1')
    assert.equal(first.attemptCount, 1)
    assert.equal(claimJob(paths, 'worker-b', { now: new Date('2026-06-08T00:31:00.000Z') }), null)
    const recovered = claimJob(paths, 'worker-b', { now: new Date('2026-06-08T00:36:00.000Z') })
    assert.equal(recovered.id, 'job-1')
    assert.equal(recovered.attemptCount, 2)
    completeJob(paths, 'job-1', 'worker-b', { status: 'sent', now: new Date('2026-06-08T00:37:00.000Z') })
    assert.equal(queueStatus(paths, { now: new Date('2026-06-08T00:37:00.000Z') }).sent, 1)
  })
})

test('failJob applies bounded retry delays then fails permanently', async () => {
  await withTempServiceDirs(async (paths) => {
    seedScheduledConfiguration(paths)
    enqueueDueJobs(paths, { now: new Date('2026-06-08T00:30:00.000Z') })
    const delayMinutes = [5, 15, 30, 60]
    let current = new Date('2026-06-08T00:30:00.000Z')

    for (const delay of delayMinutes) {
      const claimed = claimJob(paths, 'worker-a', { now: current })
      assert.equal(failJob(paths, claimed.id, 'worker-a', {
        errorCode: 'offline',
        errorMessage: 'provider unavailable',
        now: current
      }), 'retrying')
      current = new Date(current.getTime() + delay * 60 * 1000)
    }

    const finalClaim = claimJob(paths, 'worker-a', { now: current })
    assert.equal(failJob(paths, finalClaim.id, 'worker-a', {
      errorCode: 'offline',
      errorMessage: 'provider unavailable',
      now: current
    }), 'failed')
    const stored = loadSchedulerState(paths).jobs[0]
    assert.equal(stored.status, 'failed')
    assert.equal(stored.attemptCount, 5)
  })
})

test('failJob redacts secrets and password query values before storing errors', async () => {
  await withTempServiceDirs(async (paths) => {
    seedScheduledConfiguration(paths)
    enqueueDueJobs(paths, { now: new Date('2026-06-08T00:30:00.000Z') })
    const claimed = claimJob(paths, 'worker-a', { now: new Date('2026-06-08T00:30:00.000Z') })

    failJob(paths, claimed.id, 'worker-a', {
      errorCode: 'smtp_auth_failed',
      errorMessage: 'SMTP rejected password=hunter2 token super-secret-token',
      secrets: ['super-secret-token'],
      now: new Date('2026-06-08T00:30:00.000Z')
    })

    const stored = loadSchedulerState(paths).jobs[0]
    assert.equal(stored.lastErrorMessage, 'SMTP rejected password=[redacted] token [redacted]')
  })
})

test('expired dispatching jobs become delivery_result_unknown and are not claimed again', async () => {
  await withTempServiceDirs(async (paths) => {
    seedScheduledConfiguration(paths)
    enqueueDueJobs(paths, { now: new Date('2026-06-08T00:30:00.000Z') })
    const claimed = claimJob(paths, 'worker-a', { now: new Date('2026-06-08T00:30:00.000Z') })
    beginDelivery(paths, claimed.id, 'worker-a', { now: new Date('2026-06-08T00:31:00.000Z') })

    assert.equal(failUncertainDeliveries(paths, { now: new Date('2026-06-08T00:37:00.000Z') }), 1)
    assert.equal(claimJob(paths, 'worker-b', { now: new Date('2026-06-08T00:37:00.000Z') }), null)
    const status = queueStatus(paths, { now: new Date('2026-06-08T00:37:00.000Z') })
    assert.equal(status.unknown, 1)
    assert.equal(loadSchedulerState(paths).jobs[0].lastErrorCode, 'delivery_result_unknown')
  })
})
