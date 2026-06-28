# Weather Morning Report Extension Migration Design

> Status: design proposal based on the new OpenPet developer-first extension boundary.
> Scope: Weather Morning Report repository migration from command-only OpenPet plugin to unified OpenPet extension package with Web and Email service.
> Non-scope: direct OpenPet core implementation patch.

## 1. Goal

Weather Morning Report should become a full OpenPet extension package, not only a short-lived weather command plugin.

The extension should provide:

- desktop pet weather announcements;
- Web dashboard;
- Email preview and SMTP delivery;
- scheduled reports;
- restored HTML/CSS/Email template assets;
- service-managed secrets and local data;
- OpenPet lifecycle integration through shell commands, services, dashboards, health checks, logs, and optional bridge calls.

The project should maximize third-party developer freedom while keeping OpenPet’s responsibilities honest and lightweight.

## 2. Product Shape

Weather Morning Report becomes a single extension package:

```text
plugin.json
config.schema.json
commands/
service/
web/
templates/
static/
assets/
docs/
README.md
```

OpenPet installs the package, shows the manifest, keeps it disabled by default, and can later:

- run commands;
- start/stop the service;
- open the dashboard;
- show logs and health state;
- run setup/cleanup commands when the user explicitly chooses.

## 3. Responsibilities

### 3.1 OpenPet Responsibilities

OpenPet should:

- install the extension package;
- validate structural package safety;
- show `plugin.json` declarations;
- create recommended data/cache/log directories;
- inject standard environment variables;
- run shell commands;
- start and stop service entries;
- capture stdout/stderr;
- show health state;
- open dashboard URLs;
- optionally expose minimal bridge endpoints;
- disable and uninstall the extension.

OpenPet should not:

- run setup during install;
- own SMTP credentials;
- manage every Weather service secret;
- sandbox the Weather service process;
- guarantee deletion of service-owned external data.

### 3.2 Weather Extension Responsibilities

Weather Morning Report should:

- own Web dashboard implementation;
- own SMTP/Email configuration and delivery;
- own scheduler implementation;
- own service database/cache/migration;
- own HTML and Email templates;
- own report rendering;
- use OpenPet-provided directories by default;
- disclose any additional data locations;
- provide setup and cleanup commands;
- expose health endpoint;
- optionally call OpenPet bridge for pet speech and notifications.

## 4. Current Repository Assessment

The repository currently has a clean command-only OpenPet JS plugin structure:

```text
src/
openpet-plugin/
scripts/
tests/
docs/
```

This is useful but too narrow for the renewed product goal.

The old Python/Web/Email implementation assets were removed from the active product surface during the command-plugin migration. They are still recoverable from git history and should be restored intentionally as migration assets.

Known historical assets to recover:

- `src/weather_morning_report/templates/configuration.html`;
- `src/weather_morning_report/templates/dashboard.html`;
- `src/weather_morning_report/templates/forgot_password.html`;
- `src/weather_morning_report/templates/login.html`;
- `src/weather_morning_report/templates/manual_preview.html`;
- `src/weather_morning_report/static/app.css`;
- `src/weather_morning_report/email_templates.py`;
- `src/weather_morning_report/rendering/html.py`;
- `docs/ui-preview/configuration.html`;
- related Web/Email design docs.

Recovery should not reintroduce the old Python stack as-is. It should preserve product knowledge and templates, then migrate them into the new extension service architecture.

### 4.1 Detailed Review Findings

The current command-plugin implementation is production-useful for pet speech, but incomplete for the renewed product scope.

Confirmed strengths to preserve:

- current JS core already covers weather fetch, wttr fallback, defensive parsing, period selection, recommendation thresholds, bilingual rendering, command caching, and OpenPet package validation;
- tests already cover parser edge cases, provider fallback, command behavior, bundle safety, packaging, and OpenPet validator acceptance;
- the current OpenPet compatibility package remains useful while the unified extension package is the service/dashboard path for OpenPet main.

Confirmed gaps to fix:

- no active Web dashboard;
- no active SMTP or Email delivery path;
- no active HTML Email renderer;
- no recipient/schedule management UI;
- no service-owned scheduler;
- no service database or delivery history;
- old templates were only available in git history before this review;
- current docs understate how much product behavior must be restored.

Recovered legacy assets now live under `legacy-assets/recovered/`. They are intentionally preserved as migration references, not active runtime code.

### 4.2 Recovered Asset Inventory

| Legacy Source | Recovered Path | Product Value | Migration Target |
| --- | --- | --- | --- |
| `src/weather_morning_report/templates/configuration.html` | `legacy-assets/recovered/src/weather_morning_report/templates/configuration.html` | Full settings workbench: defaults, recipients, schedules, delivery, branding, notifications | `templates/web/configuration.html` or equivalent dashboard view |
| `src/weather_morning_report/templates/dashboard.html` | `legacy-assets/recovered/src/weather_morning_report/templates/dashboard.html` | Service status, manual preview, history, backups, account controls | `templates/web/dashboard.html` |
| `src/weather_morning_report/templates/manual_preview.html` | `legacy-assets/recovered/src/weather_morning_report/templates/manual_preview.html` | Send-before-confirm preview workflow | `templates/web/manual-preview.html` |
| `src/weather_morning_report/templates/login.html` | `legacy-assets/recovered/src/weather_morning_report/templates/login.html` | Local dashboard authentication UX | Optional v1 local-token page or v2 auth page |
| `src/weather_morning_report/templates/forgot_password.html` | `legacy-assets/recovered/src/weather_morning_report/templates/forgot_password.html` | Password recovery operational copy | Optional if dashboard auth uses admin password |
| `src/weather_morning_report/static/app.css` | `legacy-assets/recovered/src/weather_morning_report/static/app.css` | Full dashboard visual system | `static/app.css` |
| `src/weather_morning_report/email_templates.py` | `legacy-assets/recovered/src/weather_morning_report/email_templates.py` | Five Email presentation choices | `rendering/email-template-options.js` |
| `src/weather_morning_report/rendering/html.py` | `legacy-assets/recovered/src/weather_morning_report/rendering/html.py` | Responsive Email HTML renderer, weather visuals, bilingual labels | `rendering/email-renderer.js` and active Email templates |
| `src/weather_morning_report/delivery/smtp.py` | `legacy-assets/recovered/src/weather_morning_report/delivery/smtp.py` | SMTP connection, STARTTLS/SSL/plain modes, test mail | `service/email/smtp-transport.js` |
| `src/weather_morning_report/jobs.py` | `legacy-assets/recovered/src/weather_morning_report/jobs.py` | Queue leases, retries, dedupe, uncertain delivery handling | `service/scheduler/queue.js` |
| `src/weather_morning_report/configuration.py` | `legacy-assets/recovered/src/weather_morning_report/configuration.py` | Recipient/schedule/provider/branding/notification validation | `service/configuration/` |
| `src/weather_morning_report/database/models.py` | `legacy-assets/recovered/src/weather_morning_report/database/models.py` | Data model for recipients, schedules, jobs, run history, backups, audit | `service/storage/schema.js` |
| `src/weather_morning_report/migrations/*` | `legacy-assets/recovered/src/weather_morning_report/migrations/` | Schema evolution reference | JS migration plan or SQLite migration scripts |
| `tests/test_*.py` | `legacy-assets/recovered/tests/` | Behavioral expectations for SMTP, config, database, jobs | JS regression tests |

### 4.3 Asset Recovery Rules

- `legacy-assets/recovered/` is a preservation area.
- Active code must not import from `legacy-assets/recovered/`.
- Active templates must be copied or ported into `templates/`, `static/`, `rendering/`, and `service/`.
- Production extension packages should exclude legacy-only files unless a release intentionally includes migration evidence.
- Every recovered asset promoted into active runtime must gain a JS test or route/rendering snapshot check.

## 5. Target Architecture

### 5.1 Package Layout

Recommended repository layout:

```text
weather-morning-report/
├── plugin.json
├── config.schema.json
├── package.json
├── commands/
│   ├── announce.js
│   ├── refresh.js
│   ├── send-email-now.js
│   ├── setup.js
│   └── cleanup.js
├── service/
│   ├── index.js
│   ├── http/
│   ├── email/
│   ├── scheduler/
│   ├── storage/
│   └── health/
├── core/
│   ├── weather-provider.js
│   ├── wttr-parser.js
│   ├── recommendation-engine.js
│   ├── period-schedule.js
│   └── report-model.js
├── rendering/
│   ├── text-renderer.js
│   ├── html-renderer.js
│   └── email-renderer.js
├── web/
│   ├── routes/
│   └── views/
├── templates/
│   ├── web/
│   └── email/
├── static/
│   └── app.css
├── legacy-assets/
│   └── recovered/
├── scripts/
├── tests/
└── docs/
```

Names can be adjusted during implementation, but the responsibility split should remain.

### 5.1.1 Active Vs Legacy Boundaries

Active runtime:

- `core/`
- `rendering/`
- `commands/`
- `service/`
- `web/`
- `templates/`
- `static/`
- root `plugin.json`
- root `config.schema.json`

Migration-only reference:

- `legacy-assets/recovered/`

Current transitional runtime:

- `src/`
- `openpet-plugin/`

