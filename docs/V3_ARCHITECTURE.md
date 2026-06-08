# Weather Morning Report v3.0 Architecture

Status: Approved for implementation  
Release type: Breaking major-version redesign  
Document date: 2026-06-07

## 1. Goal

Version 3.0 turns Weather Morning Report from a command-line application with a
temporary settings page into a self-hosted service with:

- A long-running local administration UI
- A separate long-running report worker
- Per-recipient locations, timezones, languages, and multiple schedules
- Reliable task execution, retries, deduplication, and visible run history
- Secure administrator and SMTP credential storage
- Docker Compose as the primary deployment method

The administration UI is designed for local access. It listens on the host
loopback interface by default. Public exposure, HTTPS termination, and reverse
proxy authentication remain deployment-owner responsibilities.

## 2. Breaking Upgrade

Version 3.0 is intentionally incompatible with the current configuration and
scheduling architecture.

The following compatibility layers will be removed:

- `settings.json` business configuration
- Business configuration supplied through environment variables
- Project-provided cron scheduling
- Project-provided systemd timer scheduling
- The temporary `weather-report settings` process model

Existing `preview`, `send`, and `validate-config` commands may remain, but they
must read the v3.0 SQLite configuration.

There is no requirement to build a mature automated migration flow because the
current deployment has only one known user. Existing production data may be
manually recreated in v3.0.

## 3. Process Architecture

Version 3.0 runs two independent, long-lived processes:

```text
weather-report serve-ui
├── Administration UI
├── Authentication and sessions
├── Configuration management
├── Dashboard and run history
└── Manual preview and task creation

weather-report serve-worker
├── Schedule evaluation
├── SQLite job queue consumption
├── Weather fetching and recommendation generation
├── Email delivery and retries
├── Alerts, retention cleanup, and backups
└── Worker heartbeat and global lease

Shared resources
├── SQLite database
├── External secret key file
└── Weather snapshot cache
```

The UI never sends reports directly. It writes jobs to SQLite, and the worker
performs all weather fetching and delivery work.

The worker replaces cron and systemd timers. Docker or systemd is responsible
only for keeping the UI and worker processes running.

## 4. Deployment

### 4.1 Primary Deployment

Docker Compose is the primary supported deployment method.

The default Compose stack contains:

- `ui`: long-running administration UI
- `worker`: long-running report worker
- A persistent data volume shared by both services

The UI must be published only on host loopback by default:

```text
127.0.0.1:8766:8766
```

The worker exposes no network port.

### 4.2 Advanced Deployment

Native deployment may provide two systemd services:

- `weather-morning-report-ui.service`
- `weather-morning-report-worker.service`

No systemd timer is used.

### 4.3 First-Time Setup

Provide one initialization command:

```bash
weather-report setup
```

Docker users run:

```bash
docker compose run --rm setup
```

Setup must:

1. Create the data directory and SQLite database.
2. Apply the initial database schema.
3. Generate the external secret key with restricted permissions.
4. Interactively create the single administrator account.
5. Set an initial default timezone.
6. Print the UI address and service startup instructions.
7. Refuse to overwrite an initialized installation.

### 4.4 Database Upgrades

Database upgrades are explicit:

```bash
weather-report setup upgrade
```

An upgrade must:

1. Back up SQLite.
2. Verify the external secret key is readable.
3. Apply Alembic migrations.
4. Run consistency checks.
5. Preserve the backup and stop on failure.

UI and worker processes must refuse normal operation when the database schema
or task protocol is incompatible with the running application version.

## 5. Technology Stack

The v3.0 service uses:

- Python 3.12+
- FastAPI
- Jinja2 server-rendered templates
- HTMX for page interaction
- Project-owned static CSS
- SQLAlchemy
- Alembic
- SQLite
- `argon2-cffi` for administrator password hashing
- `cryptography` for credential encryption

Do not introduce Node.js, React, a separate frontend build pipeline, Redis, or
an external task queue.

## 6. Configuration Ownership

SQLite is the source of truth for business configuration:

