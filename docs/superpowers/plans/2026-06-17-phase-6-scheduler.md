# Phase 6 Scheduler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a JSON-backed service-owned scheduler queue with due-job enqueueing, leases, bounded retries, uncertain-delivery safety, and dashboard-visible queue status.

**Architecture:** Keep scheduler behavior in focused service modules under `service/scheduler/`. Persist queue state in `OPENPET_DATA_DIR/scheduler-state.json` while preserving Phase 5 delivery history separately. Expose explicit service routes for queue visibility and manual due-job enqueueing; do not start a daemon loop in Phase 6.

**Tech Stack:** Node.js CommonJS, Fastify 5, built-in `node:test`, built-in `node:fs`, `Intl.DateTimeFormat` for timezone-local schedule checks.

---

## File Structure

- Create `service/scheduler/time.js`: timezone-local date/time helpers.
- Create `service/scheduler/state-store.js`: scheduler-state JSON load/save/append helpers.
- Create `service/scheduler/queue.js`: enqueue, claim, lease, retry, complete, fail, status logic.
- Create `service/views/scheduler.js`: queue/worker status page.
- Create `tests/scheduler-queue.test.js`: scheduler queue behavior.
- Modify `service/app.js`: add `GET /scheduler` and `POST /scheduler/enqueue-due`.
- Modify `service/views/dashboard.js`: link to scheduler dashboard.
- Modify `package.json`: include scheduler files in `npm run typecheck`.
- Modify `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`: record Phase 6 completion after implementation/review.

## Task 1: Scheduler Time And State

**Files:**
- Create: `service/scheduler/time.js`
- Create: `service/scheduler/state-store.js`
- Create: `tests/scheduler-queue.test.js`

- [ ] **Step 1: Write failing tests**

Add tests for timezone-local `localDateKey()`, `localTimeKey()`, missing-state defaults, save/load, and bounded job persistence.

- [ ] **Step 2: Verify RED**

Run:

```bash
npm test -- tests/scheduler-queue.test.js
```

Expected: fail because scheduler modules do not exist.

- [ ] **Step 3: Implement time and state modules**

Implement:

- `localDateKey(date, timezone)`
- `localTimeKey(date, timezone)`
- `schedulerStatePath(paths)`
- `createDefaultSchedulerState()`
- `loadSchedulerState(paths)`
- `saveSchedulerState(paths, state)`

- [ ] **Step 4: Verify GREEN**

Run:

```bash
npm test -- tests/scheduler-queue.test.js
```

Expected: time/state tests pass.

## Task 2: Due Job Enqueue And Status

**Files:**
- Modify: `service/scheduler/queue.js`
- Modify: `tests/scheduler-queue.test.js`

- [ ] **Step 1: Write failing tests**

Add tests that seed Phase 4 configuration and assert:

- due schedules enqueue one automatic job at the recipient local minute;
- the same schedule does not enqueue twice for the same local report date;
- missed minutes are not backfilled;
- queue status counts pending jobs.

- [ ] **Step 2: Verify RED**

Run:

```bash
npm test -- tests/scheduler-queue.test.js
```

Expected: fail because queue behavior is missing.

- [ ] **Step 3: Implement enqueue and status**

Implement:

- `enqueueDueJobs(paths, { now })`
- `queueStatus(paths, { now })`
- dedupe key format: `automatic:<recipientId>:<scheduleId>:<reportType>:<localReportDate>`

- [ ] **Step 4: Verify GREEN**

Run:

```bash
npm test -- tests/scheduler-queue.test.js
```

Expected: enqueue/status tests pass.

## Task 3: Leases, Retries, And Uncertain Delivery

**Files:**
- Modify: `service/scheduler/queue.js`
- Modify: `tests/scheduler-queue.test.js`

- [ ] **Step 1: Write failing tests**

Add tests for:

- active worker lease blocks another worker;
- expired worker lease can be taken over;
- pending jobs can be claimed;
- expired running job leases can be recovered before delivery;
- retry delays are 5, 15, 30, 60 minutes and then failed;
- `dispatching` expiry becomes `delivery_result_unknown` and is not claimable.

- [ ] **Step 2: Verify RED**

Run:

```bash
npm test -- tests/scheduler-queue.test.js
```

Expected: fail until lease/retry functions exist.

- [ ] **Step 3: Implement lease and retry functions**

Implement:

- `acquireWorkerLease(paths, instanceId, { now })`
- `renewWorkerLease(paths, instanceId, { now })`
- `releaseWorkerLease(paths, instanceId)`
- `claimJob(paths, instanceId, { now })`
- `beginDelivery(paths, jobId, instanceId, { now })`
- `completeJob(paths, jobId, instanceId, { status, now })`
- `failJob(paths, jobId, instanceId, { errorCode, errorMessage, now })`
- `failUncertainDeliveries(paths, { now })`

- [ ] **Step 4: Verify GREEN**

Run:

```bash
npm test -- tests/scheduler-queue.test.js
```

Expected: scheduler queue tests pass.

## Task 4: Scheduler Dashboard Routes

**Files:**
- Create: `service/views/scheduler.js`
- Modify: `service/app.js`
- Modify: `service/views/dashboard.js`
- Modify: `tests/service-app.test.js`

- [ ] **Step 1: Write failing tests**

Add tests that:

- `GET /scheduler` renders queue status and worker status;
- `POST /scheduler/enqueue-due` returns created job count;
- dashboard links to `/scheduler`.

- [ ] **Step 2: Verify RED**

Run:

```bash
npm test -- tests/service-app.test.js
```

Expected: fail because routes/views are missing.

- [ ] **Step 3: Implement routes and views**

Add:

- `renderSchedulerPage({ status })`;
- `GET /scheduler`;
- `POST /scheduler/enqueue-due`;
- dashboard link to scheduler.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
npm test -- tests/service-app.test.js
```

Expected: service tests pass.

## Task 5: Review, Verification, Docs, Commit, Push

**Files:**
- Modify: `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`
- Modify: `package.json`
- Review all Phase 6 files.

- [ ] **Step 1: Update typecheck coverage**

Add scheduler modules and view to `npm run typecheck`.

- [ ] **Step 2: Add Phase 6 development record**

Append `## 13.7 Phase 6 Development Record` after Phase 5. Include queue storage, enqueue/dedupe, leases, retries, uncertain delivery, dashboard routes, test coverage, review status, and unchanged command-plugin package boundary.

- [ ] **Step 3: Run production review**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/weather-morning-report
```

Inspect scheduler queue, state persistence, routes, tests, docs, and package boundary. Fix confirmed findings.

- [ ] **Step 4: Run full verification**

Run:

```bash
npm ci
npm test
npm run build
npm run lint
npm run typecheck
npm run package:plugin
git diff --check
```

Expected: all pass.

- [ ] **Step 5: Commit and push**

Run:

```bash
git add docs package.json service tests
git commit -m "Implement Phase 6 scheduler queue"
git push -u origin codex/phase-6-scheduler
```

Expected: branch pushed and ready for a draft PR against `codex/phase-5-email-delivery`.
