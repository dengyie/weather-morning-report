# Phase 6 Scheduler Design

> Status: proposed and implemented on `codex/phase-6-scheduler`.
> Scope: Phase 6 of `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`.
> Non-scope: unified OpenPet package lifecycle, long-running daemon process, SQLite migration, real SMTP transport, dashboard auth.

## Goal

Phase 6 adds the service-owned scheduler queue layer needed for scheduled Email delivery while preserving the current JSON storage boundary.

The first implementation should be deterministic and testable: automatic due-job enqueueing, duplicate suppression, worker/job leases, bounded retries, uncertain-delivery safety, and a dashboard-visible queue/worker status.

## Active Capabilities

- Store scheduler state under `OPENPET_DATA_DIR/scheduler-state.json`.
- Enqueue automatic Email jobs from Phase 4 schedules when the recipient's local time reaches `localSendTime`.
- Suppress duplicate automatic jobs by recipient id, schedule id, report type, and local report date.
- Allow manual jobs to bypass `changes_only`.
- Claim jobs with a job lease so stuck workers can be recovered before delivery begins.
- Mark delivery-started jobs as `dispatching`.
- Treat expired `dispatching` jobs as `delivery_result_unknown` and never auto-claim them again.
- Retry ordinary pre-delivery failures with bounded delays.
- Expose queue/worker status through:
  - `GET /scheduler`
  - `POST /scheduler/enqueue-due`

## Storage Shape

`scheduler-state.json` should contain:

```json
{
  "schemaVersion": 1,
  "jobs": [],
  "workerLease": null
}
```

Job records should include:

- `id`
- `kind`: `automatic` or `manual`
- `status`: `pending`, `running`, `dispatching`, `retrying`, `sent`, `skipped`, `failed`, or `delivery_result_unknown`
- `recipientId`
- `scheduleId`
- `reportType`
- `sendPolicy`
- `localReportDate`
- `dedupeKey`
- `scheduledAt`
- `availableAt`
- `attemptCount`
- `leaseOwner`
- `leaseExpiresAt`
- `lastErrorCode`
- `lastErrorMessage`

Do not store Email HTML bodies or SMTP secrets in scheduler state.

## Time Handling

Use JavaScript `Intl.DateTimeFormat` with recipient timezone to compute:

- local date key as `YYYY-MM-DD`
- local time key as `HH:MM`

The scheduler should enqueue only at the exact configured minute. It should not backfill missed minutes in Phase 6.

## Retry Policy

Use bounded retry delays:

- 5 minutes
- 15 minutes
- 30 minutes
- 60 minutes

After the final retry is exhausted, mark the job `failed`.

If the job was already in `dispatching`, do not retry. Mark it `delivery_result_unknown` with a redacted diagnostic message.

## Testing Requirements

Use TDD.

Required tests:

- automatic jobs enqueue once per local date and schedule minute;
- missed minutes are not backfilled;
- duplicates are suppressed;
- worker leases block a second active worker and allow expired takeover;
- job leases allow recovery before delivery begins;
- retry delays are bounded and then exhausted;
- `dispatching` lease expiry becomes `delivery_result_unknown` and is not claimable;
- queue status reports pending/running/retrying/sent/skipped/failed/unknown counts and worker activity;
- scheduler dashboard renders queue and worker status;
- package boundary remains command-only.

## Review And Release Gates

Before Phase 6 is committed:

1. Run `npm ci`, `npm test`, `npm run build`, `npm run lint`, `npm run typecheck`, `npm run package:plugin`, and `git diff --check`.
2. Use `production-code-quality-review` on the Phase 6 diff.
3. Fix confirmed findings.
4. Update `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md` with the Phase 6 development record.
5. Commit and push `codex/phase-6-scheduler`.