- Recipients and locations
- Recipient timezone and language
- Delivery schedules
- SMTP configuration
- Provider configuration
- Branding settings
- Notification settings
- Retention settings

Environment variables are reserved for deployment-level configuration:

```dotenv
WEATHER_REPORT_DB_PATH=/data/weather-report.db
WEATHER_REPORT_SECRET_KEY_FILE=/data/secret.key
WEB_BIND=127.0.0.1
WEB_PORT=8766
```

The UI may display deployment-level values and their source, but it must not
attempt to modify process environment variables, Docker Compose files, systemd
units, or `.env` files.

## 7. Security

### 7.1 Administrator

Version 3.0 supports exactly one administrator account.

The account can only be created or reset through local CLI access:

```bash
weather-report admin create
weather-report admin reset-password
```

The UI must not provide anonymous account initialization or direct password
reset. The login page includes a "Forgot password" action that explains the
local CLI reset procedure for native and Docker deployments.

Administrator passwords:

- Are hashed with Argon2
- Are never recoverable or displayed
- May be reset without the old password when the operator has server access
- Revoke all active sessions when changed or reset

### 7.2 Sessions

- Sessions expire after 12 hours by default.
- Sessions persist across UI restarts in SQLite.
- Five consecutive login failures lock login for 15 minutes.
- Login failures never reveal whether the username exists.
- Cookies use `HttpOnly` and `SameSite=Strict`.
- Cookies use `Secure` when accessed through HTTPS.
- The UI provides "log out all devices".
- Authentication events are written to the audit history.

### 7.3 Encrypted Credentials

SMTP passwords and future provider API keys are encrypted before storage in
SQLite.

The encryption key lives outside the database in a local key file. It:

- Is generated by `weather-report setup`
- Is readable only by the service account
- Is never included in normal database backups
- Must be backed up separately by the operator

If the key is lost, encrypted credentials cannot be recovered. Non-sensitive
configuration remains usable, but credentials must be entered again.

The UI never displays an existing SMTP password. It only permits replacement.

## 8. Administration UI

The UI is a lightweight operations console, not only a settings form.

### 8.1 Dashboard

The dashboard shows:

- UI and worker component versions
- Database schema and task protocol compatibility
- Database and secret-key readiness
- Worker instance ID, heartbeat, and last activity
- Today’s recipient schedules
- Sent, skipped, retrying, and failed jobs
- Next planned sends
- Recent weather-provider and SMTP errors
- Old cron or systemd timer conflict warnings
- Manual preview, send, and retry actions

### 8.2 Configuration Pages

The UI manages:

- Recipients
- Locations
- Timezones
- Languages
- Schedules
- SMTP
- Weather providers
- Branding
- Webhook notifications
- Backup and retention status

Recipients and schedules use soft deletion. Archived items can be viewed and
restored. Deleting a recipient disables all associated schedules.

### 8.3 Manual Sending

Manual sending must:

1. Select a recipient and report type.
2. Generate and display a preview.
3. Require explicit confirmation.
4. Enqueue a worker job.

Manual sends always execute regardless of the schedule's `changes_only`
policy. They are recorded in run history but do not satisfy or alter automatic
schedule deduplication.

### 8.4 Health Endpoints

Provide minimal unauthenticated health endpoints:

```text
GET /health/live
GET /health/ready
```

They return only simple health states and never expose paths, versions,
configuration, recipients, or error details.

Do not provide a public HTTP API. FastAPI OpenAPI, Swagger, and ReDoc are
disabled in production. Internal UI and HTMX routes do not promise external
compatibility.

## 9. Internationalization and Branding

The first v3.0 release supports Chinese and English:

- UI language defaults from the browser and can be fixed by the administrator.
- Each recipient selects their report language.
- Missing translations fall back to English.
- Backend failures use stable error codes; templates translate user-facing
  messages.

Administrators may configure limited branding:

- Report title
- Greeting visibility
- Footer text
- Accent color
- Data-source visibility

Administrators cannot edit raw HTML, Jinja templates, or executable template
code.

## 10. Recipient and Schedule Model

Each recipient has:

