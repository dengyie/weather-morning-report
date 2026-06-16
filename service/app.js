const { readFileSync } = require('node:fs')
const path = require('node:path')
const fastify = require('fastify')
const { ensureServicePaths } = require('./paths')
const { version } = require('../package.json')

const renderDashboard = () => `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Weather Morning Report</title>
  <link rel="stylesheet" href="/static/app.css">
</head>
<body>
  <main class="shell">
    <section class="hero-card">
      <p class="eyebrow">OpenPet Companion Service</p>
      <h1>Weather Morning Report</h1>
      <p>Fastify service is ready. Web dashboard, Email preview, SMTP delivery, and scheduler controls will be promoted here phase by phase.</p>
    </section>
  </main>
</body>
</html>`

const createServiceApp = ({ env = process.env } = {}) => {
  const paths = ensureServicePaths(env)
  const app = fastify({ logger: false })

  app.get('/health', async () => ({
    ok: true,
    service: 'weather-morning-report',
    framework: 'fastify',
    version,
    directories: {
      data: Boolean(paths.dataDir),
      cache: Boolean(paths.cacheDir),
      logs: Boolean(paths.logDir)
    }
  }))

  app.get('/', async (_request, reply) => {
    reply.type('text/html; charset=utf-8')
    return renderDashboard()
  })

  app.get('/static/app.css', async (_request, reply) => {
    reply.type('text/css; charset=utf-8')
    return readFileSync(path.join(__dirname, '..', 'static', 'app.css'), 'utf8')
  })

  return app
}

module.exports = { createServiceApp }
