# Legacy Asset Recovery Ledger

This directory preserves product assets and implementation references recovered from commit `7d9e962`.

These files are **not active runtime code** for the current OpenPet command-plugin package. They are retained so the unified Weather Morning Report extension can migrate the previous Web dashboard, Email presentation, SMTP delivery, scheduler, and data model deliberately instead of losing product knowledge.

## Recovered Asset Groups

| Group | Files | Migration Target |
| --- | --- | --- |
| Web templates | `src/weather_morning_report/templates/*.html` | `templates/web/` and `web/` routes |
| Static styles | `src/weather_morning_report/static/app.css` | `static/app.css` |
| Email template catalog | `src/weather_morning_report/email_templates.py` | `rendering/email-template-options.js` |
| HTML Email renderer | `src/weather_morning_report/rendering/html.py` | `rendering/email-renderer.js` and `templates/email/` |
| SMTP delivery | `src/weather_morning_report/delivery/smtp.py` | `service/email/smtp-transport.js` |
| Scheduler and queue | `src/weather_morning_report/jobs.py` | `service/scheduler/` and `service/storage/` |
| Configuration workbench logic | `src/weather_morning_report/configuration.py` | `service/configuration/` and dashboard forms |
| Data model references | `src/weather_morning_report/database/*.py` and migrations | `service/storage/schema.js` or SQLite migrations |
| Historical tests | `tests/test_*.py` | JS service/core/rendering regression tests |

## Rules

- Do not import these files directly from active code.
- Do not package this directory in production extension archives unless a release explicitly needs migration evidence.
- Prefer porting behavior into JavaScript modules with focused tests.
- Keep this directory read-only except when intentionally adding more recovered history.
- The current command-plugin package script does not include this directory; keep that exclusion until assets are deliberately promoted into active `templates/`, `static/`, `rendering/`, `service/`, or `web/` paths.
