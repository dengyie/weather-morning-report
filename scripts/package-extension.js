const { cpSync, existsSync, mkdirSync, rmSync, writeFileSync } = require('node:fs')
const { execFileSync } = require('node:child_process')
const path = require('node:path')

const repoRoot = process.cwd()
const releaseDir = path.join(repoRoot, 'release')
const stageDir = path.join(releaseDir, 'weather-morning-report-extension')
const archivePath = path.join(releaseDir, 'weather-morning-report.openpet-extension.zip')

const copyRequired = (from, to) => {
  if (!existsSync(from)) throw new Error(`Required package source is missing: ${from}`)
  cpSync(from, to, { recursive: true })
}

const writePackageMetadata = () => {
  const rootPackage = require(path.join(repoRoot, 'package.json'))
  const metadata = {
    name: rootPackage.name,
    version: rootPackage.version,
    private: true,
    type: rootPackage.type,
    main: 'service/index.js',
    scripts: {
      'service:start': 'node service/index.js'
    },
    dependencies: rootPackage.dependencies || {}
  }
  writeFileSync(path.join(stageDir, 'package.json'), `${JSON.stringify(metadata, null, 2)}\n`)
}

execFileSync(process.execPath, [path.join(repoRoot, 'scripts/build-plugin.js')], { cwd: repoRoot, stdio: 'pipe' })
mkdirSync(releaseDir, { recursive: true })
rmSync(stageDir, { force: true, recursive: true })
rmSync(archivePath, { force: true })
mkdirSync(stageDir, { recursive: true })

copyRequired(path.join(repoRoot, 'extension/plugin.json'), path.join(stageDir, 'plugin.json'))
copyRequired(path.join(repoRoot, 'openpet-plugin/config.schema.json'), path.join(stageDir, 'config.schema.json'))
copyRequired(path.join(repoRoot, 'openpet-plugin/README.md'), path.join(stageDir, 'README.md'))
for (const directory of ['commands', 'core', 'rendering', 'service', 'static']) {
  copyRequired(path.join(repoRoot, directory), path.join(stageDir, directory))
}
mkdirSync(path.join(stageDir, 'compat'), { recursive: true })
copyRequired(path.join(repoRoot, 'openpet-plugin/index.js'), path.join(stageDir, 'compat/openpet-main.js'))
writePackageMetadata()

execFileSync('zip', ['-qr', archivePath, '.'], { cwd: stageDir, stdio: 'pipe' })
console.log(`Created ${archivePath}`)
