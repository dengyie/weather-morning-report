const test = require('node:test')
const assert = require('node:assert/strict')
const { existsSync } = require('node:fs')
const { rm, mkdir } = require('node:fs/promises')
const { execFileSync } = require('node:child_process')
const path = require('node:path')

const repoRoot = path.resolve(__dirname, '..')
const releaseDir = path.join(repoRoot, 'release')
const archivePath = path.join(releaseDir, 'weather-morning-report.openpet-plugin.zip')

test('package script creates an OpenPet plugin zip with only package files', async () => {
  await mkdir(releaseDir, { recursive: true })
  await rm(archivePath, { force: true })

  execFileSync('npm', ['run', 'package:plugin'], { cwd: repoRoot, stdio: 'pipe' })

  assert.equal(existsSync(archivePath), true)
  const listing = execFileSync('unzip', ['-Z1', archivePath], { encoding: 'utf8' })
    .trim()
    .split('\n')
    .sort()

  assert.deepEqual(listing, [
    'README.md',
    'config.schema.json',
    'index.js',
    'plugin.json'
  ])
})
