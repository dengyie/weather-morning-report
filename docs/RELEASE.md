# Weather Morning Report Release Notes

## 1. Release Target

- Compatibility package format: `.openpet-plugin.zip`
- Unified extension package format: `.openpet-extension.zip`
- Compatibility artifact: `release/weather-morning-report.openpet-plugin.zip`
- Unified extension artifact: `release/weather-morning-report.openpet-extension.zip`
- Compatibility plugin root: `openpet-plugin/`
- Unified extension manifest: `extension/plugin.json`
- Required compatibility package files: `plugin.json`, `config.schema.json`, `index.js`, `README.md`
- Optional package file: `signature.json`

Release artifacts must stay aligned with `docs/PLUGIN_CONTRACT.md`.

## 2. Local Preflight

Run from `/Users/mango/project/codex/weather-morning-report`:

```bash
npm test
npm run build
npm run lint
npm run typecheck
npm run package:plugin
npm run package:extension
npm run lint:extension
git diff --check
```

Expected result:

- All tests pass.
- `openpet-plugin/index.js` is regenerated before artifact linting.
- `release/weather-morning-report.openpet-plugin.zip` is regenerated.
- `release/weather-morning-report.openpet-extension.zip` is regenerated.
- Artifact check rejects runtime `require`, `process`, filesystem, Electron globals, and `eval` patterns.
- Extension artifact check rejects docs/tests/node_modules/release/.env payloads and verifies command/service/dashboard paths.

## 3. OpenPet Validation

Run from `/Users/mango/project/codex/OpenPet`:

```bash
npm run validate:plugin -- /Users/mango/project/codex/weather-morning-report/openpet-plugin
npm run validate:plugin -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-plugin.zip
npm run validate:plugin -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-extension.zip
```

This validates package structure, manifest, safe paths, permissions, network allowlist, extension entries, zip safety, signature metadata state, file hashes, and package hash through OpenPet's own validation code.

CI/release workflows validate package artifacts against OpenPet `main`. The runtime smoke test can still point `OPENPET_REPO_ROOT` at the temporary OpenPet runtime-service branch until those service lifecycle APIs are available on `main`; this must not replace main-branch package validation.

## 4. Submission Rehearsal

For OpenPet catalog or reviewer handoff, generate reviewer artifacts from `/Users/mango/project/codex/OpenPet`.

Compatibility plugin bundle:

```bash
npm run create-plugin-submission-report -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-plugin.zip --output /Users/mango/project/codex/weather-morning-report/release/plugin-submission-report.md
npm run create-plugin-submission-pr -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-plugin.zip --output /Users/mango/project/codex/weather-morning-report/release/plugin-submission-pr.md
npm run create-plugin-submission-bundle -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-plugin.zip --output-dir /Users/mango/project/codex/weather-morning-report/release/plugin-submission-bundle
npm run validate-plugin-submission-bundle -- /Users/mango/project/codex/weather-morning-report/release/plugin-submission-bundle --require-ready
```

Unified extension bundle:

```bash
npm run create-plugin-submission-bundle -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-extension.zip --output-dir /Users/mango/project/codex/weather-morning-report/release/extension-submission-bundle
npm run validate-plugin-submission-bundle -- /Users/mango/project/codex/weather-morning-report/release/extension-submission-bundle --require-ready
```

Use `--require-signature` only if the release policy requires `signature.json` hash metadata.

## 5. Artifact Policy

The release zip must not include:

- `src/`
- `tests/`
- `node_modules/`
- Python source or tests
- Docker, compose, or systemd files
- `.git/`
- temporary files

The unified extension zip must include active runtime files needed by declared entries: `commands/`, `core/`, `rendering/`, `service/`, `static/`, `compat/openpet-main.js`, `package.json`, `plugin.json`, `config.schema.json`, and `README.md`.

The GitHub tag release workflow must upload both `release/weather-morning-report.openpet-plugin.zip` and `release/weather-morning-report.openpet-extension.zip`.

The source of truth is the repository source plus build/package scripts. Do not hand-edit generated zips or `openpet-plugin/index.js` for release fixes.

## 6. Versioning Notes

- Patch/minor versions must keep existing command ids stable.
- New commands should be additive.
- New permissions or network hosts must update `docs/PLUGIN_CONTRACT.md`, README, and release notes before shipping.
- OpenPet may disable an updated plugin until the user re-enables it when permissions or hosts change.
- Keep `.openpet-plugin.zip` and `.openpet-extension.zip` command ids aligned unless intentionally deprecating the legacy compatibility path.

## 7. Remaining Release TODO

- Decide whether this release is submitted as the unified extension package, the compatibility plugin package, or both.
- Add `signature.json` hash metadata if the target review lane requires signed package coverage.
- Run a real Electron Control Center smoke before public release: install package, open dashboard, start/stop service, check health/logs, run `status`.
- Generate and validate submission bundle plus maintainer approval record for the chosen artifact.
