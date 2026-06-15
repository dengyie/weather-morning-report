const { readFileSync } = require('node:fs')
const path = require('node:path')

const pluginEntry = path.join(process.cwd(), 'openpet-plugin/index.js')
const source = readFileSync(pluginEntry, 'utf8')

const forbiddenPatterns = [
  ['runtime require', /\brequire\s*\(/],
  ['process global', /\bprocess\b/],
  ['fs module string', /['\"](?:node:)?fs['\"]/],
  ['child_process module string', /['\"](?:node:)?child_process['\"]/],
  ['electron module string', /['\"]electron['\"]/],
  ['eval call', /\beval\s*\(/],
  ['Function constructor', /\bnew\s+Function\b/]
]
const hits = forbiddenPatterns.filter(([, pattern]) => pattern.test(source)).map(([label]) => label)

if (hits.length > 0) {
  console.error(`Forbidden pattern(s) found in openpet-plugin/index.js: ${hits.join(', ')}`)
  process.exit(1)
}

if (!source.includes('module.exports = function activate')) {
  console.error('openpet-plugin/index.js must export activate(ctx)')
  process.exit(1)
}

console.log('Plugin artifact check passed.')
