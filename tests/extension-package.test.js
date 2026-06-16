const test = require('node:test')
const assert = require('node:assert/strict')
const { existsSync, readFileSync } = require('node:fs')
const { rm, mkdir } = require('node:fs/promises')
const { execFileSync } = require('node:child_process')
const path = require('node:path')

const repoRoot = path.resolve(__dirname, '..')
const manifestPath = path.join(repoRoot, 'extension/plugin.json')
const releaseDir = path.join(repoRoot, 'release')
const extensionArchivePath = path.join(releaseDir, 'weather-morning-report.openpet-extension.zip')

const loadManifest = () => JSON.parse(readFileSync(manifestPath, 'utf8'))

test('unified extension manifest declares commands service dashboard and data boundaries', () => {
  const manifest = loadManifest()

  assert.equal(manifest.id, 'weather-morning-report')
  assert.equal(manifest.main, 'compat/openpet-main.js')
  assert.equal(manifest.config, 'config.schema.json')
  assert.deepEqual(manifest.permissions, ['network', 'pet:say', 'storage'])
  assert.deepEqual(manifest.network.allowlist, ['wttr.in', 'wttr.is'])
  assert.deepEqual(manifest.manifest.network, ['wttr.in', 'wttr.is'])
  assert.deepEqual(manifest.entries.commands.map((entry) => entry.id), [
    'refresh',
    'announce',
    'last',
    'status',
    'clear-cache',
    'send-email-now',
    'setup',
    'cleanup'
  ])
  assert.deepEqual(manifest.entries.setup, [
    { id: 'setup', title: 'Setup Weather Morning Report', command: 'node commands/setup.js', cwd: '.' }
  ])
  assert.equal(manifest.entries.services[0].command, 'node service/index.js')
  assert.equal(manifest.entries.services[0].health.url, 'http://127.0.0.1:8787/health')
  assert.equal(manifest.entries.dashboards[0].url, 'http://127.0.0.1:8787')
  assert.ok(manifest.manifest.dataLocations.includes('OPENPET_DATA_DIR'))
  assert.ok(manifest.manifest.selfManagedSecrets.includes('SMTP password'))
})

test('package:extension creates a unified extension zip with active runtime files', async () => {
  await rm(releaseDir, { recursive: true, force: true })
  await mkdir(releaseDir, { recursive: true })

  execFileSync('npm', ['run', 'package:extension'], { cwd: repoRoot, stdio: 'pipe' })

  assert.equal(existsSync(extensionArchivePath), true)
  const listing = execFileSync('unzip', ['-Z1', extensionArchivePath], { encoding: 'utf8' })
    .trim()
    .split('\n')
    .sort()

  assert.ok(listing.includes('plugin.json'))
  assert.ok(listing.includes('config.schema.json'))
  assert.ok(listing.includes('package.json'))
  assert.ok(listing.includes('README.md'))
  assert.ok(listing.includes('compat/openpet-main.js'))
  assert.ok(listing.includes('commands/status.js'))
  assert.ok(listing.includes('commands/send-email-now.js'))
  assert.ok(listing.includes('commands/cleanup.js'))
  assert.ok(listing.includes('commands/weather-command.js'))
  assert.ok(listing.includes('core/weather-provider.js'))
  assert.ok(listing.includes('rendering/email-renderer.js'))
  assert.ok(listing.includes('service/index.js'))
  assert.ok(listing.includes('service/app.js'))
  assert.ok(listing.includes('static/app.css'))
  assert.equal(listing.some((file) => file.startsWith('legacy-assets/')), false)
  assert.equal(listing.some((file) => file.startsWith('docs/')), false)
  assert.equal(listing.some((file) => file.startsWith('tests/')), false)
  assert.equal(listing.some((file) => file.startsWith('node_modules/')), false)
  assert.equal(listing.some((file) => file.endsWith('.env')), false)
})

test('lint:extension validates manifest paths and URL consistency', () => {
  execFileSync('npm', ['run', 'package:extension'], { cwd: repoRoot, stdio: 'pipe' })
  const output = execFileSync('npm', ['run', 'lint:extension'], {
    cwd: repoRoot,
    encoding: 'utf8'
  })

  assert.match(output, /Unified extension artifact check passed/)
})
