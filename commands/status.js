const { runJsonCommand } = require('./runner')
const { statusReport } = require('./weather-command')

runJsonCommand('status', statusReport)
