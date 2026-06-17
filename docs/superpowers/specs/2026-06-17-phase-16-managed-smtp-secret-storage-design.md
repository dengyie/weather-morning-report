# Phase 16 Managed SMTP Secret Storage Design

> Status: approved on `codex/phase-16-managed-smtp-secret-storage`.
> Scope: Phase 16 of `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`.
> Non-scope: OpenPet-owned secret management, external KMS or Keychain integration, scheduler daemonization, provider OAuth, and dashboard authentication.

## Goal

Phase 16 upgrades SMTP password handling from runtime-only environment injection to service-managed encrypted secret storage while preserving backward compatibility with the existing `SMTP_PASSWORD` workflow.

## Product Direction

Use a compatibility-first migration path:

- keep SMTP metadata in `configuration.json`;
- move raw SMTP password persistence into a separate encrypted service-owned secret store;
- generate a local master key inside `OPENPET_DATA_DIR`;
- prefer the service-managed SMTP password for transport operations;
- fall back to `SMTP_PASSWORD` when no managed password is stored;
- continue to keep passwords out of configuration HTML, logs, HTTP responses, delivery history, and SMTP operational history.

This keeps the current SMTP workflow usable while letting the extension own its own secrets without depending on OpenPet secret APIs.

## Storage Model

Add two service-owned files under `OPENPET_DATA_DIR`:

- `.secret-key`
  - generated on first use;
  - random local master key for encrypting secrets;
  - written with restrictive permissions when possible.
- `secrets.json`
  - JSON object of encrypted service-owned secrets;
  - initial scope only needs SMTP password material.

Recommended secret shape:

```json
{
  "smtpPassword": {
    "algorithm": "aes-256-gcm",
    "keyId": "local",
    "iv": "<base64>",
    "tag": "<base64>",
    "ciphertext": "<base64>",
    "updatedAt": "2026-06-17T00:00:00.000Z"
  }
}
```

The exact field names may vary, but the store must include enough information to decrypt later without storing raw password bytes.

## Secret Store Semantics

- Saving SMTP settings with a non-empty password writes or overwrites the encrypted SMTP password record.
- Saving SMTP settings with an empty password keeps the current stored password unchanged when `passwordSaved` is already true.
- Submitting an explicit clear-password action removes the stored SMTP password and updates configuration state to `passwordSaved: false`.
- Missing or corrupt secret-store files should fail safely with redacted operator-facing errors.
- Secret store logic should remain isolated from SMTP transport construction and HTTP rendering.

## Transport Resolution

SMTP transport password lookup should use this order:

1. managed decrypted SMTP password from the secret store;
2. `env.SMTP_PASSWORD` fallback;
3. no password available.

Behavior expectations:

- username without any available password should still fail when password is required;
- existing tests that validate `SMTP_PASSWORD` compatibility should continue to pass;
- when a managed password exists, it should take precedence over `SMTP_PASSWORD`.

## Route And UI Behavior

The existing `/configuration/smtp` form remains the main update surface.

Phase 16 should add a focused clear-password action:

- `POST /configuration/smtp/clear-password`
- removes the managed SMTP password;
- redirects back to `/configuration` in page mode;
- preserves the rest of SMTP metadata.

Configuration page behavior:

- continue to show `已保存，留空保持不变` when a managed password exists;
- show a clear-password button only when a managed password exists;
- never render the decrypted secret.

## Security And Error Handling

- All thrown errors from secret loading, decryption, save, and clear operations must be redacted before reaching HTTP or persisted history surfaces.
- `configuration.json` must never contain raw SMTP password text.
- `secrets.json` must never store plaintext password text.
- delivery history and SMTP operational history must remain unchanged and secret-free.

## Suggested Implementation

- Add `service/storage/secret-store.js` with:
  - local key generation/loading;
  - SMTP password encrypt/decrypt helpers;
  - save/load/clear helpers;
  - redaction-safe corruption handling.
- Update `service/email/transports.js` so SMTP password resolution can consume an explicit password value from the caller before falling back to `env.SMTP_PASSWORD`.
- Update `service/app.js` to:
  - save encrypted SMTP password on SMTP form submit;
  - keep existing `passwordSaved` semantics aligned with actual managed-secret state;
  - add the clear-password route;
  - pass managed SMTP passwords into SMTP operational actions and send-now transport construction.
- Keep `service/storage/configuration-store.js` focused on configuration JSON only.

## Verification

Required gates:

- secret-store unit tests for key generation, encrypt/decrypt round-trip, clear, and corrupt-store failure handling;
- service route tests proving SMTP password saves never write plaintext into `configuration.json`;
- service route tests proving a managed password enables SMTP transport without `SMTP_PASSWORD`;
- service route tests proving managed password takes precedence over `SMTP_PASSWORD`;
- service route tests proving clear-password removes the managed secret and resets `passwordSaved`;
- regression checks proving delivery history, SMTP operational history, and error responses still redact secrets.
