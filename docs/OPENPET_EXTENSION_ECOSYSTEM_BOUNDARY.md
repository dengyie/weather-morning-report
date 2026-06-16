# OpenPet Extension Ecosystem Boundary Design

> Status: design proposal agreed in product discussion.
> Scope: OpenPet third-party extension model and capability boundary.
> Non-scope: concrete OpenPet implementation patch, marketplace policy, cryptographic trust chain.

## 1. Decision Summary

OpenPet should position its third-party ecosystem as a **developer-first local extension platform**.

The platform should prioritize:

- broad local automation and integration capability;
- fast third-party experimentation;
- transparent user-visible manifests;
- OpenPet-managed lifecycle, logs, health, and uninstall flow;
- simple packaging and clear failure reporting.

The platform should not position ordinary third-party extensions as a strongly sandboxed or centrally risk-reviewed environment.

This means OpenPet should provide **basic structural safety and transparency**, not heavy approval gates, exhaustive permission modeling, or main-process proxying for every high-risk operation.

## 2. Core Principles

### 2.1 Developer First

Extensions should be able to implement practical local capabilities such as:

- Web dashboards;
- Email and SMTP delivery;
- voice conversation;
- long-running local services;
- writing assistants;
- pet model generation;
- local model or binary workflows;
- scheduled jobs;
- third-party API integrations.

OpenPet should not require every new plugin category to become a first-class hardcoded platform feature.

### 2.2 One Unified Extension Model

OpenPet should treat every third-party package as one thing: an extension.

Do not split the ecosystem into separate conceptual models such as plugin, companion, hybrid, app, service, worker, or widget. Those words can describe entries, but they should not create separate package models.

The package root remains:

```text
plugin.json
```

`plugin.json` is the unified manifest for all extension shapes.

### 2.3 Manifest As Declaration, Not Sandbox

The manifest is a user-visible declaration and operational contract.

OpenPet should hard-check only structural safety:

- required identity fields;
- valid JSON shape;
- entry paths stay inside the installed package;
- package extraction cannot escape the install directory;
- symlinks and path traversal are rejected;
- platform-specific entry definitions are syntactically valid;
- referenced config/assets paths are package-relative.

OpenPet should not attempt to hard-enforce all declared runtime capabilities. A local process can use its own runtime, files, network stack, secrets, and databases. The product language must be honest about that.

### 2.4 Lifecycle Management Over Risk Policing

OpenPet should manage extension lifecycle:

- install;
- enable/disable;
- setup step status;
- start/stop service entries;
- run command entries;
- collect stdout/stderr;
- health checks;
- dashboard opening;
- uninstall;
- optional cleanup command.

OpenPet should not become a general security broker for every local operation. It should expose what an extension declares and what OpenPet observes.

## 3. Unified `plugin.json` Shape

The first clean version should use a small top-level schema:

```json
{
  "id": "weather-morning-report",
  "name": "Weather Morning Report",
  "version": "1.0.0",
  "description": "Weather reports, Web dashboard, and Email delivery for OpenPet.",
  "entries": {
    "commands": [],
    "services": [],
    "dashboards": []
  },
  "manifest": {},
  "config": "config.schema.json",
  "assets": []
}
```

### 3.1 Identity Fields

| Field | Meaning |
| --- | --- |
| `id` | Stable extension id. |
| `name` | User-facing name. |
| `version` | Extension version. |
| `description` | Short user-facing purpose. |

### 3.2 `entries`

`entries` describes what OpenPet can start, run, or open.

First-version entries:

- `commands`: user-triggered shell commands;
- `services`: long-running shell services managed by OpenPet;
- `dashboards`: URLs or dashboard entry points OpenPet can open.

No special JS runner is required. JavaScript remains supported as ordinary shell execution, for example `node ./commands/announce.js`.

### 3.3 `manifest`

`manifest` is a free but structured declaration area for facts OpenPet should show to the user.

It may include:

- declared network hosts;
- data locations;
- external accounts;
- self-managed secrets;
- setup notes;
- cleanup notes;
- supported platforms;
- service behavior;
- schedule descriptions;
- compute expectations;
- device usage.