The transitional runtime remains valid for compatibility. OpenPet main now supports shell-entry extension declarations, so service/dashboard work should target the active unified extension layout while keeping `src/` and `openpet-plugin/` as the legacy command adapter.

### 5.2 Core Layer

`core/` should contain pure weather and recommendation logic:

- configuration normalization;
- weather provider request planning;
- wttr parsing;
- period selection;
- recommendation scoring;
- report view model construction.

Core must avoid OpenPet-specific APIs, HTTP server details, SMTP, process environment, and file system writes.

### 5.3 Rendering Layer

`rendering/` should turn report models into:

- pet speech text;
- plain text detail;
- HTML preview;
- Email subject/body;
- dashboard cards.

Rendering should be deterministic and template-driven.

Email template options from the legacy system must be preserved:

| Value | Label | Required Status |
| --- | --- | --- |
| `1` | 暖调风格 | Required |
| `2` | 行动风格 | Required |
| `3` | 玻璃渐变 | Required |
| `4` | 极简风格 | Required |
| `5` | 仪表风格 | Required |

The first JS renderer can be implemented as escaped string templates or small renderer functions. It does not need to adopt a heavy template engine unless the migrated templates become hard to maintain.

### 5.4 Command Entries

Command entries should be shell commands.

Initial commands:

| Command | Purpose |
| --- | --- |
| `refresh` | Fetch weather and cache/report latest result. |
| `announce` | Generate weather summary and ask OpenPet pet to say it through bridge or result JSON. |
| `last` | Announce or return last cached report. |
| `status` | Return extension/service/cache status. |
| `send-email-now` | Trigger immediate Email delivery through service or local command logic. |
| `setup` | Install dependencies or initialize service data when needed. |
| `cleanup` | Optional cleanup for service-owned data. |

Commands receive stdin JSON and env variables from OpenPet.

### 5.5 Service Entry

The service provides Web/Email/scheduler capabilities.

Responsibilities:

- bind to loopback by default;
- expose `/health`;
- expose dashboard pages;
- expose report preview;
- manage SMTP configuration;
- send test Email;
- send scheduled Email reports;
- store report history;
- store scheduler state;
- write service logs;
- optionally call OpenPet bridge for pet announcements.

The service can use any suitable local stack. Since this repository is already JavaScript after the plugin refactor, Node is the preferred first implementation path.

Recommended first implementation:

- Node.js service using Fastify as the first-version HTTP framework;
- no Python runtime requirement for production;
- SQLite or JSON storage inside `OPENPET_DATA_DIR`;
- SMTP transport behind a small adapter so tests can inject fake transport;
- service-owned scheduler with one in-process worker loop;
- bounded logs and bounded report history.

If the service uses third-party npm dependencies, production packaging should prefer vendored or preinstalled dependencies. Development may use explicit setup commands.

### 5.6 Dashboard Entry

Dashboard first version:

- OpenPet opens the service URL externally or in a separate window;
- service owns routing, UI, auth, and form behavior;
- no iframe embedding or theme protocol in the first version.

Initial dashboard pages:

- status;
- report preview;
- weather settings;
- Email settings;
- SMTP test;
- scheduler settings;
- delivery history;
- logs/help.

### 5.7 Template Assets

Template policy:

- restore old templates into `legacy-assets/recovered/` first;
- migrate active templates into `templates/web/` and `templates/email/`;
- keep active static CSS in `static/`;
- add tests that active template rendering works;
- do not package legacy-only assets unless useful for migration notes or review.

The old templates are product memory, not dead code.

Promotion order:

1. Copy `app.css` into active `static/app.css`.
2. Port Email template option metadata into `rendering/email-template-options.js`.
3. Port `render_html()` behavior into `rendering/email-renderer.js`.
4. Port dashboard and configuration pages into active Web views.
5. Port manual preview flow.
6. Keep login/forgot-password as optional future UX only; the active service uses local dashboard tokens.

Acceptance criteria:

- all five Email styles render valid HTML;
- HTML renderer escapes user-controlled values;
- Chinese and English labels are preserved;
- dashboard pages do not require the old Python/Jinja runtime;
- active CSS loads from the service;
- migrated templates have tests.

## 5.8 Data Model Design

The service should restore the important domain entities from the legacy SQLite model, but it may simplify implementation details.

Required entities:

| Entity | Purpose |
| --- | --- |
| `app_meta` | schema version and application metadata |
| `recipients` | Email recipients and per-recipient location/language |
| `recipient_email_preferences` | selected Email template per recipient |
| `schedules` | local send time, report type, send policy, enabled state |
| `smtp_settings` | service-managed SMTP configuration |
| `provider_settings` | weather provider priority and health |
| `branding_settings` | title, greeting, footer, accent color, data source visibility |
| `notification_settings` | admin notification and retention settings |
| `new_user_defaults` | default values for new recipients |
| `jobs` | queued automatic/manual delivery work |
| `run_history` | delivery result history |
| `action_signals` | structured weather action signals for analytics/history |
| `worker_lease` | single-worker coordination if needed |
| `audit_events` | configuration and operational audit trail |
| `backups` | optional local backup records |

Recommended first-version storage:

- SQLite in `OPENPET_DATA_DIR/weather-morning-report.sqlite3` if migrations are needed immediately;
- otherwise JSON files are acceptable only for a smaller MVP that defers multi-recipient scheduling and queue leases.

Because Email schedules, delivery history, audit events, and retries are central product features, SQLite is the preferred production design.

## 5.9 Configuration Domains

The Web dashboard should expose these configuration domains:

| Domain | Fields |
| --- | --- |
| Defaults | location name/query, timezone, language, local send time, report type, send policy, schedule enabled |
| Recipients | name, email, location, timezone, language, enabled, archived state, Email template |
| Schedules | recipient, local send time, report type, send policy, enabled, archived state |
| SMTP | host, port, security, username, password, sender email |
| Providers | provider type, priority, enabled, health, last error |
| Branding | report title, greeting visibility, footer text, accent color, data source visibility |
| Notifications | admin email, webhook placeholder if retained, retention days, alert cooldown, backup confirmation |

The service may self-manage SMTP password storage. OpenPet should not own it.

## 5.10 Security And Local UX

The extension should stay local-first.

First-version service defaults:

- bind to `127.0.0.1`;
- generate a local dashboard token on first run;
- store the token in `OPENPET_DATA_DIR`;
- never log SMTP password or provider credentials;
- redact secret-like values in logs and status responses;
- expose `/health` without sensitive data;
- keep dashboard auth simple and service-owned.

The active service uses token-only dashboard protection for mutating routes. The legacy login pages can remain visual/product references if a later admin-password UX is needed.

## 6. Manifest Draft

Example first-version `plugin.json`:

```json
{
  "id": "weather-morning-report",
  "name": "Weather Morning Report",
  "version": "1.0.0",
  "description": "Weather reports with pet announcements, Web dashboard, scheduled Email delivery, and template-based previews.",
  "entries": {
    "commands": [
      {
        "id": "announce",
        "title": "Announce Weather",
        "command": "node commands/announce.js",
        "cwd": "."
      },
      {
        "id": "send-email-now",
        "title": "Send Email Now",
        "command": "node commands/send-email-now.js",
        "cwd": "."
      },
      {
        "id": "setup",
        "title": "Setup Weather Morning Report",
        "command": "npm install",
        "cwd": "."
      }
    ],
    "services": [
      {
        "id": "weather-service",
        "name": "Weather Morning Report Service",
        "command": "node service/index.js",
        "cwd": ".",
        "health": {
          "type": "http",
          "url": "http://127.0.0.1:8787/health"
        }
      }
    ],
    "dashboards": [
      {
        "id": "main",
        "title": "Weather Dashboard",
        "url": "http://127.0.0.1:8787"
      }
    ]
  },
  "manifest": {
    "network": ["wttr.in", "wttr.is"],
    "dataLocations": [
      {
        "path": "OPENPET_DATA_DIR",
        "description": "Report cache, service database, scheduler state, and Email delivery history."
      }
    ],
    "externalAccounts": ["SMTP provider"],
    "selfManagedSecrets": ["SMTP username", "SMTP password"],
    "schedules": ["Morning weather Email schedule managed by the service."],
    "notes": [
      "The service binds to loopback by default.",
      "SMTP credentials are managed by the service, not by the OpenPet command runner."
    ]
  },
  "config": "config.schema.json",
  "assets": [
    "templates/**",
    "static/**",
    "web/**",
    "README.md"
  ]
}
```

This is the unified extension package shape. `openpet-plugin/` remains the legacy compatibility package contract for the command-only artifact.

## 7. Web Service Design

### 7.1 HTTP Surface

Minimum routes:

