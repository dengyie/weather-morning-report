const { existsSync, mkdirSync, readFileSync, writeFileSync } = require('node:fs')
const path = require('node:path')

const DEFAULT_DELIVERY_HISTORY_LIMIT = 100

const deliveryHistoryPath = (paths) => path.join(paths.dataDir, 'delivery-history.json')

const loadDeliveryHistory = (paths) => {
  const file = deliveryHistoryPath(paths)
  if (!existsSync(file)) return []
  const records = JSON.parse(readFileSync(file, 'utf8'))
  return Array.isArray(records) ? records : []
}

const saveDeliveryHistory = (paths, records) => {
  mkdirSync(paths.dataDir, { recursive: true })
  writeFileSync(deliveryHistoryPath(paths), `${JSON.stringify(records, null, 2)}\n`)
}

const appendDeliveryHistory = (paths, record, options = {}) => {
  const limit = Number.isInteger(options.limit) && options.limit > 0
    ? options.limit
    : DEFAULT_DELIVERY_HISTORY_LIMIT
  const records = loadDeliveryHistory(paths).concat(record).slice(-limit)
  saveDeliveryHistory(paths, records)
  return records
}

module.exports = {
  DEFAULT_DELIVERY_HISTORY_LIMIT,
  appendDeliveryHistory,
  deliveryHistoryPath,
  loadDeliveryHistory,
  saveDeliveryHistory
}
