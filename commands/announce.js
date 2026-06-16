const { runJsonCommand } = require('./runner')
const { announceReport } = require('./weather-command')

runJsonCommand('announce', announceReport)