| Route | Purpose |
| --- | --- |
| `GET /health` | Health check for OpenPet. |
| `GET /` | Dashboard home/status. |
| `GET /reports/latest` | Latest report view. |
| `GET /reports/preview` | Preview report without sending Email. |
| `POST /reports/refresh` | Refresh weather report. |
| `GET /settings` | Settings page. |
| `POST /settings` | Save service settings. |
| `GET /email/preview` | Email preview. |
| `POST /email/test` | Send test Email. |
| `POST /email/send-now` | Send immediate report. |
| `GET /logs` | Recent service logs. |
| `GET /configuration` | Full configuration workbench. |
| `POST /configuration/defaults` | Save defaults. |
| `POST /configuration/recipients` | Create recipient. |
| `POST /configuration/recipients/:id` | Update recipient. |
| `POST /configuration/schedules` | Create or update schedule. |
| `POST /configuration/smtp` | Save SMTP settings. |
| `POST /configuration/branding` | Save branding settings. |
| `POST /manual/preview` | Generate manual report preview. |
| `POST /manual/enqueue` | Enqueue or send confirmed manual report. |

### 7.2 Authentication

The current service uses a local token stored in the service data directory.

Rendered dashboard forms include the token as a hidden field, and mutating routes reject requests without a valid token.

Keep this simple and local-first. Do not turn the service into a public Web app.

### 7.3 Service Storage

Preferred storage:

- JSON files or SQLite inside `OPENPET_DATA_DIR`;
- no raw wttr response archives unless explicitly useful;
- report history should be bounded;
- logs should rotate or be size-limited.

### 7.4 Web Pages To Restore

| Page | Legacy Template | First-Version Status |
| --- | --- | --- |
| Dashboard | `dashboard.html` | Required |
| Configuration workbench | `configuration.html` | Required |
| Manual preview | `manual_preview.html` | Required |
| Login | `login.html` | Optional, depends on auth mode |
| Forgot password | `forgot_password.html` | Optional, depends on auth mode |

The first implementation should preserve the dashboard/workbench/manual-preview workflows before adding new UI concepts.

## 8. Email Service Design

Email features:

- SMTP host/port/secure settings;
- username/password or provider-specific settings;
- sender/recipient list;
- subject template;
- HTML body template;
- plain text fallback;
- send test;
- send now;
- scheduled send;
- delivery result history.

Secret policy:

- service may store its own SMTP credentials;
- OpenPet does not need to enumerate or own these secrets;
- service should avoid logging secret values;
- dashboard should not reveal stored secret values after save.

### 8.1 Email Rendering Contract

Email rendering must produce:

- subject;
- plain text body;
- HTML body;
- selected template id;
- selected template label;
- structured action summary.

Inputs:

- weather snapshot;
- advice/report model;
- recipient profile;
- branding settings;
- language;
- report type;
- cached/provider status.

Required template behaviors:

- support the five legacy styles;
- preserve recipient greeting controls;
- preserve footer text;
- preserve accent color;
- preserve data source visibility;
- render key period rows;
- render umbrella/sunscreen/clothing actions;
- render current temperature, feels-like, range, wind, UV, and risk where available.

### 8.2 SMTP Contract

SMTP support must include:

- `plain`;
- `starttls`;
- `ssl`;
- configurable timeout;
- optional username/password;
- test connection;
- test Email;
- fake transport for tests;
- redacted error messages for dashboard/log display.

Delivery result states:

- `sent`;
- `skipped`;
- `retrying`;
- `failed`;
- `delivery_result_unknown`.

## 9. Scheduler Design

The scheduler is service-owned.

OpenPet first version only displays what the manifest says and what health/status endpoints report.

The service should manage:

- schedule configuration;
- next run calculation;
- missed run behavior;
- retry policy;
- failure logs;
- manual send override.

### 9.1 Queue Semantics To Preserve

The legacy job queue had valuable production behavior. The JS service should preserve these semantics where practical:

- automatic jobs are deduplicated by recipient, schedule, and local report date;
- manual jobs can bypass `changes_only`;
- worker lease prevents duplicate workers from sending the same queue;
- job lease prevents one stuck job from blocking forever;
- retry delays are bounded;
- once delivery has begun, uncertain completion should not trigger unsafe automatic resend;
- run history records recipient snapshots and error details.

### 9.2 Send Policies

Required policies:

- `always`: send every scheduled report;
- `changes_only`: skip if the generated preview digest is unchanged for the recipient/report period.

The manual send flow should not be blocked by `changes_only`.

## 10. Bridge Integration

Weather extension can integrate with OpenPet through:

- command result JSON `petSay`;
- optional `OPENPET_BRIDGE_URL` calls from service;
- notifications after scheduled Email sends;
- status updates from service health.

First-version bridge usage should be small:

- pet says weather summary after manual announce;
- notification after Email send success/failure;
- status update for service health.

## 11. Packaging And Release

The extension release package should include:

- `plugin.json`;
- `config.schema.json`;
- commands;
- service code;
- active templates;
- static assets;
- README;
- package metadata;
- tests or test fixtures only if intentionally included.

The package should not require old Docker/systemd deployment paths.

Optional development-only flows may still exist outside the packaged extension:

- local dev server;
- fixture generation;
- template migration scripts;
- historical asset recovery notes.

Packaging exclusions:

- `legacy-assets/recovered/` by default;
- old Python runtime files unless explicitly included as migration evidence;
- test-only fixtures;
- generated temporary files;
- local databases;
- local SMTP credentials;
- local dashboard tokens.

## 12. Validation Strategy

Validation should cover three layers.

### 12.1 Core Tests

- wttr parsing;
- numeric missing-value handling;
- weather provider fallback;
- recommendation thresholds;
- period selection;
- report model generation.

### 12.2 Service Tests

- `/health` response;
- dashboard route rendering;
- settings save/load;
- Email preview rendering;
- SMTP send adapter with fake transport;
- scheduler next run calculation;
- delivery history bounds;
- secret redaction in logs.
- dashboard token behavior if enabled;
- `/configuration` route rendering;
- manual preview confirmation flow;
- service startup with `OPENPET_DATA_DIR`;
- health endpoint without sensitive fields.

### 12.3 Extension Package Tests

- `plugin.json` schema structure;
- entry commands are package-relative;
- service command exists;
- dashboard URL matches service port;
- active assets exist;
- package does not contain legacy-only junk;
- setup/cleanup commands are declared when needed.
- production package excludes `legacy-assets/recovered/` by default;
- package includes active templates and static CSS;
- service health URL matches manifest dashboard/service defaults.

This repository now validates the unified extension zip against the current OpenPet main `validate:plugin` command, while keeping local artifact checks as stricter package-specific guards.

## 13. Migration Phases

### Phase 1: Documentation And Asset Recovery

- Add this migration design.
- Restore old templates/static/email files into `legacy-assets/recovered/`.
- Document each recovered asset and intended active replacement.

Done when:

- recovered files are present under `legacy-assets/recovered/`;
- `legacy-assets/README.md` explains usage rules;
- this document has an asset inventory and migration target for each essential component.

### Phase 2: Shared Core Refactor

- Move current `src/` business logic into framework-neutral core/rendering modules.
- Keep current OpenPet command plugin behavior working until replacement is ready.

Done when:

- current tests still pass;
- command-plugin bundle can still be built;
- core modules have no OpenPet `ctx` dependency;
- rendering can target pet text and Email/Web view models.

### Phase 3: Service Skeleton

- Add Node service entry.
- Add `/health`.
- Add dashboard shell.
- Add data/cache/log directory handling.

Done when:

- service starts with `OPENPET_DATA_DIR`;
- `/health` returns JSON without secrets;
- logs are written to `OPENPET_LOG_DIR` or service storage;
- dashboard home loads active CSS.

### Phase 4: Web Dashboard

- Migrate templates into active Web views.
- Add settings, preview, status, and logs pages.

Done when:

- dashboard, configuration, and manual preview workflows work locally;
- active views no longer depend on Jinja/Python;
- form validation covers recipients, schedules, SMTP, branding, defaults.

### Phase 5: Email Delivery

- Add Email renderer.
- Add SMTP adapter.
- Add test send and send-now command.
- Add delivery history.

Done when:

- five Email templates render;
- fake SMTP tests pass;
- send-now records run history;
- secrets are redacted from logs and status.

### Phase 6: Scheduler

- Add service-owned scheduler.
- Add dashboard controls.
- Add failure/retry behavior.

Done when:

- automatic jobs enqueue by local time;
- duplicate jobs are suppressed;
- retries are bounded;
- uncertain delivery state avoids unsafe duplicate send;
- dashboard shows queue and worker status.

### Phase 7: Unified Extension Package

- Add unified `plugin.json` while keeping the command-only compatibility package.
- Add shell command entries.
- Add service and dashboard entries.
- Update packaging scripts.

Done when:

- package includes root `plugin.json`;
- package includes active commands/service/dashboard/templates/static assets;
- package excludes local secrets and default legacy archive;
- commands consume stdin/env and return JSON;
- service entry is declared for OpenPet's extension lifecycle.

### Phase 8: OpenPet Alignment

- Validate against the current OpenPet main extension-entry model.
- Update docs for current OpenPet implementation details.

Done when:

- package passes the current OpenPet structural validator;
- dashboard opens from OpenPet;
- service health appears in OpenPet;
- command logs and result JSON appear in OpenPet.

### Phase 9: OpenPet Runtime Smoke

- Add automated runtime smoke evidence against sibling OpenPet.
- Verify dashboard open, service lifecycle, health checks, command execution, and logs.

Done when:

