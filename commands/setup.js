const { runJsonCommand } = require('./runner')

runJsonCommand('setup', ({ command, input }) => ({
  ok: true,
  command,
  input,
  requiresInstall: false,
  message: 'Package dependencies are installed by the extension host or development setup before runtime commands execute.'
}))
