const { createCommands } = require('./commands')

module.exports = function activate(ctx) {
  return createCommands(ctx)
}