- smoke script packages the unified extension and loads it through OpenPet runtime service APIs;
- dashboard `main` opens through OpenPet;
- service `weather-service` starts, returns healthy, and stops;
- command `status` runs through OpenPet command execution.

### Phase 10: Setup And Cleanup Lifecycle

- Declare setup in OpenPet's setup lifecycle surface.
- Add explicit cleanup command for service-owned local files.
- Keep cleanup dry-run by default.

Done when:

- `entries.setup` declares setup without running install-time mutations;
- cleanup reports planned files by default;
- confirmed cleanup deletes only known Weather service-owned files;
- package validation covers lifecycle command paths.

### Phase 11: Real SMTP Transport

- Activate real SMTP delivery for service-backed send-now and scheduler delivery paths.
- Keep fake transport injection for tests.
- Keep SMTP password material runtime-only.

Done when:

- default service Email transport maps SMTP configuration to a real SMTP client;
- `plain`, `starttls`, and `ssl` modes are covered by tests;
- missing SMTP host, sender, or required runtime password fails safely;
- delivery history and HTTP responses do not expose SMTP secrets.

### Phase 12: SMTP Operational Tests

- Add SMTP test connection.
- Add operational test Email.
- Expose both actions from the configuration page.

Done when:

- SMTP connection verification uses the same transport configuration path as sending;
- test Email sends a short operational message to a selected recipient;
- test Email does not write delivery history records;
- failures redact runtime SMTP secrets.

### Phase 13: SMTP Operational UX Feedback

- Turn SMTP operational actions into configuration-page workflows.
- Show human-readable success and failure feedback in the dashboard.
- Keep machine-readable JSON behavior available for non-page callers.

Done when:

- configuration page can render success notices for SMTP operational actions;
- SMTP test connection page submissions redirect back to configuration with clear success feedback;
- test Email page submissions redirect back to configuration with clear recipient-aware success feedback;
- page-mode failures stay on the configuration page with redacted, human-readable feedback.

### Phase 14: SMTP Operational History

- Persist SMTP operational checks as bounded history.
- Surface recent SMTP operational checks in the configuration page.
- Keep SMTP operational history redacted and service-owned.

Done when:

- SMTP test connection and test Email both append bounded operational history records;
- configuration page renders recent SMTP operational history;
- operational history keeps runtime SMTP secrets redacted;
- existing Email delivery history behavior remains unchanged.

## 13.1 Recommended Implementation Order

The safest development order is:

1. Preserve current command-plugin tests.
2. Restore and document legacy assets.
3. Extract core and rendering model.
4. Add Email renderer with fake data tests.
5. Add service storage schema.
6. Add service `/health`.
7. Add dashboard shell and active CSS.
8. Add configuration workbench.
9. Add SMTP fake transport and test send.
10. Add send-now command.
11. Add scheduler and queue.
12. Add unified package manifest and package script.

This order protects both current OpenPet functionality and recovered Web/Email product value.

## 13.2 Phase 1 Development Record

Phase 1 has been implemented as a documentation and preservation phase.

Implemented artifacts:

- `docs/OPENPET_EXTENSION_ECOSYSTEM_BOUNDARY.md` records the agreed OpenPet developer-first unified extension boundary.
- `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md` records this repository's migration plan.
- `legacy-assets/recovered/` preserves 26 historical Web, Email, SMTP, scheduler, database, migration, CSS, and test files recovered from commit `7d9e962`.
- `legacy-assets/README.md` documents archive rules and migration targets.
- `docs/README.md` routes maintainers to the correct current and future architecture docs.

Packaging status:

- Compatibility command-plugin packaging still includes only `openpet-plugin/plugin.json`, `openpet-plugin/config.schema.json`, `openpet-plugin/index.js`, and `openpet-plugin/README.md`.
- `legacy-assets/recovered/` is intentionally excluded from the current `.openpet-plugin.zip` artifact.
- Active runtime code must not import from `legacy-assets/recovered/`.

Validation evidence for Phase 1:

- `npm test`
- `npm run build`
- `npm run lint`
- `npm run typecheck`
- `npm run package:plugin`
- `git diff --check`
- sibling OpenPet validator against `openpet-plugin/`
- sibling OpenPet validator against `release/weather-morning-report.openpet-plugin.zip`

Python unit discovery is not part of the active validation baseline in this phase because the recovered Python files are archived migration references, not active runtime code.

## 13.3 Phase 2 Development Record

Phase 2 has started with the safe framework-neutral extraction required before adding Web and Email service code.

Implemented artifacts:

- `core/config.js`
- `core/weather-provider.js`
- `core/wttr-parser.js`
- `core/recommendation-engine.js`
- `core/period-schedule.js`
- `rendering/text-renderer.js`
- `tests/architecture-boundary.test.js`

Current boundary:

- `core/` owns weather provider, parser, configuration normalization, recommendation, and period selection logic.
- `rendering/` owns deterministic text rendering.
- `src/` remains the current OpenPet command adapter and owns `ctx`, `ctx.storage`, `ctx.pet.say`, and command orchestration.
- `scripts/build-plugin.js` still produces the current command-plugin bundle from `core/`, `rendering/`, and `src/`.

Remaining Phase 2 work before Web/Email service implementation:

- introduce a shared report model that can feed pet text, dashboard previews, and Email rendering;
- split command cache/storage helpers if the service needs to reuse them;
- add HTML/Email view-model tests before promoting legacy templates into active runtime.

## 13.4 Phase 3 Development Record

Phase 3 is complete with a Fastify companion service skeleton. This service is active repository code and is packaged in the unified `.openpet-extension.zip`; it remains excluded from the command-only `.openpet-plugin.zip` compatibility artifact.

Implemented artifacts:

- `service/app.js`
- `service/index.js`
- `service/paths.js`
- `static/app.css`
- `tests/service-app.test.js`
- `npm run service:start`

Current service behavior:

- uses Fastify as the HTTP framework;
- binds through the standalone `service/index.js` entry;
- exposes `GET /health` with redacted service metadata and directory readiness flags, without returning local absolute paths;
- creates `OPENPET_DATA_DIR`, `OPENPET_CACHE_DIR`, and `OPENPET_LOG_DIR` when provided;
- serves a dashboard shell at `GET /`;
- serves active CSS at `GET /static/app.css`;
- writes startup/shutdown logs to `OPENPET_LOG_DIR/service.log` when started through `service/index.js`.

Current packaging boundary:

- current `npm run package:plugin` still builds only the command-plugin package under `openpet-plugin/`;
- Fastify service files are intentionally excluded from the current OpenPet command-plugin zip;
- `npm run package:extension` includes the service files through the unified extension manifest and is validated against OpenPet main.

Validation record:

- production code quality review tightened `/health` so service paths are not exposed in HTTP responses;
- GitHub Actions installs plugin dependencies with `npm ci` before running service-aware tests, build, lint, typecheck, and packaging;
- `npm test`;
- `npm run typecheck`;
- `npm run build`;
- `npm run lint`;
- `npm run package:plugin`;
- `git diff --check`.

## 13.5 Phase 4 Development Record

Phase 4 is complete with a conservative Fastify Web dashboard migration. The implementation preserves the recovered dashboard, configuration workbench, manual preview, and logs workflow shape without reintroducing Python or Jinja runtime dependencies.

Implemented artifacts:

- `service/configuration/defaults.js`
- `service/configuration/validation.js`
- `service/storage/configuration-store.js`
- `service/views/layout.js`
- `service/views/dashboard.js`
- `service/views/configuration.js`
- `service/views/manual-preview.js`
- `service/views/logs.js`
- expanded `tests/service-app.test.js`

Current active routes:

- `GET /` dashboard home/status with manual preview entry, configuration/log links, and active CSS;
- `GET /configuration` editable configuration workbench using service-owned JSON state;
- `POST /configuration/defaults` default location, schedule, language, report type, and send policy save;
- `POST /configuration/recipients` recipient create/update with validation;
- `POST /configuration/schedules` schedule create/update with recipient validation;
- `POST /configuration/smtp` SMTP metadata save with password redaction;
- `POST /configuration/branding` branding save with accent color validation;
- `POST /configuration/notifications` notification and retention save with non-negative integer validation;
- `POST /manual/preview` local preview confirmation without Email delivery;
- `GET /logs` recent service log view with a safe empty state.

Current storage boundary:

- Phase 4 stores `configuration.json` under `OPENPET_DATA_DIR`;
- SMTP passwords are not persisted as raw values in Phase 4; only `passwordSaved` metadata is stored;
- `service.log` remains under `OPENPET_LOG_DIR`;
- SQLite remains deferred until Email delivery, scheduler, retries, and delivery history need transactional behavior.

Validation and safety coverage:

- active HTML rendering escapes user-controlled values;
- configuration page exposes editable forms for defaults, recipients, schedules, SMTP, providers, branding, and notifications;
- invalid recipient email returns a safe configuration page with preserved form values;
- schedules reject unknown recipient ids;
- default and schedule send times reject impossible `HH:MM` values such as `24:00` and `99:99`;
- SMTP password values are not echoed in responses or persisted JSON;
- invalid branding accent colors are rejected;
- notification retention and cooldown fields reject empty or negative values;
- manual preview renders confirmation content without sending Email.

Current packaging boundary:

