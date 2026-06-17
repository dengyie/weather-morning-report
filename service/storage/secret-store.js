const { existsSync, mkdirSync, readFileSync, writeFileSync } = require('node:fs')
const path = require('node:path')
const crypto = require('node:crypto')

const SECRET_STORE_FILE_MODE = 0o600
const SECRET_KEY_BYTES = 32
const SECRET_KEY_FILE = '.secret-key'
const SECRETS_FILE = 'secrets.json'
const DECRYPTION_ERROR_MESSAGE = 'stored SMTP password could not be decrypted'

const secretKeyPath = (paths) => path.join(paths.dataDir, SECRET_KEY_FILE)
const secretsPath = (paths) => path.join(paths.dataDir, SECRETS_FILE)

const ensureDataDir = (paths) => {
  mkdirSync(paths.dataDir, { recursive: true })
}

const decodeBase64 = (value, errorMessage) => {
  const normalized = String(value || '').trim()
  if (!normalized || normalized.length % 4 !== 0 || !/^[A-Za-z0-9+/]+={0,2}$/.test(normalized)) {
    throw new Error(errorMessage)
  }
  return Buffer.from(normalized, 'base64')
}

const loadOrCreateSecretKey = (paths) => {
  ensureDataDir(paths)
  const file = secretKeyPath(paths)
  if (!existsSync(file)) {
    const key = crypto.randomBytes(SECRET_KEY_BYTES)
    writeFileSync(file, key.toString('base64'), { mode: SECRET_STORE_FILE_MODE })
    return key
  }

  const key = decodeBase64(readFileSync(file, 'utf8'), 'SMTP secret key is invalid')
  if (key.length !== SECRET_KEY_BYTES) {
    throw new Error('SMTP secret key is invalid')
  }
  return key
}

const inspectSecretKey = (paths) => {
  const file = secretKeyPath(paths)
  if (!existsSync(file)) {
    return { present: false, valid: false }
  }
  try {
    const key = decodeBase64(readFileSync(file, 'utf8'), 'SMTP secret key is invalid')
    return { present: true, valid: key.length === SECRET_KEY_BYTES }
  } catch {
    return { present: true, valid: false }
  }
}

const loadSecrets = (paths) => {
  const file = secretsPath(paths)
  if (!existsSync(file)) return {}
  const parsed = JSON.parse(readFileSync(file, 'utf8'))
  return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
}

const inspectSecretsFile = (paths) => {
  try {
    return { ok: true, value: loadSecrets(paths) }
  } catch {
    return { ok: false, value: null }
  }
}

const loadWritableSecrets = (paths) => {
  const secrets = inspectSecretsFile(paths)
  return secrets.ok ? secrets.value : {}
}

const saveSecrets = (paths, secrets) => {
  ensureDataDir(paths)
  writeFileSync(secretsPath(paths), `${JSON.stringify(secrets, null, 2)}\n`, { mode: SECRET_STORE_FILE_MODE })
}

const hasStoredSmtpPassword = (paths) => {
  try {
    const secretRecord = loadSecrets(paths).smtpPassword
    return Boolean(secretRecord && typeof secretRecord === 'object')
  } catch {
    return true
  }
}

const saveStoredSmtpPassword = (paths, password, { now = new Date() } = {}) => {
  const key = loadOrCreateSecretKey(paths)
  const iv = crypto.randomBytes(12)
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv)
  const ciphertext = Buffer.concat([cipher.update(String(password)), cipher.final()])
  const tag = cipher.getAuthTag()
  const secrets = loadWritableSecrets(paths)

  secrets.smtpPassword = {
    algorithm: 'aes-256-gcm',
    keyId: 'local',
    iv: iv.toString('base64'),
    tag: tag.toString('base64'),
    ciphertext: ciphertext.toString('base64'),
    updatedAt: now.toISOString()
  }

  saveSecrets(paths, secrets)
  return secrets.smtpPassword
}

