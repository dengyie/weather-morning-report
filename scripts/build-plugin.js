const { readFileSync, writeFileSync } = require('node:fs')

const readModule = (path) => readFileSync(path, 'utf8')

const stripModule = (source, { removeRequires = true } = {}) => {
  let result = source
  if (removeRequires) {
    result = result.replace(/^const \{[^\n]+\} = require\('[^']+'\)\n/gm, '')
  }
  result = result.replace(/^module\.exports = \{[\s\S]*?\}\n?$/m, '')
  return result.trim()
}

const bundle = [
  stripModule(readModule('core/config.js')),
  stripModule(readModule('core/wttr-parser.js')),
  stripModule(readModule('core/weather-provider.js')),
  stripModule(readModule('core/period-schedule.js')),
  stripModule(readModule('core/recommendation-engine.js')),
  stripModule(readModule('rendering/text-renderer.js')),
  stripModule(readModule('src/commands.js')),
  'module.exports = function activate(ctx) {\n  return createCommands(ctx)\n}\n'
].join('\n\n')

writeFileSync('openpet-plugin/index.js', `${bundle}\n`)
