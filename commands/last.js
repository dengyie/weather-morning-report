const { runJsonCommand } = require('./runner')
const { lastReport } = require('./weather-command')

runJsonCommand('last', lastReport)
