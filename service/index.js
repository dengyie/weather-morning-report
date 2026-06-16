const { appendFileSync } = require('node:fs')
const path = require('node:path')
const { createServiceApp } = require('./app')
const { ensureServicePaths } = require('./paths')

const writeLog = (paths, message) => {
  const line = `${new Date().toISOString()} ${message}\n`
  appendFileSync(path.join(paths.logDir, 'service.log'), line)
}

const startService = async ({ env = process.env } = {}) => {
  const paths = ensureServicePaths(env)
  const app = createServiceApp({ env })
  const host = env.HOST || env.OPENPET_SERVICE_HOST || '127.0.0.1'
  const port = Number(env.PORT || env.OPENPET_SERVICE_PORT || 8787)

  await app.listen({ host, port })
  writeLog(paths, `started host=${host} port=${port}`)

  const shutdown = async () => {
    writeLog(paths, 'stopping')
    await app.close()
  }

  process.once('SIGINT', shutdown)
  process.once('SIGTERM', shutdown)

  return { app, host, port, paths }
}

if (require.main === module) {
  startService().catch((error) => {
    console.error(error)
    process.exitCode = 1
  })
}

module.exports = { startService }
