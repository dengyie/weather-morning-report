const { runJsonCommand } = require('./runner')
const { clearCommandCache } = require('./weather-command')

runJsonCommand('clear-cache', clearCommandCache)
