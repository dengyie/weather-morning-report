const { existsSync, mkdirSync, rmSync } = require('node:fs')
const { execFileSync } = require('node:child_process')
const path = require('node:path')

const repoRoot = process.cwd()
const releaseDir = path.join(repoRoot, 'release')
const pluginDir = path.join(repoRoot, 'openpet-plugin')
const archivePath = path.join(releaseDir, 'weather-morning-report.openpet-plugin.zip')
const files = ['plugin.json', 'config.schema.json', 'index.js', 'README.md']

if (!existsSync(path.join(pluginDir, 'README.md'))) {
  throw new Error('openpet-plugin/README.md is required before packaging')
}

execFileSync(process.execPath, [path.join(repoRoot, 'scripts/build-plugin.js')], { cwd: repoRoot, stdio: 'pipe' })
mkdirSync(releaseDir, { recursive: true })
rmSync(archivePath, { force: true })
execFileSync('zip', ['-q', '-j', archivePath, ...files.map((file) => path.join(pluginDir, file))], { cwd: repoRoot, stdio: 'pipe' })
console.log(`Created ${archivePath}`)