- Name
- Email address
- Weather location display name
- Weather provider query
- Required IANA timezone
- Report language
- Enabled state
- One or more schedules

The timezone is always selected explicitly by the administrator. It is not
automatically inferred or changed when the weather location changes.

Each schedule has:

- A local send time
- A report type
- A send policy
- An enabled state

Recipients may have multiple schedules per day.

Supported report types:

- `morning`: from send time through 22:00, emphasizing morning, midday, and
  evening
- `midday`: from send time through 22:00, emphasizing afternoon and evening
- `evening`: from send time through the next day at 10:00, emphasizing tonight
  and the next morning

Expired periods are omitted. When next-day data is unavailable, the report
states that it is unavailable rather than inventing advice.

Supported send policies:

- `always`: always send at the scheduled time
- `changes_only`: send only when action-relevant weather signals have changed

Defaults:

- `morning`: `always`
- `midday`: `changes_only`
- `evening`: `changes_only`

## 11. Change Detection

`changes_only` compares the candidate report with the recipient's most recent
successfully sent report.

Comparison uses structured action signals, not rendered wording:

- Highest risk level
- Umbrella recommendation level
- Sunscreen recommendation level
- Clothing recommendation level
- Target-period precipitation risk
- Thunderstorm state
- Strong-wind state
- Dangerous-heat state

A send is triggered only when one or more signals cross a meaningful
threshold. Small temperature changes, wording differences, or description-only
changes do not trigger delivery.

Skipped jobs are recorded with the reason "no meaningful weather change".

## 12. Worker and Job Queue

### 12.1 SQLite Queue

UI actions and scheduled work use a SQLite-backed job queue.

```text
UI or scheduler creates job
→ Worker transactionally claims job
→ Worker fetches weather and renders report
→ Worker sends or skips report
→ Worker updates job and run history
```

Job claiming uses leases so an interrupted job can be recovered after its
lease expires.

### 12.2 Single Worker

Version 3.0 supports one machine and exactly one active worker.

- The worker acquires a global SQLite lease.
- It renews the lease every 30 seconds.
- A second worker refuses to start while the lease is valid.
- A replacement worker may take over after lease expiry.
- Multi-host SQLite and parallel workers are unsupported.

### 12.3 Deduplication

Automatic jobs use this logical uniqueness key:

```text
recipient_id + schedule_id + local_report_date
```

Completed automatic jobs are never sent twice.

### 12.4 Retry Policy

On failure, retry after:

```text
5 minutes, 15 minutes, 30 minutes, 60 minutes
```

Stop retrying two hours after the scheduled time. After retries are exhausted,
mark the job failed and notify the administrator.

Worker downtime is not backfilled. When the worker restarts, it resumes with
current and future schedules only.

### 12.5 Old Scheduler Conflicts

The worker checks for recognizable legacy project cron entries and systemd
timers. If an old scheduler is active, automatic sending is blocked by default.

The dashboard shows the conflict. The administrator may explicitly ignore the
conflict and enable sending. The project does not automatically modify or
delete host cron entries or systemd units.

## 13. Weather Providers

Keep the existing provider-independent weather model and `WeatherProvider`
boundary.

The first v3.0 release implements only:

- `wttr.in`
- `wttr.is` fallback

SQLite and the UI must nevertheless model configurable providers, priority,
health status, recent failures, and encrypted provider credentials so future
providers can be added without redesigning the UI or worker.

## 14. History, Auditing, and Alerts

### 14.1 Run History

Retain run history for 90 days by default.

Store:

- Status and timestamps
- Recipient and schedule identifiers
- A snapshot of recipient name, masked email, and report type
- Subject
- Structured weather/action summary
- Sanitized error information

Do not store complete HTML or plain-text email bodies by default.

The UI supports filtering by recipient, date, report type, and status. It also
provides an immediate history cleanup action.

### 14.2 Alerts

The first v3.0 release supports:

- Dashboard alerts
- Structured standard-output logs
- Administrator email notification
- Optional generic HTTP webhook notification

Notify after retries are exhausted, or when the worker cannot operate because
of conditions such as a missing secret key or an invalid database.

