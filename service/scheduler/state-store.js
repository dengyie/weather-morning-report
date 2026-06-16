const { existsSync, mkdirSync, readFileSync, writeFileSync } = require('node:fs')
const path = require('node:path')

const SCHEDULER_STATE_LIMIT = 500

const schedulerStatePath = (paths) => path.join(paths.dataDir, 'scheduler-state.json')

const createDefaultSchedulerState = () => ({
  schemaVersion: 1,
  jobs: [],
  workerLease: null
})

const mergeSchedulerState = (state = {}) => {
  const defaults = createDefaultSchedulerState()
  const jobs = Array.isArray(state.jobs) ? state.jobs.slice(-SCHEDULER_STATE_LIMIT) : defaults.jobs
  return {
    ...defaults,
    ...state,
    schemaVersion: 1,
    jobs,
    workerLease: state.workerLease || null
  }
}

const loadSchedulerState = (paths) => {
  const file = schedulerStatePath(paths)
  if (!existsSync(file)) return createDefaultSchedulerState()
  return mergeSchedulerState(JSON.parse(readFileSync(file, 'utf8')))
}

const saveSchedulerState = (paths, state) => {
  mkdirSync(paths.dataDir, { recursive: true })
  const merged = mergeSchedulerState(state)
  writeFileSync(schedulerStatePath(paths), `${JSON.stringify(merged, null, 2)}\n`)
  return merged
}

module.exports = {
  SCHEDULER_STATE_LIMIT,
  createDefaultSchedulerState,
  loadSchedulerState,
  saveSchedulerState,
  schedulerStatePath
}
