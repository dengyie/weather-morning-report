const { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } = require('node:fs')
const path = require('node:path')
const crypto = require('node:crypto')

const SECRET_STORE_FILE_MODE = 0o600
const SECRET_KEY_BYTES = 32
const SECRET_KEY_FILE = '.secret-key'
const SECRET_ROTATION_STATE_FILE = '.secret-key-rotation.json'
const SECRETS_FILE = 'secrets.json'
const DECRYPTION_ERROR_MESSAGE = 'stored SMTP password could not be decrypted'
const CURRENT_SECRET_KEY_ERROR_MESSAGE = 'current local secret key is invalid'

const secretKeyPath = (paths) => path.join(paths.dataDir, SECRET_KEY_FILE)
const secretRotationStatePath = (paths) => path.join(paths.dataDir, SECRET_ROTATION_STATE_FILE)
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

const readRotationState = (paths) => {
  const file = secretRotationStatePath(paths)
  if (!existsSync(file)) return null
  try {
    const parsed = JSON.parse(readFileSync(file, 'utf8'))
    return parsed && typeof parsed === 'object' ? parsed : null
  } catch {
    return null
  }
}

const recoverPendingSecretRotation = (paths) => {
  const state = readRotationState(paths)
  if (!state) return

  try {
    writeFileSync(secretKeyPath(paths), state.previousKey, { mode: SECRET_STORE_FILE_MODE })
    writeFileSync(secretsPath(paths), state.previousSecrets, { mode: SECRET_STORE_FILE_MODE })
  } finally {
    rmSync(secretRotationStatePath(paths), { force: true })
  }
}

const loadOrCreateSecretKey = (paths) => {
  ensureDataDir(paths)
  recoverPendingSecretRotation(paths)
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

const loadExistingSecretKey = (paths) => {
  recoverPendingSecretRotation(paths)
  const file = secretKeyPath(paths)
  if (!existsSync(file)) {
    throw new Error(CURRENT_SECRET_KEY_ERROR_MESSAGE)
  }
  try {
    const key = decodeBase64(readFileSync(file, 'utf8'), CURRENT_SECRET_KEY_ERROR_MESSAGE)
    if (key.length !== SECRET_KEY_BYTES) {
      throw new Error(CURRENT_SECRET_KEY_ERROR_MESSAGE)
    }
    return key
  } catch {
    throw new Error(CURRENT_SECRET_KEY_ERROR_MESSAGE)
  }
}

const inspectSecretKey = (paths) => {
  recoverPendingSecretRotation(paths)
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
  recoverPendingSecretRotation(paths)
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

const encryptStoredSmtpPassword = (key, password, { now = new Date() } = {}) => {
  const iv = crypto.randomBytes(12)
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv)
  const ciphertext = Buffer.concat([cipher.update(String(password)), cipher.final()])
  const tag = cipher.getAuthTag()
  return {
    algorithm: 'aes-256-gcm',
    keyId: 'local',
    iv: iv.toString('base64'),
    tag: tag.toString('base64'),
    ciphertext: ciphertext.toString('base64'),
    updatedAt: now.toISOString()
  }
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
  const secrets = loadWritableSecrets(paths)

  secrets.smtpPassword = encryptStoredSmtpPassword(key, password, { now })

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

const rotateStoredSmtpPasswordKey = (paths, { now = new Date(), onRotated, writeFile } = {}) => {
  const secretsSnapshot = inspectSecretsFile(paths)
  if (!secretsSnapshot.ok) {
    return { ok: false, error: DECRYPTION_ERROR_MESSAGE }
  }

  const secretRecord = secretsSnapshot.value && typeof secretsSnapshot.value.smtpPassword === 'object'
    ? secretsSnapshot.value.smtpPassword
    : null
  if (!secretRecord) {
    return { ok: false, error: 'managed SMTP password is not configured' }
  }

  try {
    loadExistingSecretKey(paths)
  } catch (error) {
    return { ok: false, error: error.message }
  }

  let stored
  try {
    stored = loadStoredSmtpPassword(paths)
  } catch (error) {
    return { ok: false, error: error.message }
  }
  if (!stored?.password) {
    return { ok: false, error: 'managed SMTP password is not configured' }
  }

  const keyFile = secretKeyPath(paths)
  const secretFile = secretsPath(paths)
  const rotationStateFile = secretRotationStatePath(paths)
  const nextKeyFile = `${keyFile}.next`
  const nextSecretFile = `${secretFile}.next`
  const previousKey = readFileSync(keyFile, 'utf8')
  const previousSecrets = readFileSync(secretFile, 'utf8')
  const nextKey = crypto.randomBytes(SECRET_KEY_BYTES)
  const nextSecrets = {
    ...secretsSnapshot.value,
    smtpPassword: encryptStoredSmtpPassword(nextKey, stored.password, { now })
  }
  const nextKeyValue = nextKey.toString('base64')
  const nextSecretsValue = `${JSON.stringify(nextSecrets, null, 2)}\n`
  const rotationStateValue = `${JSON.stringify({
    previousKey,
    previousSecrets,
    nextKey: nextKeyValue,
    nextSecrets: nextSecretsValue
  }, null, 2)}\n`
  const write = typeof writeFile === 'function'
    ? (file, value, options) => writeFile(file, value, options, writeFileSync)
    : writeFileSync

  try {
    write(rotationStateFile, rotationStateValue, { mode: SECRET_STORE_FILE_MODE })
    write(nextKeyFile, nextKeyValue, { mode: SECRET_STORE_FILE_MODE })
    write(nextSecretFile, nextSecretsValue, { mode: SECRET_STORE_FILE_MODE })
    write(keyFile, nextKeyValue, { mode: SECRET_STORE_FILE_MODE })
    write(secretFile, nextSecretsValue, { mode: SECRET_STORE_FILE_MODE })
    if (typeof onRotated === 'function') {
      onRotated({
        backupConfirmed: false,
        updatedAt: nextSecrets.smtpPassword.updatedAt
      })
    }
    return {
      ok: true,
      backupConfirmed: false,
      updatedAt: nextSecrets.smtpPassword.updatedAt
    }
  } catch (error) {
    try {
      writeFileSync(keyFile, previousKey, { mode: SECRET_STORE_FILE_MODE })
    } catch {}
    try {
      writeFileSync(secretFile, previousSecrets, { mode: SECRET_STORE_FILE_MODE })
    } catch {}
    try {
      rmSync(rotationStateFile, { force: true })
    } catch {}
    return {
      ok: false,
      error: `rotation failed: ${error.message}`
    }
  } finally {
    if (existsSync(nextKeyFile)) rmSync(nextKeyFile, { force: true })
    if (existsSync(nextSecretFile)) rmSync(nextSecretFile, { force: true })
    if (existsSync(rotationStateFile)) rmSync(rotationStateFile, { force: true })
  }
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
  rotateStoredSmtpPasswordKey,
  saveStoredSmtpPassword,
  secretKeyPath,
  secretRotationStatePath,
  secretsPath
}