- current `npm run package:plugin` still builds only the command-plugin package under `openpet-plugin/`;
- Web dashboard service files are intentionally excluded from the current OpenPet command-plugin zip;
- `npm run package:extension` includes Web dashboard service files in the unified extension zip.

## 13.6 Phase 5 Development Record

Phase 5 is complete with the first active Email delivery boundary for the Fastify companion service. This phase adds deterministic Email rendering, fake SMTP transport support for tests, send-now orchestration, and bounded delivery history without changing the current command-only OpenPet package.

Implemented artifacts:

- `rendering/email-template-options.js`
- `rendering/email-renderer.js`
- `service/email/transports.js`
- `service/email/send-now.js`
- `service/storage/delivery-history-store.js`
- `service/views/email-preview.js`
- expanded `tests/email-renderer.test.js`
- expanded `tests/email-send-now.test.js`
- expanded `tests/service-app.test.js`

Current active Email behavior:

- preserves the five legacy Email template options: `1` 暖调风格, `2` 行动风格, `3` 玻璃渐变, `4` 极简风格, and `5` 仪表风格;
- renders Email subject, plain text fallback, HTML body, selected template id/label, and structured action summary;
- supports Chinese and English labels;
- preserves greeting visibility, footer text, accent color, and data source visibility;
- renders key periods, current conditions, temperature range, wind, UV, umbrella, sunscreen, clothing, and risk level;
- exposes `GET /email/preview` for local preview without sending Email;
- exposes `POST /email/send-now` for immediate Email send through an injected transport;
- stores bounded `delivery-history.json` records under `OPENPET_DATA_DIR`.

Current secret and transport boundary:

- raw SMTP passwords are not persisted in `configuration.json` or delivery history;
- `createServiceApp` accepts an injected Email transport for tests and future runtime wiring;
- the default service transport is an unavailable transport, so Phase 5 cannot accidentally send real Email without explicit wiring;
- send failures record redacted error messages and avoid storing HTML bodies.

Validation and safety coverage:

- all five Email templates render valid HTML;
- Email rendering escapes recipient, location, and footer values;
- fake transport send-now records `sent` history without storing HTML bodies or secret values;
- throwing transport records `failed` history with redacted error text;
- `GET /email/preview` does not call the transport;
- `POST /email/send-now` rejects unknown recipients with a safe 400 response.

Current packaging boundary:

- current `npm run package:plugin` still builds only the command-plugin package under `openpet-plugin/`;
- Email service files are intentionally excluded from the current OpenPet command-plugin zip;
- real SMTP lifecycle, scheduler queueing, retries, and unified service packaging remain deferred to later phases.

## 13.7 Phase 6 Development Record

Phase 6 is complete with a JSON-backed service-owned scheduler queue. This phase adds deterministic due-job enqueueing, queue deduplication, worker/job leases, bounded retry behavior, uncertain delivery safety, and dashboard-visible queue status without starting a long-running daemon loop or changing the command-only OpenPet package.

Implemented artifacts:

- `service/scheduler/time.js`
- `service/scheduler/state-store.js`
- `service/scheduler/queue.js`
- `service/views/scheduler.js`
- expanded `tests/scheduler-queue.test.js`
- expanded `tests/service-app.test.js`

Current scheduler behavior:

- stores scheduler state in `scheduler-state.json` under `OPENPET_DATA_DIR`;
- enqueues automatic jobs when a recipient's timezone-local minute matches a configured schedule;
- skips recipients with invalid timezone strings instead of failing the enqueue route;
- suppresses duplicate automatic jobs by recipient id, schedule id, report type, and local report date;
- does not backfill missed minutes in Phase 6;
- supports worker leases with active-worker blocking and expired takeover;
- supports job leases with recovery before delivery begins;
- applies bounded retry delays of 5, 15, 30, and 60 minutes before marking a job failed;
- marks expired `dispatching` jobs as `delivery_result_unknown` and prevents automatic re-claiming;
- exposes `GET /scheduler` and `POST /scheduler/enqueue-due`;
- dashboard now links to the scheduler status page.

Current safety and storage boundary:

- scheduler state does not store Email HTML bodies or SMTP secrets;
- scheduler failure diagnostics redact explicit secrets and password query values before persistence;
- Phase 6 uses explicit route-triggered due-job enqueueing instead of a background daemon;
- real worker processing and scheduler lifecycle integration remain deferred until the unified extension package phase can define service start/stop behavior.

Validation and safety coverage:

- automatic jobs enqueue once per local date and schedule minute;
- duplicate jobs are suppressed;
- invalid recipient timezones do not crash due-job enqueueing;
- missed minutes are not backfilled;
- worker leases and expired takeover are covered;
- expired running job leases can be recovered before delivery starts;
- retry delays are bounded and exhaustion marks jobs failed;
- uncertain delivery state avoids unsafe duplicate send;
- scheduler failure messages are redacted before they are stored;
- scheduler dashboard renders queue and worker status.

Current packaging boundary:

- current `npm run package:plugin` still builds only the command-plugin package under `openpet-plugin/`;
- scheduler service files are intentionally excluded from the current OpenPet command-plugin zip;
- unified service/dashboard/scheduler packaging remains deferred to Phase 7.

## 13.8 Phase 7 Development Record

Phase 7 is complete with a dual-package transition toward the unified OpenPet extension model. The repository still produces the command-plugin compatibility artifact for command-only installations, and also produces an OpenPet-main-validated unified extension artifact that includes active commands, service, dashboard assets, and package metadata.

Implemented artifacts:

- `extension/plugin.json`
- `commands/runner.js`
- `commands/refresh.js`
- `commands/announce.js`
- `commands/last.js`
- `commands/status.js`
- `commands/clear-cache.js`
- `commands/send-email-now.js`
- `commands/setup.js`
- `commands/weather-command.js`
- `scripts/package-extension.js`
- `scripts/check-extension-artifact.js`
- `tests/extension-package.test.js`
- `tests/extension-commands.test.js`

Current packaging behavior:

- `npm run package:plugin` is unchanged and still creates `release/weather-morning-report.openpet-plugin.zip` from `openpet-plugin/`;
- `npm run package:extension` creates `release/weather-morning-report.openpet-extension.zip` from a staged package root;
- the unified package root contains `plugin.json`, `config.schema.json`, `package.json`, `README.md`, `commands/`, `core/`, `rendering/`, `service/`, and `static/`;
- the unified package excludes `legacy-assets/`, `docs/`, `tests/`, `release/`, `node_modules/`, `.git/`, local data directories, and `.env` files;
- `npm run lint:extension` validates package-specific rules locally, and OpenPet main `validate:plugin` validates the unified zip against the host package rules.

Current unified manifest entries:

- shell commands: `refresh`, `announce`, `last`, `status`, `clear-cache`, `send-email-now`, and `setup`;
- service: `weather-service`, command `node service/index.js`, health `http://127.0.0.1:8787/health`;
- dashboard: `main`, URL `http://127.0.0.1:8787`;
- manifest metadata records network hosts, local data environment variables, SMTP as a self-managed external account, and the service-owned schedule boundary.

Current shell command contract:

- command entries are package-relative Node scripts under `commands/`;
- commands read optional JSON from stdin and emit one JSON object to stdout;
- weather shell commands reuse the active JS core parser, provider, recommendation engine, and text renderer;
- `refresh` and `announce` fetch/render reports and persist a command cache under `OPENPET_CACHE_DIR` or `OPENPET_DATA_DIR`;
- `last`, `status`, and `clear-cache` operate on the persisted command cache;
- invalid stdin JSON exits non-zero and redacts known secret values in stderr;
- stdout JSON recursively redacts secret-looking input keys such as password, token, and secret;
- Phase 7 `send-email-now` reports a service requirement unless `OPENPET_SERVICE_URL` is provided;
- `setup` reports setup metadata instead of running dependency installation at runtime.

Validation coverage:

- unified manifest shape and entry lists are covered;
- command stdin/env/JSON behavior is covered;
- command stdout redaction for secret-looking input fields is covered;
- unified zip inclusion and exclusion rules are covered;
- local extension artifact validation checks command paths, service path, dashboard/health URL origin consistency, required active files, and forbidden package paths;
- current `.openpet-plugin.zip` compatibility remains covered by the existing OpenPet validator tests.

Production review fixes:

- shell command entries now execute active weather command semantics instead of returning metadata-only placeholders;
- command stdout JSON recursively redacts secret-looking input fields before writing results.

Remaining Phase 8 alignment:

- keep the unified package passing the current OpenPet main extension-entry validator;
- wire real OpenPet service lifecycle start/stop semantics;
- expose dashboard/service health through OpenPet surfaces;
- keep repository-local artifact validation as an additional package-specific guard.

## 13.9 Phase 8 Development Record

Phase 8 aligns the unified extension package with the current sibling OpenPet validator while preserving the local package-specific validator from Phase 7.

Implemented artifacts:

- `tests/openpet-extension-validate.test.js`
- `docs/superpowers/specs/2026-06-17-phase-8-openpet-alignment-design.md`
- `docs/superpowers/plans/2026-06-17-phase-8-openpet-alignment.md`
- updated `extension/plugin.json`

