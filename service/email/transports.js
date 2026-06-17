const nodemailer = require('nodemailer')

const createFakeEmailTransport = ({ messageId = 'fake-message' } = {}) => {
  const sentMessages = []
  return {
    sentMessages,
    async send (message) {
      sentMessages.push(message)
      return { messageId }
    }
  }
}

const createUnavailableEmailTransport = (reason = 'SMTP transport is not configured') => ({
  async send () {
    throw new Error(reason)
  }
})

const timeoutFromEnv = (env) => {
  const timeout = Number(env.SMTP_TIMEOUT_MS || 10000)
  return Number.isFinite(timeout) && timeout > 0 ? timeout : 10000
}

const securityOptions = (security) => {
  if (security === 'ssl') return { secure: true }
  if (security === 'plain') return { secure: false, ignoreTLS: true }
  return { secure: false, requireTLS: true }
}

const buildSmtpOptions = ({ message, env }) => {
  const smtp = message.smtp || {}
  const host = String(smtp.host || '').trim()
  const port = Number(smtp.port || 587)
  const configuredSenderEmail = String(smtp.senderEmail || smtp.username || '').trim()
  const senderEmail = String(smtp.senderEmail || message.envelope?.from || '').trim()
  const username = String(smtp.username || '').trim()
  const password = String(env.SMTP_PASSWORD || '')

  if (!host) throw new Error('SMTP host is required')
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('SMTP port is invalid')
  if (!configuredSenderEmail || !senderEmail) throw new Error('SMTP sender email is required')
  if (smtp.passwordSaved && username && !password) throw new Error('SMTP password is required')

  const timeout = timeoutFromEnv(env)
  const options = {
    host,
    port,
    ...securityOptions(smtp.security),
    connectionTimeout: timeout,
    greetingTimeout: timeout,
    socketTimeout: timeout
  }
  if (username) {
    options.auth = { user: username, pass: password }
  }

  return { options, senderEmail }
}

const createSmtpEmailTransport = ({ env = process.env, createTransport = nodemailer.createTransport } = {}) => ({
  async verify (message) {
    const { options } = buildSmtpOptions({ message, env })
    const client = createTransport(options)
    await client.verify()
    return { ok: true }
  },
  async send (message) {
    const { options, senderEmail } = buildSmtpOptions({ message, env })
    const client = createTransport(options)
    return client.sendMail({
      from: senderEmail,
      to: message.envelope?.to,
      subject: message.subject,
      text: message.text,
      html: message.html
    })
  }
})

module.exports = {
  createFakeEmailTransport,
  createSmtpEmailTransport,
  createUnavailableEmailTransport
}
