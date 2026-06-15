# Weather Morning Report Release Notes

## 1. Release Target

- Package format: `.openpet-plugin.zip`
- Default artifact: `release/weather-morning-report.openpet-plugin.zip`
- Plugin root: `openpet-plugin/`
- Required package files: `plugin.json`, `config.schema.json`, `index.js`, `README.md`
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
git diff --check
```

Expected result:

- All tests pass.
- `openpet-plugin/index.js` is regenerated before artifact linting.
- `release/weather-morning-report.openpet-plugin.zip` is regenerated.
- Artifact check rejects runtime `require`, `process`, filesystem, Electron globals, and `eval` patterns.

## 3. OpenPet Validation

Run from `/Users/mango/project/codex/OpenPet`:

```bash
npm run validate:plugin -- /Users/mango/project/codex/weather-morning-report/openpet-plugin
npm run validate:plugin -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-plugin.zip
```

This validates package structure, manifest, safe paths, permissions, network allowlist, zip safety, signature metadata state, file hashes, and package hash through OpenPet's own validation code.

## 4. Submission Rehearsal

For OpenPet catalog or reviewer handoff, generate reviewer artifacts from `/Users/mango/project/codex/OpenPet`:

```bash
npm run create-plugin-submission-report -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-plugin.zip --output /Users/mango/project/codex/weather-morning-report/release/plugin-submission-report.md
npm run create-plugin-submission-pr -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-plugin.zip --output /Users/mango/project/codex/weather-morning-report/release/plugin-submission-pr.md
npm run create-plugin-submission-bundle -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-plugin.zip --output-dir /Users/mango/project/codex/weather-morning-report/release/plugin-submission-bundle
npm run validate-plugin-submission-bundle -- /Users/mango/project/codex/weather-morning-report/release/plugin-submission-bundle --require-ready
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

The source of truth is the repository source plus build/package scripts. Do not hand-edit the generated zip or `openpet-plugin/index.js` for release fixes.

## 6. Versioning Notes

- Patch/minor versions must keep existing command ids stable.
- New commands should be additive.
- New permissions or network hosts must update `docs/PLUGIN_CONTRACT.md`, README, and release notes before shipping.
- OpenPet may disable an updated plugin until the user re-enables it when permissions or hosts change.