OpenPet alignment behavior:

- `release/weather-morning-report.openpet-extension.zip` is now validated by `/Users/mango/project/codex/OpenPet` using `npm run validate:plugin`;
- `extension/plugin.json` keeps extension `entries.commands`, `entries.services`, and `entries.dashboards`;
- `assets` now use OpenPet-supported literal package paths: `static`, `service/views`, and `README.md`;
- repository-local `npm run lint:extension` remains in place to enforce this project's stricter package exclusions and URL consistency.

Validation coverage:

- the unified extension zip passes the current OpenPet package validator;
- current command-plugin `.openpet-plugin.zip` validator coverage remains unchanged;
- local unified artifact validation still checks package-specific exclusions and entry path consistency.
- CI treats OpenPet `main` extension-entry support as required; the unified extension zip must pass the sibling OpenPet `validate:plugin` command, and real validation failures fail the test.

Runtime evidence still required after repository alignment:

- dashboard open behavior should be smoke-tested in the OpenPet Control Center;
- service start/stop and `/health` state should be smoke-tested through OpenPet service lifecycle controls;
- command logs and result JSON display should be verified through OpenPet command execution surfaces.

## 13.10 Phase 9 Planned Runtime Smoke

Phase 9 should convert the runtime evidence gaps into an automated smoke pass against the sibling OpenPet runtime service.

Planned evidence:

- dashboard `main` opens through OpenPet's dashboard opener and records a `dashboard:main` plugin log;
- service `weather-service` starts through OpenPet lifecycle controls, returns healthy from `/health`, stops cleanly, and records `service:weather-service` logs;
- command `status` runs through OpenPet command execution, returns JSON-compatible status data, and records command completion logs.

Implementation note:

- current OpenPet runs commands through a plugin `main` handler, while the unified extension target also declares shell command entries;
- Phase 9 should package the existing bundled command-plugin `main` as a compatibility entry inside the unified extension without removing the target `entries.commands` declarations.

## 13.11 Phase 9 Development Record

Phase 9 adds automated runtime smoke evidence for the unified extension against the sibling OpenPet runtime service.

Implemented artifacts:

- `scripts/openpet-runtime-smoke.js`
- `tests/openpet-runtime-smoke.test.js`
- `docs/superpowers/specs/2026-06-17-phase-9-openpet-runtime-smoke-design.md`
- `docs/superpowers/plans/2026-06-17-phase-9-openpet-runtime-smoke.md`
- updated `extension/plugin.json`

Runtime compatibility behavior:

- unified package now declares `main: compat/openpet-main.js` for current OpenPet command execution;
- `compat/openpet-main.js` is copied from the existing bundled `openpet-plugin/index.js` during `npm run package:extension`;
- target `entries.commands`, `entries.services`, and `entries.dashboards` remain in place;
- top-level `permissions` and `network.allowlist` are declared so current OpenPet SDK permission checks can run the compatibility command handlers.

Smoke evidence:

- `npm run smoke:openpet-runtime -- --json` packages the extension, extracts the zip into a temporary OpenPet-style plugin directory, installs production dependencies there, and loads it through `/Users/mango/project/codex/OpenPet/src/main/services/plugin-service.js`;
- dashboard `main` opens through OpenPet's dashboard opener and records `dashboard:main`;
- service `weather-service` starts through OpenPet lifecycle controls, returns healthy from `/health`, and records `service:weather-service` logs;
- command `status` runs through OpenPet command execution, returns JSON-compatible status data, and records `Command completed`.
- GitHub Actions checks out `dengyie/OpenPet@codex/plugin-service-health-checks` until those runtime service APIs land on OpenPet `main`.

Remaining runtime evidence:

- full Electron Control Center visual smoke remains outside this repository-owned phase;
- direct shell spawning for `entries.commands` remains an OpenPet host capability target, while the compatibility `main` keeps current runtime command execution working.

## 13.12 Phase 10 Planned Setup And Cleanup Lifecycle

Phase 10 should complete the repository-owned setup and cleanup lifecycle declarations for the unified extension package.

Planned behavior:

- setup should be declared in `entries.setup` for OpenPet's setup lifecycle UI and status tracking;
- setup should remain metadata-only and must not silently run dependency installation during package install;
- cleanup should be explicit, dry-run by default, and limited to known service-owned files under `OPENPET_DATA_DIR`, `OPENPET_CACHE_DIR`, and `OPENPET_LOG_DIR`;
- cleanup should not claim to remove SMTP provider data, external accounts, cloud data, arbitrary directories, or third-party-managed secrets.

## 13.13 Phase 10 Development Record

Phase 10 adds explicit setup lifecycle declaration and conservative cleanup behavior for service-owned local files.

Implemented artifacts:

- `commands/cleanup.js`
- `docs/superpowers/specs/2026-06-17-phase-10-setup-cleanup-lifecycle-design.md`
- `docs/superpowers/plans/2026-06-17-phase-10-setup-cleanup-lifecycle.md`
- updated `extension/plugin.json`
- updated `scripts/check-extension-artifact.js`

Lifecycle behavior:

- `entries.setup` now declares `setup` with `node commands/setup.js` for OpenPet's current setup lifecycle surface;
- `entries.commands` keeps `setup` for compatibility and adds `cleanup` as an explicit user-run command;
- `setup` remains metadata-only and does not install dependencies or mutate package state;
- `cleanup` defaults to dry-run and reports planned service-owned files;
- `cleanup` deletes files only when stdin includes `{ "confirm": true }`;
- confirmed cleanup is limited to `configuration.json`, `delivery-history.json`, `scheduler-state.json`, `weather-command-cache.json`, and `service.log`;
- command cache cleanup follows command runtime storage behavior: `OPENPET_CACHE_DIR/weather-command-cache.json` when configured, otherwise `OPENPET_DATA_DIR/weather-command-cache.json`.
- the compatibility `main` command bundle also exposes `cleanup` so current OpenPet runtimes that execute through `compat/openpet-main.js` do not surface a missing command; that compatibility handler is dry-run by default and only clears OpenPet command-plugin storage when confirmed.

Validation coverage:

- command tests cover cleanup dry-run and confirmed deletion behavior;
- cleanup tests assert unrelated files in data/cache/log directories are preserved;
- cleanup tests assert the `OPENPET_DATA_DIR` command-cache fallback is removed when no cache directory is configured;
- compatibility command tests assert the bundled OpenPet command surface includes cleanup;
- package tests cover manifest setup/cleanup declarations and packaged `commands/cleanup.js`;
- local extension artifact validation now checks setup lifecycle entry paths are safe package-relative node commands.

Remaining lifecycle work:

- OpenPet does not yet expose a dedicated `entries.cleanup` lifecycle runner, so cleanup remains a normal command entry;
- uninstall automation and third-party account cleanup remain outside this repository-owned phase;
- dependency installation remains the host/development setup responsibility, not an install-time side effect.

## 13.14 Phase 11 Planned Real SMTP Transport

Phase 11 should replace the service's unavailable default Email transport with a real SMTP adapter while preserving fake transport injection for deterministic tests.

Planned behavior:

- `createServiceApp` should default to an SMTP transport for `/email/send-now`;
- fake transport injection should remain supported for service and unit tests;
- SMTP configuration should be read from service-owned configuration, while raw password material remains runtime-only through `SMTP_PASSWORD`;
- `plain`, `starttls`, and `ssl` security modes should map explicitly to SMTP client options;
- timeout should be configurable with `SMTP_TIMEOUT_MS`;
- missing SMTP host, sender identity, or required runtime password should fail with redacted error handling.

## 13.15 Phase 11 Development Record

Phase 11 activates real SMTP delivery for the service Email send-now path without changing the persisted secret policy.

Implemented artifacts:

- `docs/superpowers/specs/2026-06-17-phase-11-real-smtp-transport-design.md`
- `docs/superpowers/plans/2026-06-17-phase-11-real-smtp-transport.md`
- updated `service/email/transports.js`
- updated `service/email/send-now.js`
- updated `service/app.js`
- added `nodemailer` dependency

SMTP runtime behavior:

- `createServiceApp` now defaults to `createSmtpEmailTransport({ env })` when no test transport is injected;
- `sendEmailNow` passes `configuration.smtp` to the transport while continuing to own recipient lookup, rendering, history, and redacted failure records;
- SMTP password material is read from `SMTP_PASSWORD`, not from `configuration.json`;
- `SMTP_TIMEOUT_MS` controls connection, greeting, and socket timeouts, with a 10000 ms default;
- `starttls` maps to `secure: false` and `requireTLS: true`;
- `ssl` maps to `secure: true`;
- `plain` maps to `secure: false` and `ignoreTLS: true`;
- missing SMTP host, invalid port, missing configured sender identity, or required runtime password fails before creating the SMTP client;
- runtime SMTP password values are passed through exactly as provided by `SMTP_PASSWORD`.

Validation coverage:

- SMTP transport tests cover security mode mapping, auth mapping, timeout mapping, and missing configuration;
- SMTP transport tests cover invalid persisted port values, configured sender identity enforcement, and exact runtime password preservation;
- send-now tests assert SMTP configuration is passed to transports without storing raw password material;
- service route tests assert the default send-now path uses the SMTP transport factory when no fake transport is injected;
- existing fake transport route tests remain in place.

