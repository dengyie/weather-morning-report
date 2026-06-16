const { execFileSync } = require('node:child_process')
const { mkdirSync, mkdtempSync, rmSync } = require('node:fs')
const { tmpdir } = require('node:os')
const path = require('node:path')
const { spawn } = require('node:child_process')

const repoRoot = path.resolve(__dirname, '..')
const archivePath = path.join(repoRoot, 'release/weather-morning-report.openpet-extension.zip')
const openPetRoot = path.resolve(process.env.OPENPET_REPO_ROOT || path.join(repoRoot, '../OpenPet'))
const pluginId = 'weather-morning-report'
const serviceId = 'weather-service'
const dashboardId = 'main'

const createSettingsService = () => {
  let current = {
    plugins: {
      enabled: {},
      config: {},
      storage: {},
      installed: {},
      logs: []
    }
  }

  return {
    get: () => current,
    save: (settings) => {
      current = settings
      return current
    }
  }
}

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const waitForHealthyService = async (pluginService, attempts = 20) => {
  let lastResult = null
  for (let index = 0; index < attempts; index += 1) {
    lastResult = await pluginService.checkServiceHealth(pluginId, serviceId)
    if (lastResult.health?.status === 'healthy') return lastResult
    await delay(100)
  }
  throw new Error(`Service did not become healthy: ${lastResult?.health?.message || 'unknown'}`)
}

const assertOpenPetRuntimeCapabilities = (pluginService) => {
  const requiredMethods = [
    'listPlugins',
    'setEnabled',
    'openDashboard',
    'startService',
    'checkServiceHealth',
    'runCommand',
    'stopService',
    'stopAllServices',
    'getLogs'
  ]
  const missing = requiredMethods.filter((method) => typeof pluginService[method] !== 'function')
  if (missing.length) {
    throw new Error(`OpenPet runtime does not expose Phase 9 plugin service APIs: ${missing.join(', ')}`)
  }
}

const runSmoke = async () => {
  execFileSync('npm', ['run', 'package:extension'], { cwd: repoRoot, stdio: 'pipe' })

  const { createPluginService } = require(path.join(openPetRoot, 'src/main/services/plugin-service'))
  const runtimeRoot = mkdtempSync(path.join(tmpdir(), 'wmr-openpet-runtime-'))
  const installedPluginsRoot = path.join(runtimeRoot, 'plugins')
  const installedPluginDir = path.join(installedPluginsRoot, pluginId)
  const openedDashboards = []
  const petSpeech = []
  const settingsService = createSettingsService()
  let pluginService

  mkdirSync(installedPluginDir, { recursive: true })
  execFileSync('unzip', ['-q', archivePath, '-d', installedPluginDir], { cwd: repoRoot, stdio: 'pipe' })
  execFileSync('npm', ['install', '--omit=dev', '--ignore-scripts', '--package-lock=false'], {
    cwd: installedPluginDir,
    stdio: 'pipe'
  })

  const spawnServiceProcess = (file, args, options = {}) => spawn(file, args, {
    ...options,
    env: {
      ...options.env,
      OPENPET_DATA_DIR: path.join(runtimeRoot, 'data'),
      OPENPET_CACHE_DIR: path.join(runtimeRoot, 'cache'),
      OPENPET_LOG_DIR: path.join(runtimeRoot, 'logs')
    }
  })

  try {
    pluginService = createPluginService({
      settingsService,
      petService: {
        say: async (payload) => {
          petSpeech.push(payload)
          return { ok: true }
        },
        playAction: async () => ({ ok: true }),
        setEvent: async () => ({ ok: true })
      },
      pluginDirs: [installedPluginsRoot],
      openExternal: async (url) => {
        openedDashboards.push(url)
      },
      spawnServiceProcess,
      healthCheckTimeoutMs: 1000
    })
    assertOpenPetRuntimeCapabilities(pluginService)

    const beforeEnable = pluginService.listPlugins().find((plugin) => plugin.id === pluginId)
    if (!beforeEnable) throw new Error(`OpenPet runtime did not discover ${pluginId}`)
    if (!beforeEnable.entries?.services?.some((entry) => entry.id === serviceId)) {
      throw new Error(`OpenPet runtime did not expose service entry ${serviceId}`)
    }
    if (!beforeEnable.entries?.dashboards?.some((entry) => entry.id === dashboardId)) {
      throw new Error(`OpenPet runtime did not expose dashboard entry ${dashboardId}`)
    }
    if (!beforeEnable.entries?.commands?.some((entry) => entry.id === 'status')) {
      throw new Error('OpenPet runtime did not expose status command entry')
    }

    const enabled = pluginService.setEnabled(pluginId, true)
    const dashboard = await pluginService.openDashboard(pluginId, dashboardId)
    const serviceStart = pluginService.startService(pluginId, serviceId)
    await delay(150)
    const serviceHealth = await waitForHealthyService(pluginService)
    const commandStatus = await pluginService.runCommand(pluginId, 'status')
    const serviceStop = pluginService.stopService(pluginId, serviceId)
    const logs = pluginService.getLogs({ pluginId })

    return {
      ok: true,
      pluginId,
      installed: {
        fromArchive: true,
        dependenciesInstalled: true,
        pluginDir: installedPluginDir
      },
      discovered: {
        commands: beforeEnable.entries.commands.map((entry) => entry.id),
        services: beforeEnable.entries.services.map((entry) => entry.id),
        dashboards: beforeEnable.entries.dashboards.map((entry) => entry.id)
      },
      enabled: { enabled: enabled.enabled },
      dashboard: {
        ...dashboard,
        openedUrl: openedDashboards[0] || ''
      },
      service: {
        start: serviceStart,
        health: serviceHealth,
        stop: serviceStop
      },
      command: {
        status: commandStatus
      },
      logs,
      petSpeech
    }
  } finally {
    try {
      pluginService?.stopAllServices()
    } finally {
      rmSync(runtimeRoot, { recursive: true, force: true })
    }
  }
}

const main = async () => {
  const json = process.argv.includes('--json')
  const evidence = await runSmoke()
  if (json) {
    process.stdout.write(`${JSON.stringify(evidence, null, 2)}\n`)
    return
  }
  console.log('OpenPet runtime smoke passed.')
  console.log(`Dashboard opened: ${evidence.dashboard.openedUrl}`)
  console.log(`Service health: ${evidence.service.health.health.status}`)
  console.log(`Command status ok: ${evidence.command.status.ok}`)
  console.log(`Logs captured: ${evidence.logs.length}`)
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error.message || error)
    process.exit(1)
  })
}

module.exports = { runSmoke }