OpenPet should display this information but should not treat it as a complete enforcement boundary.

### 3.4 `config`

`config` points to an optional package-relative configuration schema.

This config can power OpenPet UI forms, but extensions may also maintain their own configuration files, databases, dashboards, or external accounts.

### 3.5 `assets`

`assets` declares meaningful package assets such as:

- templates;
- static files;
- dashboard frontend files;
- Email templates;
- model assets;
- documentation;
- examples.

OpenPet should not restrict extension packages to small JS-only bundles.

## 4. Entry Model

### 4.1 Commands

Commands are shell entries triggered by the user or by OpenPet UI.

Example:

```json
{
  "id": "send-email-now",
  "title": "Send Email Now",
  "command": "npm run email:send-now",
  "cwd": "."
}
```

OpenPet should:

- run the command in the installed extension directory;
- inject standard environment variables;
- pass command context as stdin JSON;
- collect stdout/stderr;
- read result JSON from `OPENPET_RESULT_PATH` when provided;
- optionally parse the final stdout JSON line as a fallback;
- show success/failure and recent logs.

OpenPet should not:

- parse or rewrite shell commands;
- require the command to be JavaScript;
- enforce business permissions;
- run commands at install time.

### 4.2 Services

Services are long-running shell entries managed by OpenPet.

Example:

```json
{
  "id": "companion",
  "name": "Weather Companion Service",
  "command": "npm run service:start",
  "cwd": ".",
  "platforms": {
    "darwin": { "command": "npm run service:start" },
    "win32": { "command": "npm run service:start:win" },
    "linux": { "command": "npm run service:start" }
  },
  "health": {
    "type": "http",
    "url": "http://127.0.0.1:8787/health"
  }
}
```

OpenPet should:

- select platform-specific command overrides;
- start and stop the process;
- capture stdout/stderr;
- show running/stopped/failed state;
- run health checks;
- stop services on disable/uninstall;
- avoid running service code during install.

OpenPet should not:

- require a specific language or runtime;
- require a self-contained package;
- attempt full process sandboxing;
- inspect shell internals.

### 4.3 Dashboards

Dashboards are user-facing URLs or local service pages.

First version behavior:

- OpenPet shows an “Open Dashboard” action.
- OpenPet opens the URL externally or in a separate app window.
- OpenPet does not host, iframe, theme, or inspect the dashboard.

Example:

```json
{
  "id": "main",
  "title": "Weather Dashboard",
  "url": "http://127.0.0.1:8787"
}
```

Later versions may add optional Control Center embedding, but the first version should stay simple.

## 5. Context Passing

OpenPet should use language-neutral context passing.

### 5.1 Environment Variables

Common variables:

| Variable | Purpose |
| --- | --- |
| `OPENPET_EXTENSION_ID` | Current extension id. |
| `OPENPET_EXTENSION_DIR` | Installed package directory. |
| `OPENPET_DATA_DIR` | Recommended persistent data directory. |
| `OPENPET_CACHE_DIR` | Recommended cache directory. |
| `OPENPET_LOG_DIR` | Recommended log directory. |
| `OPENPET_CONFIG_PATH` | Optional generated config JSON path. |
| `OPENPET_RESULT_PATH` | Command result JSON output path. |
| `OPENPET_BRIDGE_URL` | Optional local bridge endpoint. |
| `OPENPET_BRIDGE_TOKEN` | Optional bridge token. |

### 5.2 Command Stdin

Commands receive JSON on stdin:

```json
{
  "commandId": "announce",
  "payload": {},
  "config": {},
  "paths": {
    "extensionDir": "...",
    "dataDir": "...",
    "cacheDir": "...",
    "logDir": "..."
  }
}
```

### 5.3 Command Result

Preferred result:

- write JSON to `OPENPET_RESULT_PATH`.

Fallback result:

- final stdout line may be JSON.

OpenPet may interpret common keys:

```json
{
  "ok": true,
  "message": "Report sent.",
  "petSay": "今天有雨，邮件已发送。",
  "dashboardUrl": "http://127.0.0.1:8787/reports/latest"
}
```

