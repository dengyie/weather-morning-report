const { existsSync, mkdirSync, readFileSync, writeFileSync } = require('node:fs')
const path = require('node:path')

const DEFAULT_SMTP_OPERATION_HISTORY_LIMIT = 50

const smtpOperationHistoryPath = (paths) => path.join(paths.dataDir, 'smtp-operation-history.json')

const loadSmtpOperationHistory = (paths) => {
  const file = smtpOperationHistoryPath(paths)
  if (!existsSync(file)) return []
  const records = JSON.parse(readFileSync(file, 'utf8'))
  return Array.isArray(records) ? records : []
}

const saveSmtpOperationHistory = (paths, records) => {
  mkdirSync(paths.dataDir, { recursive: true })
  writeFileSync(smtpOperationHistoryPath(paths), `${JSON.stringify(records, null, 2)}\n`)
}

const appendSmtpOperationHistory = (paths, record, options = {}) => {
  const limit = Number.isInteger(options.limit) && options.limit > 0
    ? options.limit
    : DEFAULT_SMTP_OPERATION_HISTORY_LIMIT
  const records = loadSmtpOperationHistory(paths).concat(record).slice(-limit)
  saveSmtpOperationHistory(paths, records)
  return records
}

module.exports = {
  DEFAULT_SMTP_OPERATION_HISTORY_LIMIT,
  appendSmtpOperationHistory,
  loadSmtpOperationHistory,
  saveSmtpOperationHistory,
  smtpOperationHistoryPath
}