Repeated identical alerts use a cooldown to avoid notification floods.

## 15. Backup and Restore

- The worker creates SQLite backups using the SQLite Online Backup API.
- Retain seven daily backups and four weekly backups by default.
- Normal backups never contain the external secret key.
- The UI provides a database-backup download action.
- The UI displays whether the operator has confirmed separate secret-key
  backup.

Restore command:

```bash
weather-report setup restore /backup/weather-report.db
```

Restore runs database migrations and consistency checks. If the external key is
missing, restore non-sensitive configuration and require encrypted credentials
to be re-entered.

## 16. Suggested Data Model

The exact schema may evolve during implementation, but it must represent:

- `app_meta`: schema, application, and task protocol versions
- `admin`: the single administrator account
- `sessions`: authenticated UI sessions
- `login_attempts` or equivalent lockout state
- `recipients`: recipient profile, location, timezone, language, archive state
- `schedules`: recipient schedules, report type, policy, archive state
- `smtp_settings`: non-sensitive SMTP fields and encrypted password
- `provider_settings`: provider priority, state, and encrypted credentials
- `branding_settings`
- `notification_settings`
- `jobs`: queue state, lease, retries, and uniqueness key
- `run_history`: sanitized delivery and skip history
- `action_signals`: structured signals used by `changes_only`
- `worker_lease`: singleton worker ownership and heartbeat
- `audit_events`: administrator security and configuration events
- `backups`: backup metadata and retention state

## 17. Required Commands

```text
weather-report setup
weather-report setup upgrade
weather-report setup restore PATH
weather-report admin create
weather-report admin reset-password
weather-report serve-ui
weather-report serve-worker
weather-report preview
weather-report send
weather-report validate-config
```

`preview`, `send`, and `validate-config` read SQLite configuration in v3.0.

## 18. Explicitly Out of Scope

The first v3.0 release does not include:

- Public internet exposure management
- Built-in TLS certificate management
- Reverse proxy configuration
- Multiple administrators or role-based access control
- Public HTTP API
- Node.js or a separate SPA frontend
- Redis or an external task queue
- Multi-host or multi-worker execution
- Automatic timezone inference
- Raw email-template editing
- Configuration import or export
- Mature migration from v0.2 configuration
- Backfilling schedules missed while the worker was stopped
- Additional weather providers beyond the existing wttr implementation

## 19. Implementation Order

1. Add dependencies, SQLite models, Alembic, and external-key encryption.
2. Implement setup, database upgrade, restore, administrator creation, and
   password reset.
3. Implement authentication, sessions, lockout, and the long-running UI shell.
4. Implement recipients, schedules, SMTP, providers, branding, and
   notification configuration.
5. Implement the SQLite job queue, worker lease, scheduler, deduplication, and
   retry behavior.
6. Extend recommendation and rendering for report types, recipient timezones,
   languages, and structured action signals.
7. Implement Dashboard, run history, manual preview/send, alerts, and health
   endpoints.
8. Implement backup retention, conflict detection, Compose, and native systemd
   services.
9. Complete automated and production acceptance validation.

## 20. Release Acceptance Criteria

Version 3.0 may replace the current VPS service only when:

- Automated test coverage is at least 85%.
- Setup, SQLite, Alembic, external key, administrator authentication, and
  password-reset flows are tested.
- UI and worker run as separate long-lived services.
- Two recipients with independent locations, timezones, languages, and
  multiple schedules are validated.
- `morning`, `midday`, and `evening` reports are validated.
- `always`, `changes_only`, retry exhaustion, deduplication, and single-worker
  locking are validated.
- Restarting the worker cannot resend a completed automatic job.
- SMTP passwords cannot be read directly from SQLite.
- Manual send requires preview and confirmation.
- Dashboard accurately shows worker heartbeat, jobs, run results, and failures.
- Docker Compose starts the complete service using the documented setup flow.
- Health checks expose no sensitive data.
- A real VPS manual delivery succeeds.
- Existing VPS cron and systemd timer schedules are disabled before the new
  worker begins automatic sending.

