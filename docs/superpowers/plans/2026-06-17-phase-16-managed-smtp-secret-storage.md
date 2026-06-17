# Phase 16 Managed SMTP Secret Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add service-managed encrypted SMTP password storage with local master-key generation while preserving backward compatibility with the existing `SMTP_PASSWORD` path.

**Architecture:** Keep SMTP metadata in `configuration.json`, isolate encrypted password handling in a dedicated service secret store, and update SMTP transport resolution to prefer managed secrets before falling back to `SMTP_PASSWORD`. The HTTP layer only coordinates save/clear flows and never renders decrypted password material.

**Tech Stack:** Node.js CommonJS, Fastify, built-in `node:test`, Node `crypto`, Node `fs`.

---

## File Structure

- Create `service/storage/secret-store.js`: local master-key generation, encrypted secret load/save/clear, and decrypt helpers.
- Modify `service/app.js`: wire SMTP save/clear routes and managed-secret lookups.
- Modify `service/email/transports.js`: accept resolved SMTP password input before env fallback.
- Modify `service/views/configuration.js`: render clear-password action and password-state copy.
- Modify `tests/email-send-now.test.js`: add secret-store unit tests and SMTP password resolution tests.
- Modify `tests/service-app.test.js`: add route-level managed-secret persistence and clear-password coverage.
- Modify `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`: record Phase 16 completion after implementation and review.

### Task 1: Write Failing Secret-Store And Route Tests

**Files:**
- Modify: `tests/email-send-now.test.js`
- Modify: `tests/service-app.test.js`

- [ ] **Step 1: Write failing secret-store tests**

Add tests for:

- local master-key generation and reuse;
- SMTP password encrypt/decrypt round-trip;
- clear-password behavior;
- corrupt secret store failing safely.

- [ ] **Step 2: Write failing service tests**

Add tests for:

- SMTP settings save does not write plaintext into `configuration.json`;
- managed SMTP password enables transport use without `SMTP_PASSWORD`;
- managed SMTP password takes precedence over `SMTP_PASSWORD`;
- clear-password route removes stored secret and resets `passwordSaved`.

- [ ] **Step 3: Verify RED**

Run:

```bash
node --test --test-concurrency=1 tests/email-send-now.test.js tests/service-app.test.js
```

Expected: fail because managed secret storage and clear-password behavior do not exist yet.

### Task 2: Implement Managed SMTP Secret Storage

**Files:**
- Create: `service/storage/secret-store.js`
- Modify: `service/app.js`
- Modify: `service/email/transports.js`
- Modify: `service/views/configuration.js`

- [ ] **Step 1: Add secret-store helpers**

Implement:

- local master-key generation under `OPENPET_DATA_DIR/.secret-key`;
- encrypted SMTP password save/load/clear helpers;
- safe JSON file persistence for `secrets.json`;
- corruption and decrypt failures with operator-safe errors.

- [ ] **Step 2: Update SMTP transport password resolution**

Allow SMTP transport construction to use:

- explicit resolved password from the caller first;
- `env.SMTP_PASSWORD` second;
- existing validation when neither is available.

- [ ] **Step 3: Wire SMTP save and clear flows**

Update `POST /configuration/smtp` to:

- save encrypted password when a new password is submitted;
- keep stored password unchanged when the password field is blank;
- keep `passwordSaved` aligned with actual managed-secret presence.

Add `POST /configuration/smtp/clear-password` to:

- delete the managed SMTP password;
- set `passwordSaved` to `false`;
- redirect back to `/configuration`.

- [ ] **Step 4: Render password-state controls**

Render:

- existing saved-password hint;
- clear-password button when a managed password exists;
- no decrypted value exposure.

- [ ] **Step 5: Verify GREEN**

Run:

```bash
node --test --test-concurrency=1 tests/email-send-now.test.js tests/service-app.test.js
```

Expected: all pass.

### Task 3: Documentation, Review, Verification, Commit, Push

**Files:**
- Create: `docs/superpowers/specs/2026-06-17-phase-16-managed-smtp-secret-storage-design.md`
- Create: `docs/superpowers/plans/2026-06-17-phase-16-managed-smtp-secret-storage.md`
- Modify: `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`

- [ ] **Step 1: Add Phase 16 development record**

Document the managed SMTP secret store, transport fallback order, tests, and remaining non-goals.

- [ ] **Step 2: Run production review**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/weather-morning-report
```

Fix confirmed findings with tests first.

- [ ] **Step 3: Run full verification**

Run:

```bash
npm test
npm run build
npm run lint
npm run typecheck
npm run package:plugin
npm run package:extension
npm run lint:extension
npm run smoke:openpet-runtime -- --json
git diff --check
```

Expected: all pass.

- [ ] **Step 4: Commit, push, and create PR**

Commit on `codex/phase-16-managed-smtp-secret-storage`, push, and create a draft PR against `codex/phase-15-smtp-history-filter-export`.
