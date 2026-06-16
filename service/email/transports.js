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

module.exports = { createFakeEmailTransport, createUnavailableEmailTransport }