## 6. Optional Bridge

OpenPet should provide a minimal optional HTTP bridge for deeper integration.

Injected values:

- `OPENPET_BRIDGE_URL`;
- `OPENPET_BRIDGE_TOKEN`.

First-version endpoint set:

- `POST /pet/say`;
- `POST /pet/action`;
- `POST /notification`;
- `POST /status`;
- `GET /config`.

The bridge is not a full SDK and should not grow into a heavy permission system in the first version.

## 7. Setup And Dependencies

OpenPet should not run code during install.

Extensions may declare explicit setup commands:

```json
{
  "id": "setup",
  "title": "Install Dependencies",
  "command": "npm install",
  "cwd": "."
}
```

Setup behavior:

- install only extracts and inspects;
- extension remains disabled by default;
- setup runs only when the user explicitly runs it or when enable/start flow asks for confirmation;
- OpenPet records setup status and logs;
- setup may be rerun.

Packages may be self-contained or non-self-contained.

OpenPet should recommend self-contained production packages, but should not require them.

## 8. Data And Secret Ownership

OpenPet manages:

- extension installation metadata;
- enabled state;
- service process state;
- setup state;
- OpenPet-created data/cache/log directories;
- health and log summaries;
- any configuration the user enters through OpenPet UI.

Third-party extensions may manage:

- their own databases;
- SMTP credentials;
- API tokens;
- `.env` files;
- external accounts;
- model caches;
- generated files;
- user content.

OpenPet should not claim it can enumerate, audit, or delete every third-party secret or data file.

Manifest should disclose likely locations and external dependencies:

```json
{
  "dataLocations": [
    {
      "path": "OPENPET_DATA_DIR",
      "description": "Service database, report history, and scheduler state."
    },
    {
      "path": "~/.weather-morning-report",
      "description": "Optional developer-managed local configuration."
    }
  ],
  "externalAccounts": [
    "SMTP provider",
    "Weather API provider"
  ]
}
```

## 9. Uninstall And Cleanup

Default uninstall should:

- stop services;
- disable the extension;
- remove the installed package;
- remove OpenPet-owned metadata;
- optionally remove OpenPet-created data/cache/log directories when the user chooses.

Default uninstall should not:

- delete third-party-declared external data locations automatically;
- revoke external accounts;
- delete cloud data;
- assume extension-managed secrets are known.

Extensions may declare cleanup commands. Running cleanup should be explicit.

## 10. Package Shape

An extension package may contain a full application layout:

```text
plugin.json
config.schema.json
commands/
service/
web/
templates/
static/
assets/
bin/
models/
README.md
```

OpenPet should preserve structural safety:

- `plugin.json` must be at package root;
- entries must not escape the installed package;
- absolute paths and path traversal are rejected for package-relative fields;
- extracted symlinks that escape the package are rejected;
- package installation cannot overwrite OpenPet application files.

OpenPet should display:

- package size;
- file count;
- executable-looking entries;
- declared services;
- declared dashboards;
- declared setup and cleanup commands;
- declared data locations.

## 11. Source Labels

OpenPet should preserve source labels:

- `official`;
- `community`;
- `local`.

Source labels affect display and trust messaging only. They should not change runtime capability in the first version.

## 12. Product Language

Use honest language:

- “OpenPet runs local extensions and shows their manifest declarations.”
- “OpenPet manages lifecycle, logs, health, and uninstall flow.”
- “Extensions may run local commands and manage their own data.”
- “OpenPet does not fully sandbox arbitrary local processes.”

Avoid misleading language:

- “fully safe”;
- “complete sandbox”;
- “all secrets are controlled by OpenPet”;
- “OpenPet blocks every undeclared action.”

## 13. First-Version Open Questions

These need implementation-level decisions:

- final command result precedence: result file vs stdout JSON;
- service stop strategy and cross-platform process tree cleanup;
- setup status storage and rerun policy;
- exact bridge token lifetime;
- exact health check timeout and retry behavior;
- UI copy for local/community/official source labels;
- package size warning threshold.

