# Phase 8 OpenPet Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the unified extension zip pass the current sibling OpenPet validator and document remaining runtime smoke evidence.

**Architecture:** Keep Phase 7 local validation and package scripts. Add one OpenPet validator integration test and align manifest assets with OpenPet's literal path rules.

**Tech Stack:** Node.js CommonJS, built-in `node:test`, sibling OpenPet `npm run validate:plugin`, zip packaging scripts.

---

## Task 1: OpenPet Validator Integration

**Files:**
- Create: `tests/openpet-extension-validate.test.js`
- Modify: `extension/plugin.json`

- [x] **Step 1: Write failing test**

Create a test that runs `npm run package:extension`, then validates `release/weather-morning-report.openpet-extension.zip` through `../OpenPet`.

- [x] **Step 2: Verify RED**

Run:

```bash
npm test -- tests/openpet-extension-validate.test.js
```

Expected: fail with `Plugin asset file does not exist` while assets still use glob patterns.

- [x] **Step 3: Align manifest assets**

Change `extension/plugin.json` assets from glob patterns to literal paths:

```json
"assets": ["static", "service/views", "README.md"]
```

- [x] **Step 4: Verify GREEN**

Run:

```bash
npm test -- tests/openpet-extension-validate.test.js
npm run package:extension
npm run lint:extension
```

Expected: OpenPet validator and local extension validator pass.

## Task 2: Documentation, Review, Verification, Commit, Push

**Files:**
- Modify: `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`
- Review all Phase 8 files.

- [x] **Step 1: Add Phase 8 development record**

Append `## 13.9 Phase 8 Development Record` after Phase 7. Include OpenPet validator pass, literal assets alignment, retained local validator, and runtime smoke evidence gaps.

- [x] **Step 2: Run production review**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/weather-morning-report
```

Fix confirmed findings with tests first.

- [x] **Step 3: Run full verification**

Run:

```bash
npm ci
npm test
npm run build
npm run lint
npm run typecheck
npm run package:plugin
npm run package:extension
npm run lint:extension
git diff --check
```

Expected: all pass.

- [x] **Step 4: Commit and push**

Run:

```bash
git add docs extension tests
git commit -m "Align unified package with OpenPet validator"
git push -u origin codex/phase-8-openpet-alignment
```

Expected: branch pushed and ready for a draft PR against `codex/phase-7-unified-package`.
