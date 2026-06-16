const { runJsonCommand } = require('./runner')

runJsonCommand('send-email-now', ({ command, input, env }) => {
  const serviceUrl = String(env.OPENPET_SERVICE_URL || '').trim()
  if (!serviceUrl) {
    return {
      ok: false,
      command,
      input,
      status: 'service_unavailable',
      message: 'OPENPET_SERVICE_URL is required for service-backed Email delivery in Phase 7.'
    }
  }
  return {
    ok: false,
    command,
    input,
    status: 'not_sent',
    serviceUrl,
    message: 'Service-backed send-email-now transport will be wired after OpenPet service lifecycle integration.'
  }
})