Remaining SMTP work:

- encrypted service-managed SMTP password storage remains out of scope;
- dashboard test-connection/test-email UX remains a future phase;
- scheduler worker daemonization remains separate from this transport activation.

## 13.16 Phase 12 Planned SMTP Operational Tests

Phase 12 should add operator-facing SMTP test connection and test Email actions now that the real SMTP transport exists.

Planned behavior:

- `POST /configuration/smtp/test-connection` should verify the current SMTP configuration through the active transport;
- `POST /email/test` should send a short operational Email to a selected recipient;
- test Email should not create delivery history records because it is not a weather report delivery;
- configuration page should expose both actions near the SMTP settings;
- failures should redact `SMTP_PASSWORD` and other known secret values from JSON responses.

## 13.17 Phase 12 Development Record

Phase 12 adds SMTP operational tests for the dashboard/service path.

Implemented artifacts:

- `docs/superpowers/specs/2026-06-17-phase-12-smtp-operational-tests-design.md`
- `docs/superpowers/plans/2026-06-17-phase-12-smtp-operational-tests.md`
- updated `service/email/transports.js`
- updated `service/app.js`
- updated `service/views/configuration.js`

Operational behavior:

- SMTP transport now exposes `verify(message)` using the same option-building path as `send(message)`;
- `POST /configuration/smtp/test-connection` calls the active transport `verify()` and returns `{ ok: true, status: "connected" }` on success;
- test connection failures return redacted 502 JSON;
- `POST /email/test` sends a short SMTP operational test message to a selected recipient;
- test Email includes SMTP configuration in the transport message but does not append delivery history records;
- both operational routes require a configured sender identity before calling injected transports, avoiding fake success when SMTP sender config is missing;
- the configuration page renders a test connection form and recipient-select test Email form inside the SMTP section.

Validation coverage:

- SMTP transport tests cover `verify()` option mapping and client verification;
- service route tests cover test connection success without sending Email;
- service route tests cover redacted test connection failures;
- service route tests cover missing sender rejection before `verify()` or `send()` side effects;
- service route tests cover test Email success and no delivery history write;
- configuration page tests cover operational action controls.

Production review:

- Ran `/Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py` and reviewed Phase 12 against `origin/codex/phase-11-real-smtp-transport`.
- Confirmed and fixed one issue: route-level SMTP operational checks could pass under injected transports without a configured sender.
- Re-ran focused RED/GREEN tests and the full phase verification gate.

Remaining SMTP work:

- encrypted service-managed SMTP password storage remains out of scope;
- richer dashboard status rendering for operation results remains future UI work;
- scheduler worker daemonization remains separate from SMTP operational checks.

## 13.18 Phase 13 Planned SMTP Operational UX Feedback

Phase 13 should convert the raw SMTP operation responses into configuration-page feedback workflows while preserving API-friendly behavior.

Planned behavior:

- configuration page should support success notices distinct from validation errors;
- SMTP operational forms should opt into page-mode feedback instead of raw JSON responses;
- successful SMTP connection tests should redirect back to `/configuration` with a clear success notice;
- successful test Emails should redirect back to `/configuration` with a clear recipient-aware success notice;
- page-mode failures should render the configuration page with redacted operational feedback and preserve the SMTP testing controls.

## 13.19 Phase 13 Development Record

Phase 13 turns SMTP operational actions into first-class configuration workbench flows.

Implemented artifacts:

- `docs/superpowers/specs/2026-06-17-phase-13-smtp-operational-ux-feedback-design.md`
- `docs/superpowers/plans/2026-06-17-phase-13-smtp-operational-ux-feedback.md`
- updated `service/app.js`
- updated `service/views/configuration.js`
- updated `static/app.css`

Operational behavior:

- configuration page now supports success notices in addition to warning/error feedback;
- SMTP operational forms submit `page_mode=configuration` so browser form posts get page-native feedback;
- page-mode `POST /configuration/smtp/test-connection` redirects back to `/configuration` with a success notice after a successful verify;
- page-mode `POST /email/test` redirects back to `/configuration` with a recipient-aware success notice after a successful send;
- page-mode operational failures render the configuration page with redacted warnings instead of raw JSON;
- non-page callers keep the existing JSON contracts for SMTP operational routes.

Validation coverage:

- configuration page tests cover success notice rendering alongside SMTP controls;
- service route tests cover page-mode SMTP connection success redirects and failure re-renders;
- service route tests cover page-mode test Email success redirects and failure re-renders;
- existing JSON-mode route tests remain in place to guard backward-compatible operational responses.

Remaining SMTP work:

- encrypted service-managed SMTP password storage remains out of scope;
- scheduler worker daemonization remains separate from SMTP operational UX.

## 13.20 Phase 14 Planned SMTP Operational History

Phase 14 should persist SMTP operational check results and show recent checks in the configuration page.

Planned behavior:

- SMTP test connection should append a bounded operational history record on both success and failure;
- test Email should append a bounded operational history record on both success and failure;
- configuration page should render recent SMTP operational history in the SMTP section;
- operational history should remain separate from delivery history and redact runtime SMTP secrets.

### Phase 15: SMTP Operational History Filter/Export

- Add conservative filtering for SMTP operational history in the configuration page.
- Add filtered JSON and CSV export endpoints for SMTP operational history.
- Keep exported operational history redacted and service-owned.

Done when:

- configuration page can filter SMTP operational history by action, status, and recipient;
- JSON export returns the currently filtered SMTP operational history;
- CSV export returns a newline-terminated attachment with safe columns;
- operational history filtering/export stays separate from delivery history.

### Phase 16: Managed SMTP Secret Storage

- Add encrypted service-managed SMTP password storage under `OPENPET_DATA_DIR`.
- Keep `configuration.json` free of raw SMTP password material.
- Preserve `SMTP_PASSWORD` as a backward-compatible fallback when no managed secret exists.

Done when:

- SMTP password can be saved into a service-owned encrypted secret store;
- SMTP transport prefers managed secrets and falls back to `SMTP_PASSWORD`;
- SMTP password can be explicitly cleared from service storage;
- configuration, logs, delivery history, and SMTP operational history stay secret-free.

### Phase 17: Secret Key Backup And Health UX

- Surface local `.secret-key` and managed SMTP password health on the configuration page.
- Add explicit backup confirmation and revocation controls for the local key.
- Keep raw key, raw password, ciphertext, and invalid key payloads non-exportable and hidden from HTML.

Done when:

- configuration page renders secret key and managed SMTP password health;
- users can mark the local key as backed up and revoke that confirmation;
- degraded key or managed-secret states render as warnings without crashing the dashboard;
- health inspection and configuration routes are covered by tests.

### Phase 18: Secret Key Rotation And Recovery

- Add a safe local `.secret-key` rotation workflow that re-encrypts the managed SMTP password under a new key.
- Reset backup confirmation after successful rotation so the new key must be acknowledged as backed up.
- Keep key rotation rollback-safe, secret-free in HTML/logs, and out of export/download scope.

Done when:

- configuration page exposes a safe key-rotation action for healthy managed secret state;
- successful rotation preserves the managed SMTP password and resets backup confirmation;
- failed rotation leaves the prior key, secret payload, and configuration metadata usable;
- rotation behavior is covered by tests and production review.

## 13.21 Phase 14 Development Record

Phase 14 adds persistent SMTP operational history for connection tests and test Emails.

Implemented artifacts:

- `docs/superpowers/specs/2026-06-17-phase-14-smtp-operational-history-design.md`
- `docs/superpowers/plans/2026-06-17-phase-14-smtp-operational-history.md`
- added `service/storage/smtp-operation-history-store.js`
- updated `service/app.js`
- updated `service/views/configuration.js`

Operational behavior:

- SMTP test connection appends bounded operational history records on both success and failure;
- test Email appends bounded operational history records on both success and failure;
- operational history is stored separately from `delivery-history.json`;
- configuration page renders recent SMTP operational history beside the SMTP controls;
- persisted operational history keeps runtime SMTP secrets redacted.

Validation coverage:

- storage tests cover bounded SMTP operational history persistence;
- service route tests cover success/failure history records for SMTP connection tests;
- service route tests cover success/failure history records for test Emails;
- configuration page tests cover recent SMTP operational history rendering;
- existing delivery-history tests remain in place to guard separation from weather report delivery history.

Remaining SMTP work:

- encrypted service-managed SMTP password storage remains out of scope;
- scheduler worker daemonization remains separate from SMTP operational history.

## 13.22 Phase 15 Development Record

Phase 15 adds conservative filtering and export for SMTP operational history in the configuration workbench.

Implemented artifacts:

- `docs/superpowers/specs/2026-06-17-phase-15-smtp-history-filter-export-design.md`
- `docs/superpowers/plans/2026-06-17-phase-15-smtp-history-filter-export.md`
- updated `service/storage/smtp-operation-history-store.js`
- updated `service/app.js`
- updated `service/views/configuration.js`
- expanded `tests/email-send-now.test.js`
- expanded `tests/service-app.test.js`

Operational behavior:

