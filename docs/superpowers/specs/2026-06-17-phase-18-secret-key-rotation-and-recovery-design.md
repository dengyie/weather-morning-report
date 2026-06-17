# Phase 18 Secret Key Rotation And Recovery Design

> Status: proposed on `codex/phase-18-secret-key-rotation-and-recovery`.
> Scope: Phase 18 after `docs/superpowers/specs/2026-06-17-phase-17-secret-key-backup-and-health-ux-design.md`.
> Non-scope: raw secret-key export/download, cross-machine restore, external KMS or OS keychain integration, SMTP credential rotation at the provider, scheduler daemonization, dashboard authentication, and OpenPet-owned secret management.

## Goal

Phase 18 adds a safe local secret-key rotation flow so operators can replace the service-owned `.secret-key` without losing the managed SMTP password and without leaving the service in a half-rotated broken state.

## Product Direction

Use a conservative service-owned rotation path:

- keep the local key opaque and non-exportable;
- rotate only when the current managed SMTP secret can be decrypted successfully;
- re-encrypt the existing managed SMTP password under a new local key;
- make rotation atomic from the operator point of view;
- reset backup acknowledgement after success so the new key must be re-confirmed as backed up;
- preserve Phase 16 and Phase 17 redaction guarantees.

This phase is about lifecycle safety for local secrets, not portability.

## User Problem

After Phase 17, operators can see whether the local key and managed SMTP secret are healthy, but they still cannot safely replace the key if they want to refresh local secret material after a backup event, workstation change, or security review.

Today the only possible way to do that is manual filesystem surgery:

- delete or overwrite `.secret-key`;
- risk breaking the encrypted SMTP secret permanently;
- recover only by manually re-entering SMTP credentials;
- lose UI continuity and backup-confirmation semantics.

That is too brittle for a production-facing local secret lifecycle.

## Rotation Scope

Phase 18 should support one rotation mode only:

1. validate the existing local key and managed SMTP password;
2. decrypt the current managed SMTP password into runtime memory only;
3. generate a new local key;
4. re-encrypt the same managed SMTP password with the new key;
5. commit the new key and updated secret payload;
6. reset `configuration.notifications.secretKeyBackupConfirmed` to `false`.

This phase should not support:

- generating a new key while leaving managed SMTP secret state unresolved;
- forcing the operator to re-enter the SMTP password as the primary happy path;
- exporting old or new key material through HTTP;
- keeping backup confirmation set to `true` after a successful rotation.

## Preconditions

Rotation should be allowed only when all of these are true:

- a managed SMTP password record exists;
- the current local key exists and is valid;
- the current managed SMTP secret decrypts successfully;
- configuration state is loadable and writable.

If any precondition fails, the route should reject rotation with a safe operator-facing error and leave all files unchanged.

## State And Health Semantics

Phase 18 should preserve the Phase 17 health model and extend its lifecycle semantics:

- before rotation, configuration page shows the current secret-health state;
- after successful rotation, secret health remains `backup-unconfirmed`;
- after successful rotation, warning copy should continue to guide the operator to confirm backup of the new key;
- after failed rotation, the prior secret-health state should still be renderable and SMTP operations should remain usable if they were usable before the attempt.

Recommended successful post-rotation semantics:

```json
{
  "status": "backup-unconfirmed",
  "backupConfirmed": false,
  "warning": "本地密钥尚未确认备份"
}
```

## Route And UX Behavior

Phase 18 should add one focused rotation action:

- `POST /configuration/secrets/rotate-key`
  - attempts local key rotation and managed SMTP secret re-encryption;
  - on success, resets `secretKeyBackupConfirmed` to `false`;
  - redirects back to `/configuration` with a success notice in page mode;
  - returns a safe failure response or page warning when rotation cannot proceed.

Configuration page behavior:

- secret-health section should render a rotation action only when a managed SMTP password exists;
- unhealthy secret state should not offer a misleading “successful recovery by rotation” path;
- if preconditions are not met, the action may be disabled or fail with explicit operator-safe feedback;
- the page must never render old key, new key, decrypted password, ciphertext, IV, or auth tag values.

