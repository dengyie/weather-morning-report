const { chmodSync, existsSync, mkdirSync, readFileSync, writeFileSync } = require('node:fs')
const path = require('node:path')
const crypto = require('node:crypto')

const DASHBOARD_TOKEN_FILE = '.dashboard-token'
const DASHBOARD_TOKEN_FILE_MODE = 0o600
const DASHBOARD_TOKEN_BYTES = 32

const dashboardTokenPath = (paths) => path.join(paths.dataDir, DASHBOARD_TOKEN_FILE)

const dashboardAuthEnabled = (env = process.env) => env.OPENPET_DASHBOARD_AUTH !== 'disabled'

const generateDashboardToken = () => crypto.randomBytes(DASHBOARD_TOKEN_BYTES).toString('base64url')

const ensureDashboardToken = (paths) => {
  mkdirSync(paths.dataDir, { recursive: true })
  const file = dashboardTokenPath(paths)
  if (existsSync(file)) {
    const existing = readFileSync(file, 'utf8').trim()
    if (existing) {
      chmodSync(file, DASHBOARD_TOKEN_FILE_MODE)
      return existing
    }
  }
  const token = generateDashboardToken()
  writeFileSync(file, `${token}\n`, { mode: DASHBOARD_TOKEN_FILE_MODE })
  return token
}

const timingSafeEqualString = (left, right) => {
  const leftBuffer = Buffer.from(String(left || ''))
  const rightBuffer = Buffer.from(String(right || ''))
  return leftBuffer.length === rightBuffer.length && crypto.timingSafeEqual(leftBuffer, rightBuffer)
}

const tokenFromRequest = (request) => {
  const headerToken = request.headers['x-openpet-dashboard-token']
  if (Array.isArray(headerToken)) return headerToken[0]
  return headerToken || request.body?.dashboard_token || ''
}

const verifyDashboardToken = (request, expectedToken) => timingSafeEqualString(tokenFromRequest(request), expectedToken)

module.exports = {
  dashboardAuthEnabled,
  dashboardTokenPath,
  ensureDashboardToken,
  verifyDashboardToken
}