const loadStoredSmtpPassword = (paths) => {
  let secretRecord
  try {
    secretRecord = loadSecrets(paths).smtpPassword
  } catch {
    throw new Error(DECRYPTION_ERROR_MESSAGE)
  }
  if (!secretRecord || typeof secretRecord !== 'object') return null

  try {
    if (secretRecord.algorithm !== 'aes-256-gcm') {
      throw new Error(DECRYPTION_ERROR_MESSAGE)
    }

    const key = loadOrCreateSecretKey(paths)
    const iv = decodeBase64(secretRecord.iv, DECRYPTION_ERROR_MESSAGE)
    const tag = decodeBase64(secretRecord.tag, DECRYPTION_ERROR_MESSAGE)
    const ciphertext = decodeBase64(secretRecord.ciphertext, DECRYPTION_ERROR_MESSAGE)
    if (iv.length !== 12 || tag.length !== 16 || ciphertext.length === 0) {
      throw new Error(DECRYPTION_ERROR_MESSAGE)
    }

    const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv)
    decipher.setAuthTag(tag)
    const password = Buffer.concat([decipher.update(ciphertext), decipher.final()]).toString('utf8')

    return {
      password,
      updatedAt: secretRecord.updatedAt || ''
    }
  } catch (error) {
    if (error.message === DECRYPTION_ERROR_MESSAGE) {
      throw error
    }
    throw new Error(DECRYPTION_ERROR_MESSAGE)
  }
}

const clearStoredSmtpPassword = (paths) => {
  const secrets = loadSecrets(paths)
  if (!secrets.smtpPassword) return false
  delete secrets.smtpPassword
  saveSecrets(paths, secrets)
  return true
}

const inspectSecretHealth = (paths, { backupConfirmed = false } = {}) => {
  const masterKey = inspectSecretKey(paths)
  const secrets = inspectSecretsFile(paths)

  if (!secrets.ok) {
    return {
      status: 'unhealthy',
      backupConfirmed: Boolean(backupConfirmed),
      warning: '已保存的 SMTP 密码无法解密',
      masterKey,
      managedSmtpPassword: { present: false, healthy: false, updatedAt: '' }
    }
  }

  const secretRecord = secrets.value && typeof secrets.value.smtpPassword === 'object'
    ? secrets.value.smtpPassword
    : null

  if (!secretRecord) {
    return {
      status: 'not-configured',
      backupConfirmed: Boolean(backupConfirmed),
      warning: '',
      masterKey,
      managedSmtpPassword: { present: false, healthy: false, updatedAt: '' }
    }
  }

  if (!masterKey.valid) {
    return {
      status: 'unhealthy',
      backupConfirmed: Boolean(backupConfirmed),
      warning: '本地密钥缺失或无效',
      masterKey,
      managedSmtpPassword: {
        present: true,
        healthy: false,
        updatedAt: secretRecord.updatedAt || ''
      }
    }
  }

  try {
    const stored = loadStoredSmtpPassword(paths)
    if (!stored) throw new Error('missing managed SMTP password')
    return {
      status: backupConfirmed ? 'healthy' : 'backup-unconfirmed',
      backupConfirmed: Boolean(backupConfirmed),
      warning: backupConfirmed ? '' : '本地密钥尚未确认备份',
      masterKey,
      managedSmtpPassword: {
        present: true,
        healthy: true,
        updatedAt: stored.updatedAt || ''
      }
    }
  } catch {
    return {
      status: 'unhealthy',
      backupConfirmed: Boolean(backupConfirmed),
      warning: '已保存的 SMTP 密码无法解密',
      masterKey,
      managedSmtpPassword: {
        present: true,
        healthy: false,
        updatedAt: secretRecord.updatedAt || ''
      }
    }
  }
}

module.exports = {
  clearStoredSmtpPassword,
  hasStoredSmtpPassword,
  inspectSecretHealth,
  loadStoredSmtpPassword,
  saveStoredSmtpPassword,
  secretKeyPath,
  secretsPath
}
