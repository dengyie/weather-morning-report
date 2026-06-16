# Phase 5 Email Delivery Design

> Status: proposed and implemented on `codex/phase-5-email-delivery`.
> Scope: Phase 5 of `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`.
> Non-scope: service-owned scheduler, queue leasing, retries, unified OpenPet package, dashboard auth, storing raw SMTP passwords in JSON.

## Goal

Phase 5 adds the active Email rendering and immediate delivery boundary needed before scheduler work begins.

The implementation should keep the current command-only OpenPet package valid while the companion Fastify service gains testable Email rendering, fake SMTP delivery, send-now behavior, and bounded delivery history.

## Active Capabilities

- Preserve all five legacy Email template options:
  - `1` 暖调风格
  - `2` 行动风格
  - `3` 玻璃渐变
  - `4` 极简风格
  - `5` 仪表风格
- Render an Email payload with:
  - subject
  - plain text body
  - HTML body
  - selected template id
  - selected template label
  - structured action summary
- Add a service delivery function that can:
  - find a recipient from Phase 4 configuration
  - fetch or accept a weather report model
  - render the selected Email template
  - send through an injected transport
  - record bounded delivery history under `OPENPET_DATA_DIR`
- Add service routes:
  - `GET /email/preview`
  - `POST /email/send-now`

## Transport Boundary

Phase 5 must use an adapter shape that supports fake transport in tests:

```js
await transport.send({
  envelope: { from, to },
  subject,
  text,
  html
})
```

The default service transport should remain conservative:

- do not store raw SMTP passwords in `configuration.json`;
- read `SMTP_PASSWORD` from runtime env when real SMTP is attempted;
- never include SMTP password values in responses, logs, or delivery history;
- allow tests to inject a fake transport that records sent messages and returns deterministic message ids.

## Storage

Add `delivery-history.json` under `OPENPET_DATA_DIR`.

Records must be bounded and must include:

- `id`
- `createdAt`
- `recipientId`
- `recipientEmail`
- `reportType`
- `templateId`
- `templateLabel`
- `status`
- `messageId` when available
- redacted `error` when failed

Do not store Email HTML body or raw SMTP secrets in delivery history.

## Rendering Requirements

Email HTML rendering must:

- escape user-controlled values;
- preserve Chinese and English labels;
- preserve greeting visibility, footer text, accent color, and data source visibility;
- render key period rows;
- render umbrella, sunscreen, and clothing actions;
- render current temperature, feels-like, daily range, wind, UV, and risk level when available;
- render visibly distinct CSS classes for all five template styles.

## Testing Requirements

Use TDD.

Required tests:

- all five template options normalize and expose legacy labels;
- all five Email templates render valid HTML with selected template ids/labels;
- Email renderer escapes recipient, location, and footer values;
- English rendering uses English labels;
- fake transport send-now records `sent` history without storing HTML bodies or secrets;
- failed transport records `failed` history with redacted error text;
- `POST /email/send-now` returns 400 for unknown recipients;
- `GET /email/preview` renders HTML without sending Email;
- current `.openpet-plugin.zip` remains command-only.

## Review And Release Gates

Before Phase 5 is committed:

1. Run `npm ci`, `npm test`, `npm run build`, `npm run lint`, `npm run typecheck`, `npm run package:plugin`, and `git diff --check`.
2. Use `production-code-quality-review` on the Phase 5 diff.
3. Fix confirmed findings.
4. Update `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md` with the Phase 5 development record.
5. Commit and push `codex/phase-5-email-delivery`.
