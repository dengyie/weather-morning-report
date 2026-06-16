const { existsSync } = require('node:fs')
const { execFileSync } = require('node:child_process')
const path = require('node:path')

const repoRoot = process.cwd()
const archivePath = path.join(repoRoot, 'release/weather-morning-report.openpet-extension.zip')

const fail = (message) => {
  console.error(message)
  process.exit(1)
}

if (!existsSync(archivePath)) {
  fail(`Missing unified extension archive: ${archivePath}`)
}

const listing = execFileSync('unzip', ['-Z1', archivePath], { encoding: 'utf8' })
  .trim()
  .split('\n')
  .filter(Boolean)
const files = new Set(listing)
const manifest = JSON.parse(execFileSync('unzip', ['-p', archivePath, 'plugin.json'], { encoding: 'utf8' }))

const requireFile = (file) => {
  if (!files.has(file)) fail(`Missing required file in extension archive: ${file}`)
}

const forbiddenPrefixes = ['legacy-assets/', 'docs/', 'tests/', 'release/', 'node_modules/', '.git/']
for (const file of listing) {
  if (forbiddenPrefixes.some((prefix) => file.startsWith(prefix)) || file === '.env' || file.endsWith('/.env')) {
    fail(`Forbidden file in extension archive: ${file}`)
  }
}

for (const file of [
  'plugin.json',
  'config.schema.json',
  'package.json',
  'README.md',
  'compat/openpet-main.js',
  'commands/runner.js',
  'commands/weather-command.js',
  'core/weather-provider.js',
  'rendering/email-renderer.js',
  'service/index.js',
  'service/app.js',
  'static/app.css'
]) {
  requireFile(file)
}

const main = String(manifest.main || '')
if (!main) fail('Manifest must declare a compatibility main file')
if (path.isAbsolute(main) || main.includes('..')) {
  fail('Manifest main must be package-relative')
}
requireFile(main)

for (const entry of manifest.entries?.commands || []) {
  const command = String(entry.command || '')
  const match = /^node ([^\s]+)$/.exec(command)
  if (!match) fail(`Command entry must use "node <relative-file>": ${entry.id}`)
  const commandFile = match[1]
  if (path.isAbsolute(commandFile) || commandFile.includes('..')) {
    fail(`Command entry must be package-relative: ${entry.id}`)
  }
  requireFile(commandFile)
}

for (const entry of manifest.entries?.setup || []) {
  const command = String(entry.command || '')
  const match = /^node ([^\s]+)$/.exec(command)
  if (!match) fail(`Setup entry must use "node <relative-file>": ${entry.id}`)
  const commandFile = match[1]
  if (path.isAbsolute(commandFile) || commandFile.includes('..')) {
    fail(`Setup entry must be package-relative: ${entry.id}`)
  }
  requireFile(commandFile)
}

const service = manifest.entries?.services?.[0]
if (!service) fail('Manifest must declare a service entry')
const serviceMatch = /^node ([^\s]+)$/.exec(String(service.command || ''))
if (!serviceMatch) fail('Service command must use "node <relative-file>"')
requireFile(serviceMatch[1])

const dashboard = manifest.entries?.dashboards?.[0]
if (!dashboard) fail('Manifest must declare a dashboard entry')
const serviceOrigin = new URL(service.health.url).origin
const dashboardOrigin = new URL(dashboard.url).origin
if (serviceOrigin !== dashboardOrigin) {
  fail(`Dashboard origin ${dashboardOrigin} does not match service health origin ${serviceOrigin}`)
}

console.log('Unified extension artifact check passed.')
