const { runJsonCommand } = require('./runner')
const { refreshReport } = require('./weather-command')

runJsonCommand('refresh', refreshReport)
