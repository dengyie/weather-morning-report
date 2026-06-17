# Phase 17 Secret Key Backup And Health UX Design

> Status: proposed on `codex/phase-17-secret-key-backup-and-health-ux`.
> Scope: Phase 17 after `docs/superpowers/specs/2026-06-17-phase-16-managed-smtp-secret-storage-design.md`.
> Non-scope: raw secret-key export/download, secret import/restore, external KMS or OS keychain integration, scheduler daemonization, dashboard authentication, and OpenPet-owned secret management.

## Goal

Phase 17 adds user-facing operational visibility for the local master key and managed SMTP secret state, so operators can understand whether managed secrets are present, healthy, and acknowledged as backed up without exposing raw key or password material.

## Product Direction

Use a safety-first observability path:

- keep local secret material service-owned and opaque;
- surface operator-visible state in the configuration workbench;
- keep backup acknowledgement as metadata, not proof of export;
- fail clearly when local key or encrypted secret state becomes unhealthy;
- preserve existing SMTP behavior and secret redaction guarantees.

This phase is about making the local secret lifecycle understandable before adding any higher-risk export or restore capability.

## User Problem

After Phase 16, the service can manage encrypted SMTP passwords locally, but operators still cannot answer basic questions from the UI:

- does the local master key exist?
- is a managed SMTP password currently stored?
- can the stored secret still be decrypted?
- has someone explicitly confirmed the key was backed up?

Today those answers are either invisible or only discoverable through runtime failures. That is workable for tests but too opaque for real operation.

## State Model

Phase 17 should introduce an explicit secret-health view model derived from:

- `OPENPET_DATA_DIR/.secret-key`
- `OPENPET_DATA_DIR/secrets.json`
- `configuration.notifications.secretKeyBackupConfirmed`

Recommended status shape:

```json
{
  "masterKey": {
    "present": true,
    "valid": true
  },
  "managedSmtpPassword": {
    "present": true,
    "healthy": true,
    "updatedAt": "2026-06-17T00:00:00.000Z"
  },
  "backupConfirmed": true,
  "warning": "",
  "status": "healthy"
}
```

Exact field names may vary, but the UI and routes should be driven by one normalized service-owned state object rather than scattered file checks.

## Health Semantics

Phase 17 should distinguish these situations:

1. **No managed secret configured**
   - no stored SMTP password;
   - no backup warning required;
   - informational state only.

2. **Managed secret healthy, backup not confirmed**
   - key exists and is valid;
   - SMTP password exists and decrypts successfully;
   - configuration page should show a warning that the local key has not been acknowledged as backed up.

3. **Managed secret healthy, backup confirmed**
   - key exists and is valid;
   - SMTP password exists and decrypts successfully;
   - configuration page should show an explicit healthy state.

4. **Managed secret unhealthy**
   - key missing, invalid, or encrypted SMTP payload cannot be decrypted;
   - configuration page should show a warning/error state with operator-safe language;
   - UI must not reveal raw ciphertext, raw key content, or stored password bytes.

## Route And UX Behavior

Phase 17 should add focused backup-confirmation actions:

- `POST /configuration/secrets/confirm-backup`
  - sets `configuration.notifications.secretKeyBackupConfirmed` to `true`;
  - redirects back to `/configuration`.

- `POST /configuration/secrets/revoke-backup-confirmation`
  - sets `configuration.notifications.secretKeyBackupConfirmed` to `false`;
  - redirects back to `/configuration`.

Configuration page behavior:

- render a secret-health section in or near the notifications area;
- show whether the local master key exists;
- show whether a managed SMTP password exists;
- show last-updated metadata when a managed password is healthy;
- show a warning when backup is not confirmed for an active managed secret;
- show a warning/error when the managed secret is unhealthy;
- show confirm/revoke backup actions according to current state;
- never render raw key, password, ciphertext, IV, or auth tag values.

## Error Handling

Health inspection should be safe to render during ordinary page loads:

- missing key with no managed secret is informational, not fatal;
- missing or corrupt key with a managed secret should be reported as unhealthy state;
- corrupt `secrets.json` or invalid encrypted SMTP payload should be reported as unhealthy state;
- configuration page should remain renderable even when secret state is unhealthy;
- SMTP operational paths should keep the Phase 16 behavior of explicit safe failure on corrupt managed secrets.

This means Phase 17 should separate **health inspection for UI** from **strict secret loading for SMTP operations**.

## Backup Confirmation Semantics

`secretKeyBackupConfirmed` remains a human acknowledgement:

- it means an operator claims the local key has been backed up;
- it does not prove export actually occurred;
- changing SMTP passwords should not automatically clear the confirmation in this phase;
- clearing the managed SMTP password should not automatically delete the master key in this phase.

That keeps the phase narrow and avoids inventing false automation semantics around backup state.

## Suggested Implementation

- Extend `service/storage/secret-store.js` with read-only health inspection helpers for:
  - key presence/validity;
  - managed SMTP secret presence;
  - managed SMTP secret decryptability;
  - safe status normalization.
- Update `service/app.js` to:
  - load the normalized secret-health state for `/configuration`;
  - add backup-confirmation routes;
  - preserve existing notifications save behavior.
- Update `service/views/configuration.js` to:
  - render a secret-health section and backup-confirmation actions;
  - show warnings and healthy state copy using the normalized model.
- Keep `service/storage/configuration-store.js` responsible only for configuration JSON persistence.

## Security And Privacy

- UI health inspection must never emit raw secret material.
- HTTP responses, logs, delivery history, and SMTP operational history must remain secret-free.
- Backup confirmation actions must not create any new export endpoint or downloadable raw key artifact.
- Corruption warnings should use operator-safe phrases such as:
  - `本地密钥缺失或无效`
  - `已保存的 SMTP 密码无法解密`

## Verification

Required gates:

- secret-store tests for normalized health state across:
  - no key and no managed secret;
  - healthy key and healthy managed secret;
  - corrupt key;
  - corrupt managed secret payload.
- configuration page tests proving:
  - secret-health section renders without leaking secret material;
  - backup warning appears when a managed secret exists without confirmation;
  - healthy state appears when backup is confirmed;
  - unhealthy state appears when key or managed secret is corrupted.
- route tests proving:
  - confirm-backup toggles `secretKeyBackupConfirmed` to `true`;
  - revoke-backup-confirmation toggles it back to `false`;
  - configuration remains renderable when secret health is degraded.
- regression checks proving:
  - SMTP operational routes still fail safely for corrupt managed secrets;
  - configuration JSON stores only acknowledgement metadata, not raw secret material.