Recommended operator-facing copy:

- success: `本地密钥已轮换，请重新确认新密钥的备份状态`
- blocked by missing or invalid key: `当前本地密钥不可用，无法执行轮换`
- blocked by undecryptable managed secret: `已保存的 SMTP 密码无法解密，无法执行轮换`

Implementation copy may add short context around these messages, but it should preserve these exact meanings and stay operator-safe.

## Atomicity And Rollback

Phase 18 should prefer an all-or-nothing write pattern.

Minimum safety expectation:

- do not overwrite the existing `.secret-key` until the new encrypted SMTP payload is ready;
- do not leave the service with a new key and old ciphertext mismatch after a failed attempt;
- do not clear the existing managed SMTP password on failure;
- do not change `secretKeyBackupConfirmed` on failure.

Recommended file-write sequence:

1. decrypt current managed SMTP password using current key;
2. generate new key in memory;
3. build new encrypted secret record in memory;
4. write candidate secret payload and key via temporary files in `OPENPET_DATA_DIR`;
5. replace active files only after both temp artifacts are ready;
6. persist configuration metadata update last.

The implementation does not need a full transaction engine, but it should preserve a clear rollback path if any write fails.

## Recovery Semantics

Phase 18 should treat rotation as a recovery-friendly maintenance operation, not a secret rescue tool.

This means:

- rotation is not a supported way to fix already-corrupt key/secret material;
- if the current managed SMTP password cannot be decrypted, the operator must restore SMTP configuration through another future path rather than forcing rotation;
- rotation succeeds only from a healthy starting state;
- successful rotation should leave SMTP operational routes and send-now behavior unchanged except for key material refresh.

## Suggested Implementation

- Extend `service/storage/secret-store.js` with a dedicated rotation helper that:
  - validates current key and managed secret;
  - decrypts current password;
  - generates a new local key;
  - re-encrypts the password;
  - writes replacement artifacts safely;
  - never exposes decrypted secret material beyond process memory.
- Update `service/app.js` to:
  - add `POST /configuration/secrets/rotate-key`;
  - reset `notifications.secretKeyBackupConfirmed` on success;
  - treat rotation as a configuration-page workflow that redirects to `/configuration` on success and re-renders `/configuration` with operator-safe feedback on failure.
- Update `service/views/configuration.js` to:
  - show the rotation control in the secret-health section;
  - show success and failure feedback using the normalized secret-health model.
- Keep `service/storage/configuration-store.js` responsible only for configuration metadata persistence.

## Security And Privacy

- Rotation must not introduce any raw-key export, download endpoint, or hidden debug output.
- Logs, notices, errors, delivery history, and SMTP operational history must remain secret-free.
- Temporary rotation files, if used, should stay inside `OPENPET_DATA_DIR` and be cleaned up on failure.
- Rotation should not preserve the old key in an operator-visible location after success.

## Verification

Required gates:

- secret-store tests for:
  - successful key rotation preserving decryptability of the managed SMTP password;
  - resetting backup-confirmation semantics at the route level after success;
  - rejecting rotation when no managed SMTP password exists;
  - rejecting rotation when current key is invalid;
  - rejecting rotation when managed SMTP secret is undecryptable;
  - leaving prior active files usable after simulated write failure.
- configuration page tests proving:
  - rotation control renders only in meaningful secret-health states;
  - successful rotation shows a re-backup notice without leaking secret material;
  - failed rotation shows operator-safe feedback without changing existing unhealthy state.
- route tests proving:
  - `POST /configuration/secrets/rotate-key` rotates healthy local secret state and redirects back to `/configuration`;
  - successful rotation resets `secretKeyBackupConfirmed` to `false`;
  - failed rotation leaves configuration metadata and secret files unchanged.
- regression checks proving:
  - SMTP test connection, test Email, and send-now still work after successful rotation;
  - corrupt secret-state failures continue to redact sensitive material;
  - `configuration.json` still stores only metadata, never raw secret values.
