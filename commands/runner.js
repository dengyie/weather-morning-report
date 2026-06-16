const { readFileSync } = require('node:fs')

const readInputJson = () => {
  const input = readFileSync(0, 'utf8').trim()
  if (!input) return {}
  try {
    return JSON.parse(input)
  } catch (error) {
    throw new Error(`Invalid JSON input: ${error.message}`)
  }
}

const redact = (message, env = process.env) => {
  let redacted = String(message || '')
  for (const secret of [env.SMTP_PASSWORD].filter(Boolean)) {
    redacted = redacted.split(String(secret)).join('[redacted]')
  }
  return redacted.replace(/password=[^\s&]+/gi, 'password=[redacted]')
}

const shouldRedactKey = (key) => /password|secret|token/i.test(String(key))

const redactJson = (value, env = process.env) => {
  if (Array.isArray(value)) return value.map((item) => redactJson(item, env))
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [
      key,
      shouldRedactKey(key) ? '[redacted]' : redactJson(item, env)
    ]))
  }
  if (typeof value === 'string') return redact(value, env)
  return value
}

const extensionEnv = (env = process.env) => ({
  dataDirConfigured: Boolean(env.OPENPET_DATA_DIR),
  cacheDirConfigured: Boolean(env.OPENPET_CACHE_DIR),
  logDirConfigured: Boolean(env.OPENPET_LOG_DIR)
})

const basicCommandResult = (command, input, env = process.env) => ({
  ok: true,
  command,
  input,
  env: extensionEnv(env)
})

const runJsonCommand = async (command, handler, { env = process.env } = {}) => {
  try {
    const input = readInputJson()
    const result = await handler({ command, input, env })
    process.stdout.write(`${JSON.stringify(redactJson(result, env))}\n`)
  } catch (error) {
    process.stderr.write(`${redact(error.message, env)}\n`)
    process.exitCode = 1
  }
}

module.exports = { basicCommandResult, extensionEnv, redact, redactJson, runJsonCommand }
