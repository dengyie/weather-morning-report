"""Long-running FastAPI administration UI shell."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from weather_morning_report.auth import authenticated_admin, login, logout, logout_all
from weather_morning_report.backups import list_backups, resolve_backup_path
from weather_morning_report.database.core import DatabaseConfig
from weather_morning_report.database.operations import check_consistency
from weather_morning_report.jobs import queue_status
from weather_morning_report.jobs import enqueue_manual_job
from weather_morning_report.database.core import open_session
from weather_morning_report.database.models import RunHistory
from sqlalchemy import select
from weather_morning_report.v3_service import preview_recipient_report, report_digest
from weather_morning_report.providers.base import ProviderError
from weather_morning_report.database.models import (
    BrandingSettings,
    Recipient,
    RecipientEmailPreference,
    utc_now,
)
from weather_morning_report.email_templates import EMAIL_TEMPLATE_OPTIONS
from weather_morning_report.configuration import (
    archive_recipient,
    archive_schedule,
    create_default_schedule_for_recipient,
    load_configuration,
    restore_recipient,
    restore_schedule,
    save_branding,
    save_new_user_defaults,
    save_notifications,
    save_provider,
    save_recipient,
    save_schedule,
    save_smtp,
)

SESSION_COOKIE = "weather_report_session"
PACKAGE_DIR = Path(__file__).resolve().parent
MANUAL_CONFIRMATION_LIFETIME = timedelta(minutes=5)


@dataclass(frozen=True, slots=True)
class ManualConfirmation:
    recipient_id: int
    report_type: str
    session_hash: str
    preview_digest: str
    configuration_digest: str
    expires_at: datetime


def create_app(config: DatabaseConfig | None = None) -> FastAPI:
    database = config or DatabaseConfig.from_env()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.database = database
    app.state.manual_confirmations = {}
    templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")
    app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")

    @app.get("/health/live")
    def health_live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready")
    def health_ready() -> JSONResponse:
        try:
            check_consistency(database)
        except (OSError, ValueError):
            return JSONResponse({"status": "not_ready"}, status_code=503)
        return JSONResponse({"status": "ready"})

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request) -> HTMLResponse:
        if _admin(request, database):
            return RedirectResponse("/", status_code=303)
        return templates.TemplateResponse(request, "login.html", {"error": ""})

    @app.post("/login", response_class=HTMLResponse)
    def login_action(
        request: Request,
        username: str = Form(),
        password: str = Form(),
    ) -> HTMLResponse:
        source = request.client.host if request.client else "unknown"
        result = login(database.path, username=username, password=password, source=source)
        if result.token:
            response = RedirectResponse("/", status_code=303)
            response.set_cookie(
                SESSION_COOKIE,
                result.token,
                max_age=12 * 60 * 60,
                httponly=True,
                samesite="strict",
                secure=request.url.scheme == "https",
            )
            return response
        error = (
            "登录暂时锁定，请稍后重试。"
            if result.locked
            else "用户名或密码不正确。"
        )
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": error},
            status_code=401,
        )

    @app.get("/forgot-password", response_class=HTMLResponse)
    def forgot_password(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "forgot_password.html", {})

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request) -> HTMLResponse:
        admin = _admin(request, database)
        if admin is None:
            return RedirectResponse("/login", status_code=303)
        with open_session(database.path) as session:
            history = tuple(
                session.scalars(
                    select(RunHistory).order_by(RunHistory.id.desc()).limit(20)
                )
            )
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "admin": admin,
                "database_ready": True,
                "queue": queue_status(database.path),
                "configuration": load_configuration(database.path),
                "history": history,
                "backups": list_backups(database.path),
                "csrf_token": _csrf_token(request.cookies[SESSION_COOKIE]),
            },
        )

    @app.get("/backups/{backup_id}/download")
    def backup_download(request: Request, backup_id: int):
        if _admin(request, database) is None:
            return RedirectResponse("/login", status_code=303)
        try:
            path = resolve_backup_path(database.path, backup_id)
        except ValueError:
            return JSONResponse({"detail": "backup not found"}, status_code=404)
        return FileResponse(
            path,
            filename=path.name,
            media_type="application/vnd.sqlite3",
        )

    @app.post("/manual/preview", response_class=HTMLResponse)
    def manual_preview(
        request: Request,
        csrf_token: str = Form(),
        recipient_id: int = Form(),
        report_type: str = Form(),
    ) -> HTMLResponse:
        admin = _verified_admin(request, database, csrf_token)
        if admin is None:
            return RedirectResponse("/login", status_code=303)
        try:
            subject, text, html = preview_recipient_report(
                database,
                recipient_id=recipient_id,
                report_type=report_type,
            )
        except (OSError, ProviderError, ValueError) as exc:
            return templates.TemplateResponse(
                request,
                "manual_preview.html",
                {"error": str(exc), "csrf_token": csrf_token},
                status_code=400,
            )
        return templates.TemplateResponse(
            request,
            "manual_preview.html",
            {
                "error": "",
                "subject": subject,
                "text": text,
                "html": html,
                "recipient_id": recipient_id,
                "report_type": report_type,
                "csrf_token": csrf_token,
                "confirmation_token": _store_manual_confirmation(
                    app,
                    session_token=request.cookies[SESSION_COOKIE],
                    recipient_id=recipient_id,
                    report_type=report_type,
                    preview_digest=report_digest(subject, text, html),
                    configuration_digest=_manual_configuration_digest(
                        database.path, recipient_id
                    ),
                ),
                "preview_digest": report_digest(subject, text, html),
            },
        )

    @app.post("/manual/enqueue")
    def manual_enqueue(
        request: Request,
        csrf_token: str = Form(),
        confirmation_token: str = Form(),
        preview_digest: str = Form(""),
        recipient_id: int = Form(),
        report_type: str = Form(),
    ) -> RedirectResponse:
        admin = _verified_admin(request, database, csrf_token)
        if admin is None:
            return RedirectResponse("/login", status_code=303)
        expected = app.state.manual_confirmations.pop(confirmation_token, None)
        if (
            expected is None
            or expected.expires_at <= utc_now()
            or expected.recipient_id != recipient_id
            or expected.report_type != report_type
            or not secrets.compare_digest(expected.preview_digest, preview_digest)
            or not secrets.compare_digest(
                expected.session_hash,
                sha256(request.cookies[SESSION_COOKIE].encode("utf-8")).hexdigest(),
            )
            or not secrets.compare_digest(
                expected.configuration_digest,
                _manual_configuration_digest(database.path, recipient_id),
            )
        ):
            return RedirectResponse("/", status_code=303)
        enqueue_manual_job(
            database.path,
            recipient_id=recipient_id,
            report_type=report_type,
            preview_digest=expected.preview_digest,
        )
        return RedirectResponse("/", status_code=303)

    @app.get("/configuration", response_class=HTMLResponse)
    def configuration_page(request: Request) -> HTMLResponse:
        return _configuration_response(request, database, templates)

    @app.post("/configuration/recipients", response_class=HTMLResponse)
    def recipient_action(
        request: Request,
        csrf_token: str = Form(),
        recipient_id: int | None = Form(None),
        name: str = Form(),
        email: str = Form(),
        location_name: str = Form(),
        location_query: str = Form(),
        timezone: str = Form(),
        language: str = Form(),
        email_template: str = Form("1"),
        enabled: str | None = Form(None),
    ) -> HTMLResponse:
        admin = _verified_admin(request, database, csrf_token)
        if admin is None:
            return RedirectResponse("/login", status_code=303)
        try:
            is_new_recipient = recipient_id is None
            recipient = save_recipient(
                database.path,
                actor=admin.username,
                recipient_id=recipient_id,
                name=name,
                email=email,
                location_name=location_name,
                location_query=location_query,
                timezone=timezone,
                language=language,
                email_template=email_template,
                enabled=enabled == "on",
            )
            if is_new_recipient:
                create_default_schedule_for_recipient(
                    database.path,
                    actor=admin.username,
                    recipient_id=recipient.id,
                )
        except ValueError as exc:
            return _configuration_response(request, database, templates, str(exc), 400)
        return RedirectResponse("/configuration", status_code=303)

    @app.post("/configuration/recipients/{recipient_id}/archive")
    def recipient_archive(request: Request, recipient_id: int, csrf_token: str = Form()):
        admin = _verified_admin(request, database, csrf_token)
        if admin is None:
            return RedirectResponse("/login", status_code=303)
        archive_recipient(database.path, recipient_id, actor=admin.username)
        return RedirectResponse("/configuration?archived=1", status_code=303)

    @app.post("/configuration/recipients/{recipient_id}/restore")
    def recipient_restore(request: Request, recipient_id: int, csrf_token: str = Form()):
        admin = _verified_admin(request, database, csrf_token)
        if admin is None:
            return RedirectResponse("/login", status_code=303)
        restore_recipient(database.path, recipient_id, actor=admin.username)
        return RedirectResponse("/configuration?archived=1", status_code=303)

    @app.post("/configuration/schedules", response_class=HTMLResponse)
    def schedule_action(
        request: Request,
        csrf_token: str = Form(),
        schedule_id: int | None = Form(None),
        recipient_id: int = Form(),
        local_send_time: str = Form(),
        report_type: str = Form(),
        send_policy: str = Form(),
        enabled: str | None = Form(None),
    ) -> HTMLResponse:
        admin = _verified_admin(request, database, csrf_token)
        if admin is None:
            return RedirectResponse("/login", status_code=303)
        try:
            save_schedule(
                database.path,
                actor=admin.username,
                schedule_id=schedule_id,
                recipient_id=recipient_id,
                local_send_time=local_send_time,
                report_type=report_type,
                send_policy=send_policy,
                enabled=enabled == "on",
            )
        except ValueError as exc:
            return _configuration_response(request, database, templates, str(exc), 400)
        return RedirectResponse("/configuration", status_code=303)

    @app.post("/configuration/schedules/{schedule_id}/archive")
    def schedule_archive(request: Request, schedule_id: int, csrf_token: str = Form()):
        admin = _verified_admin(request, database, csrf_token)
        if admin is None:
            return RedirectResponse("/login", status_code=303)
        archive_schedule(database.path, schedule_id, actor=admin.username)
        return RedirectResponse("/configuration?archived=1", status_code=303)

    @app.post("/configuration/schedules/{schedule_id}/restore")
    def schedule_restore(request: Request, schedule_id: int, csrf_token: str = Form()):
        admin = _verified_admin(request, database, csrf_token)
        if admin is None:
            return RedirectResponse("/login", status_code=303)
        try:
            restore_schedule(database.path, schedule_id, actor=admin.username)
        except ValueError as exc:
            return _configuration_response(request, database, templates, str(exc), 400)
        return RedirectResponse("/configuration?archived=1", status_code=303)

    @app.post("/configuration/smtp", response_class=HTMLResponse)
    def smtp_action(
        request: Request,
        csrf_token: str = Form(),
        host: str = Form(),
        port: int = Form(),
        username: str = Form(),
        password: str = Form(""),
        security: str = Form(),
        sender_email: str = Form(),
    ) -> HTMLResponse:
        admin = _verified_admin(request, database, csrf_token)
        if admin is None:
            return RedirectResponse("/login", status_code=303)
        try:
            save_smtp(
                database,
                actor=admin.username,
                host=host,
                port=port,
                username=username,
                password=password,
                security=security,
                sender_email=sender_email,
            )
        except ValueError as exc:
            return _configuration_response(request, database, templates, str(exc), 400)
        return RedirectResponse("/configuration", status_code=303)

    @app.post("/configuration/providers/{provider_id}", response_class=HTMLResponse)
    def provider_action(
        request: Request,
        provider_id: int,
        csrf_token: str = Form(),
        priority: int = Form(),
        enabled: str | None = Form(None),
        credentials: str = Form(""),
    ) -> HTMLResponse:
        admin = _verified_admin(request, database, csrf_token)
        if admin is None:
            return RedirectResponse("/login", status_code=303)
        try:
            save_provider(
                database,
                provider_id,
                actor=admin.username,
                priority=priority,
                enabled=enabled == "on",
                credentials=credentials,
            )
        except ValueError as exc:
            return _configuration_response(request, database, templates, str(exc), 400)
        return RedirectResponse("/configuration", status_code=303)

    @app.post("/configuration/branding", response_class=HTMLResponse)
    def branding_action(
        request: Request,
        csrf_token: str = Form(),
        report_title: str = Form(),
        greeting_visible: str | None = Form(None),
        footer_text: str = Form(""),
        accent_color: str = Form(),
        data_source_visible: str | None = Form(None),
    ) -> HTMLResponse:
        admin = _verified_admin(request, database, csrf_token)
        if admin is None:
            return RedirectResponse("/login", status_code=303)
        try:
            save_branding(
                database.path,
                actor=admin.username,
                report_title=report_title,
                greeting_visible=greeting_visible == "on",
                footer_text=footer_text,
                accent_color=accent_color,
                data_source_visible=data_source_visible == "on",
            )
        except ValueError as exc:
            return _configuration_response(request, database, templates, str(exc), 400)
        return RedirectResponse("/configuration", status_code=303)

    @app.post("/configuration/notifications", response_class=HTMLResponse)
    def notification_action(
        request: Request,
        csrf_token: str = Form(),
        admin_email: str = Form(""),
        webhook_url: str = Form(""),
        webhook_enabled: str | None = Form(None),
        retention_days: int = Form(),
        alert_cooldown_minutes: int = Form(),
        secret_key_backup_confirmed: str | None = Form(None),
    ) -> HTMLResponse:
        admin = _verified_admin(request, database, csrf_token)
        if admin is None:
            return RedirectResponse("/login", status_code=303)
        try:
            save_notifications(
                database.path,
                actor=admin.username,
                admin_email=admin_email,
                webhook_url=webhook_url,
                webhook_enabled=webhook_enabled == "on",
                retention_days=retention_days,
                alert_cooldown_minutes=alert_cooldown_minutes,
                secret_key_backup_confirmed=secret_key_backup_confirmed == "on",
            )
        except ValueError as exc:
            return _configuration_response(request, database, templates, str(exc), 400)
        return RedirectResponse("/configuration", status_code=303)

    @app.post("/configuration/new-user-defaults", response_class=HTMLResponse)
    def new_user_defaults_action(
        request: Request,
        csrf_token: str = Form(),
        location_name: str = Form(),
        location_query: str = Form(),
        timezone: str = Form(),
        language: str = Form(),
        local_send_time: str = Form(),
        report_type: str = Form(),
        send_policy: str = Form(),
        schedule_enabled: str | None = Form(None),
    ) -> HTMLResponse:
        admin = _verified_admin(request, database, csrf_token)
        if admin is None:
            return RedirectResponse("/login", status_code=303)
        try:
            save_new_user_defaults(
                database.path,
                actor=admin.username,
                location_name=location_name,
                location_query=location_query,
                timezone=timezone,
                language=language,
                local_send_time=local_send_time,
                report_type=report_type,
                send_policy=send_policy,
                schedule_enabled=schedule_enabled == "on",
            )
        except ValueError as exc:
            return _configuration_response(request, database, templates, str(exc), 400)
        return RedirectResponse("/configuration", status_code=303)

    @app.post("/logout")
    def logout_action(request: Request) -> RedirectResponse:
        logout(database.path, request.cookies.get(SESSION_COOKIE))
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(SESSION_COOKIE)
        return response

    @app.post("/logout-all")
    def logout_all_action(
        request: Request,
        csrf_token: str = Form(),
    ) -> RedirectResponse:
        admin = _verified_admin(request, database, csrf_token)
        if admin is None:
            return RedirectResponse("/login", status_code=303)
        logout_all(database.path, admin.username)
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(SESSION_COOKIE)
        return response

    return app


def serve_ui(config: DatabaseConfig | None = None) -> None:
    database = config or DatabaseConfig.from_env()
    check_consistency(database)
    uvicorn.run(
        create_app(database),
        host=os.getenv("WEB_BIND", "127.0.0.1"),
        port=int(os.getenv("WEB_PORT", "8766")),
    )


def _admin(request: Request, config: DatabaseConfig):
    return authenticated_admin(config.path, request.cookies.get(SESSION_COOKIE))


def _configuration_response(
    request: Request,
    config: DatabaseConfig,
    templates: Jinja2Templates,
    error: str = "",
    status_code: int = 200,
) -> HTMLResponse:
    admin = _admin(request, config)
    if admin is None:
        return RedirectResponse("/login", status_code=303)
    include_archived = request.query_params.get("archived") == "1"
    return templates.TemplateResponse(
        request,
        "configuration.html",
        {
            "admin": admin,
            "configuration": load_configuration(
                config.path, include_archived=include_archived
            ),
            "include_archived": include_archived,
            "csrf_token": _csrf_token(request.cookies[SESSION_COOKIE]),
            "email_template_options": EMAIL_TEMPLATE_OPTIONS,
            "error": error,
        },
        status_code=status_code,
    )


def _verified_admin(request: Request, config: DatabaseConfig, csrf_token: str):
    token = request.cookies.get(SESSION_COOKIE)
    if not token or not secrets.compare_digest(_csrf_token(token), csrf_token):
        return None
    return authenticated_admin(config.path, token)


def _csrf_token(session_token: str) -> str:
    return sha256(f"csrf:{session_token}".encode("utf-8")).hexdigest()


def _store_manual_confirmation(
    app: FastAPI,
    *,
    session_token: str,
    recipient_id: int,
    report_type: str,
    preview_digest: str,
    configuration_digest: str,
) -> str:
    if len(app.state.manual_confirmations) >= 100:
        app.state.manual_confirmations.pop(next(iter(app.state.manual_confirmations)))
    token = secrets.token_urlsafe(24)
    app.state.manual_confirmations[token] = ManualConfirmation(
        recipient_id=recipient_id,
        report_type=report_type,
        session_hash=sha256(session_token.encode("utf-8")).hexdigest(),
        preview_digest=preview_digest,
        configuration_digest=configuration_digest,
        expires_at=utc_now() + MANUAL_CONFIRMATION_LIFETIME,
    )
    return token


def _manual_configuration_digest(path: Path, recipient_id: int) -> str:
    with open_session(path) as session:
        recipient = session.get(Recipient, recipient_id)
        branding = session.get(BrandingSettings, 1)
        email_preference = session.scalar(
            select(RecipientEmailPreference).where(
                RecipientEmailPreference.recipient_id == recipient_id
            )
        )
        if recipient is None or branding is None:
            return ""
        email_template = email_preference.email_template if email_preference else "1"
        values = (
            recipient.name,
            recipient.email,
            recipient.location_name,
            recipient.location_query,
            recipient.timezone,
            recipient.language,
            recipient.enabled,
            recipient.archived_at,
            recipient.updated_at,
            email_template,
            branding.report_title,
            branding.greeting_visible,
            branding.footer_text,
            branding.accent_color,
            branding.data_source_visible,
        )
    return sha256(repr(values).encode("utf-8")).hexdigest()