- configuration page can filter SMTP operational history by action, status, and recipient;
- JSON export returns the currently filtered SMTP operational history;
- CSV export returns a newline-terminated attachment with safe columns;
- operational history filtering and export remain separate from delivery history.

Validation coverage:

- store tests cover SMTP operational history filtering and CSV serialization;
- service route tests cover filtered configuration rendering;
- service route tests cover filtered JSON and CSV export behavior;
- existing delivery-history tests remain in place to guard separation from weather report delivery history.

Remaining SMTP work:

- encrypted service-managed SMTP password storage remains out of scope;
- scheduler worker daemonization remains separate from SMTP operational history.

## 13.23 Phase 16 Development Record

Phase 16 adds service-managed encrypted SMTP password storage with compatibility-preserving runtime fallback.

Implemented artifacts:

- `docs/superpowers/specs/2026-06-17-phase-16-managed-smtp-secret-storage-design.md`
- `docs/superpowers/plans/2026-06-17-phase-16-managed-smtp-secret-storage.md`
- added `service/storage/secret-store.js`
- updated `service/app.js`
- updated `service/email/send-now.js`
- updated `service/email/transports.js`
- updated `service/views/configuration.js`
- expanded `tests/email-send-now.test.js`
- expanded `tests/service-app.test.js`

Operational behavior:

- SMTP metadata remains in `configuration.json`, while raw SMTP password material moves into encrypted service-owned storage under `OPENPET_DATA_DIR`;
- the service generates a local master key in `.secret-key` and stores encrypted SMTP secret payloads in `secrets.json`;
- SMTP password resolution now prefers managed decrypted password and falls back to `SMTP_PASSWORD` only when no managed secret exists;
- `POST /configuration/smtp` stores new passwords in managed secret storage and keeps existing secrets unchanged when the password field is left blank;
- `POST /configuration/smtp/clear-password` removes the managed password and resets `passwordSaved`;
- configuration UI shows saved-password state and a clear-password action without rendering decrypted secrets;
- resolved SMTP passwords are kept out of `configuration.json`, page HTML, delivery history, SMTP operational history, and JSON-stringified injected transport payloads.

Validation coverage:

- secret-store tests cover local key generation, encrypted round-trip, clear flow, and corrupt payload failure handling;
- SMTP transport tests cover managed-password precedence over `SMTP_PASSWORD`;
- service route tests cover managed-secret persistence, send-now usage, and clear-password behavior;
- existing redaction tests remain in place to guard configuration, HTTP error, delivery history, and SMTP operational history secrecy.

Remaining SMTP work:

- external KMS or OS keychain integration remains out of scope;
- user-facing secret rotation and backup UX remain separate from local key generation;
- scheduler worker daemonization remains separate from SMTP secret storage.

## 13.24 Phase 17 Development Record

Phase 17 adds user-facing secret key backup acknowledgement and managed SMTP secret health visibility.

Implemented artifacts:

- `docs/superpowers/specs/2026-06-17-phase-17-secret-key-backup-and-health-ux-design.md`
- `docs/superpowers/plans/2026-06-17-phase-17-secret-key-backup-and-health-ux.md`
- updated `service/storage/secret-store.js`
- updated `service/app.js`
- updated `service/views/configuration.js`
- expanded `tests/email-send-now.test.js`
- expanded `tests/service-app.test.js`

Operational behavior:

- secret storage now exposes `inspectSecretHealth()` for normalized read-only health inspection;
- health inspection reports local master-key presence/validity, managed SMTP password presence/health, last update time, backup confirmation, and one safe warning string;
- `GET /configuration` renders a new `密钥与备份状态` section with backup status, degraded-state warnings, and confirmation controls;
- `POST /configuration/secrets/confirm-backup` records `notifications.secretKeyBackupConfirmed = true`;
- `POST /configuration/secrets/revoke-backup-confirmation` records `notifications.secretKeyBackupConfirmed = false`;
- unhealthy local keys or corrupt managed SMTP payloads show warnings without exposing raw secret material.

Security boundary:

- Phase 17 does not export, import, download, rotate, or reveal the local `.secret-key`;
- page HTML does not include raw SMTP passwords, decrypted passwords, ciphertext, or invalid key file contents;
- managed password decryption remains local to service runtime flows that need SMTP delivery.

Validation coverage:

- secret-store tests cover no-secret, healthy unconfirmed, healthy confirmed, invalid local key, and corrupt managed SMTP payload states;
- service route tests cover backup warning rendering, confirmation route toggles, healthy confirmed rendering, and degraded health rendering;
- focused Phase 17 verification passed with `node --test --test-concurrency=1 tests/email-send-now.test.js tests/service-app.test.js`.

Remaining SMTP work:

- raw key export/import and downloadable backup files remain intentionally out of scope;
- external KMS or OS keychain integration remains separate from local key backup UX;
- scheduler worker daemonization remains separate from secret health UX.

## 13.25 Phase 18 Development Record

Phase 18 adds safe local secret-key rotation with managed SMTP password re-encryption and backup-confirmation reset.

Implemented artifacts:

- `docs/superpowers/specs/2026-06-17-phase-18-secret-key-rotation-and-recovery-design.md`
- `docs/superpowers/plans/2026-06-17-phase-18-secret-key-rotation-and-recovery.md`
- updated `service/storage/secret-store.js`
- updated `service/app.js`
- updated `service/views/configuration.js`
- expanded `tests/email-send-now.test.js`
- expanded `tests/service-app.test.js`

Operational behavior:

- `POST /configuration/secrets/rotate-key` rotates the local `.secret-key` only when the managed SMTP password is healthy and decryptable;
- the managed SMTP password is re-encrypted under the new local key;
- successful rotation resets `notifications.secretKeyBackupConfirmed = false`;
- the configuration page renders a rotation action when a managed SMTP password exists;
- failed rotation keeps the prior secret payload usable and shows operator-safe feedback without leaking secret material;
- rotation recovery uses a local rotation-state file to restore pending writes if a previous attempt was interrupted.

Security boundary:

- Phase 18 does not add key export, download, import, or cross-machine recovery flows;
- page HTML, notices, and tests keep raw keys, decrypted passwords, ciphertext, and invalid key contents hidden;
- rollback artifacts stay in `OPENPET_DATA_DIR` and are cleaned up after recovery.

Validation coverage:

- secret-store tests cover successful rotation, missing secret rejection, invalid key rejection, rollback on write failure, rollback on post-rotation callback failure, and interrupted-rotation recovery;
- service route tests cover configuration rendering, successful rotation, undecryptable-secret failure, and configuration-persistence rollback;
- focused Phase 18 verification passed with `node --test --test-concurrency=1 tests/email-send-now.test.js tests/service-app.test.js`.

Production review summary:

- review skill: `production-code-quality-review`
- review scope: whole-repo context collection plus Phase 18 diff verification
- blocking issue found and fixed: rotation originally allowed the local key/secrets write to succeed before configuration backup-confirmation persistence, which could leave `secretKeyBackupConfirmed` stale after a configuration write failure; the implementation now rolls back the secret rotation when the post-rotation configuration callback fails and recovers pending writes from a local rotation-state file;
- optimization items reviewed:
  - keep operator-facing rotation failures secret-free and bounded to the configuration workflow;
  - keep interrupted-rotation recovery local to `OPENPET_DATA_DIR` without adding export/import scope;
  - defer raw key portability and external KMS/keychain work because they exceed the approved Phase 18 boundary;
- quality score: `9/10` (assumption recorded here because the review skill defines pass/fail guidance but does not define a built-in numeric rubric);
- release recommendation: `通过`

Todo status:

- Phase 18 tasks from the migration document and implementation plan are complete;
- no separate repo-level `todo` artifact was found beyond the migration-phase checklist, so this record treats the documented phase list as the active todo source;
- no new in-scope follow-up items were introduced by the Phase 18 review.

Next-stage dependency and risk:

- the migration document currently defines phases through Phase 18 only;
- if work continues beyond this point, the next stage needs a new approved spec before implementation so scope does not drift beyond the documented first-pass project goal.

Remaining SMTP work:

- external KMS or OS keychain integration remains out of scope;
- raw key export/import and downloadable backup recovery remain intentionally out of scope;
- scheduler worker daemonization remains separate from secret lifecycle UX.

## 14. Deliberate Non-Goals

First version should not:

- implement OpenPet Control Center iframe embedding;
- require strong sandboxing;
- require all secrets to be stored by OpenPet;
- revive Docker/systemd as primary product paths;
- reintroduce Python service as the default unless there is a clear implementation reason;
- silently run setup during install;
- claim full cleanup of third-party-managed data.

## 15. Implementation Defaults

- The first service implementation should use Fastify for route structure and test-friendly local HTTP injection.
- Exact template mechanism can be finalized during implementation; default recommendation is JS renderer functions with explicit escaping.
- SMTP settings should live in service-managed storage under `OPENPET_DATA_DIR`; `.env` may be supported for developer overrides.
- Production packages should aim to be self-contained, but `setup` remains supported.
- Current `openpet-plugin/` should remain valid as the legacy compatibility path while `.openpet-extension.zip` is the preferred service/dashboard-capable artifact.
- Login/forgot-password pages are optional future UX; current dashboard auth is local-token based.
