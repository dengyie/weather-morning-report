"""Local-only web UI for delivery settings."""

from __future__ import annotations

import html
import secrets
import smtplib
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from weather_morning_report.delivery.smtp import send_test_email, test_smtp_connection
from weather_morning_report.settings import DeliverySettings, SettingsStore


def serve_settings(
    path: Path,
    port: int = 8766,
    *,
    host: str = "127.0.0.1",
    open_browser: bool = True,
) -> None:
    store = SettingsStore(path)
    token = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(
        (host, port),
        make_handler(store, token),
    )
    display_host = "127.0.0.1" if host == "0.0.0.0" else host
    url = f"http://{display_host}:{server.server_port}/"
    print(f"Settings UI: {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def make_handler(store: SettingsStore, token: str) -> type[BaseHTTPRequestHandler]:
    class SettingsHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != "/":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self._render(store.load())

        def do_POST(self) -> None:
            if self.path not in {"/save", "/test-smtp", "/send-test-email"}:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                form = self._read_form()
                if form.get("csrf_token", [""])[0] != token:
                    self.send_error(HTTPStatus.FORBIDDEN)
                    return
                current = store.load()
                settings = _settings_from_form(form, current.smtp_password)
                if self.path == "/save":
                    store.save(settings)
                    self._render(settings, "设置已保存。", "success")
                elif self.path == "/test-smtp":
                    test_smtp_connection(settings)
                    self._render(settings, "SMTP 连接和登录验证成功。", "success")
                else:
                    send_test_email(settings)
                    self._render(
                        settings,
                        f"测试邮件已发送至管理员邮箱 {settings.admin_email}。",
                        "success",
                    )
            except (OSError, ValueError, smtplib.SMTPException) as exc:
                self._render(
                    locals().get("settings", store.load()),
                    f"操作失败：{exc}",
                    "error",
                )

        def log_message(self, format: str, *args: object) -> None:
            return

        def _read_form(self) -> dict[str, list[str]]:
            length = int(self.headers.get("Content-Length", "0"))
            return parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)

        def _render(
            self,
            settings: DeliverySettings,
            message: str = "",
            message_kind: str = "",
        ) -> None:
            content = _page(settings, token, message, message_kind).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; form-action 'self'")
            self.end_headers()
            self.wfile.write(content)

    return SettingsHandler


def _settings_from_form(
    form: dict[str, list[str]],
    existing_password: str,
) -> DeliverySettings:
    def value(name: str) -> str:
        return form.get(name, [""])[0].strip()

    password = form.get("smtp_password", [""])[0] or existing_password
    settings = DeliverySettings(
        recipient_name=value("recipient_name"),
        recipient_email=value("recipient_email"),
        admin_email=value("admin_email"),
        sender_email=value("sender_email"),
        smtp_host=value("smtp_host"),
        smtp_port=int(value("smtp_port") or "587"),
        smtp_username=value("smtp_username"),
        smtp_password=password,
        smtp_security=value("smtp_security") or "starttls",
    )
    settings.validate()
    return settings


def _page(
    settings: DeliverySettings,
    token: str,
    message: str,
    message_kind: str,
) -> str:
    def e(value: object) -> str:
        return html.escape(str(value), quote=True)

    def selected(value: str) -> str:
        return " selected" if settings.smtp_security == value else ""

    notice = (
        f'<div class="notice {e(message_kind)}">{e(message)}</div>' if message else ""
    )
    password_hint = "已保存，留空表示保持不变" if settings.smtp_password else "SMTP 密码"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>天气早报设置</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #f1f5f7; color: #24323b; font: 15px/1.5 Arial, sans-serif; }}
    main {{ max-width: 760px; margin: 32px auto; padding: 0 16px 40px; }}
    .card {{ background: white; border-radius: 16px; padding: 26px; box-shadow: 0 8px 30px rgba(30,60,80,.08); }}
    h1 {{ margin: 0 0 6px; color: #17324d; }}
    h2 {{ margin: 28px 0 12px; color: #294e68; font-size: 18px; }}
    .muted {{ color: #6b7e89; margin-top: 0; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    label {{ display: block; color: #49616f; font-weight: bold; }}
    input, select {{ width: 100%; margin-top: 6px; border: 1px solid #cbd7de; border-radius: 8px; padding: 10px 11px; font: inherit; background: white; }}
    input:focus, select:focus {{ outline: 2px solid #8bc3e6; border-color: #4c99ca; }}
    .wide {{ grid-column: 1 / -1; }}
    .actions {{ display: flex; gap: 10px; margin-top: 26px; flex-wrap: wrap; }}
    button {{ border: 0; border-radius: 9px; padding: 11px 18px; font: inherit; font-weight: bold; cursor: pointer; }}
    .primary {{ background: #2477ad; color: white; }}
    .secondary {{ background: #e8f1f6; color: #245675; }}
    .notice {{ margin: 18px 0; border-radius: 8px; padding: 11px 13px; }}
    .success {{ background: #e4f5e9; color: #23643a; }}
    .error {{ background: #fde9e7; color: #8a3028; }}
    .security {{ margin-top: 22px; border-left: 4px solid #e0a528; padding: 8px 12px; color: #66511b; background: #fff9e8; }}
    @media (max-width: 620px) {{ .grid {{ grid-template-columns: 1fr; }} .wide {{ grid-column: auto; }} main {{ margin-top: 12px; }} .card {{ padding: 18px; }} }}
  </style>
</head>
<body>
  <main>
    <div class="card">
      <h1>天气早报设置</h1>
      <p class="muted">配置收件人、管理员通知与 SMTP。页面仅监听本机 127.0.0.1。</p>
      {notice}
      <form method="post">
        <input type="hidden" name="csrf_token" value="{e(token)}">
        <h2>邮件对象</h2>
        <div class="grid">
          <label>收件人称呼<input name="recipient_name" value="{e(settings.recipient_name)}"></label>
          <label>收件人邮箱<input type="email" name="recipient_email" value="{e(settings.recipient_email)}"></label>
          <label>管理员邮箱<input type="email" name="admin_email" value="{e(settings.admin_email)}"></label>
          <label>发件人邮箱<input type="email" name="sender_email" value="{e(settings.sender_email)}"></label>
        </div>
        <h2>SMTP</h2>
        <div class="grid">
          <label class="wide">SMTP 主机<input name="smtp_host" value="{e(settings.smtp_host)}" placeholder="smtp.example.com"></label>
          <label>端口<input type="number" min="1" max="65535" name="smtp_port" value="{e(settings.smtp_port)}"></label>
          <label>加密方式
            <select name="smtp_security">
              <option value="starttls"{selected("starttls")}>STARTTLS</option>
              <option value="ssl"{selected("ssl")}>SSL/TLS</option>
              <option value="plain"{selected("plain")}>无加密（不推荐）</option>
            </select>
          </label>
          <label>SMTP 用户名<input name="smtp_username" value="{e(settings.smtp_username)}"></label>
          <label>SMTP 密码<input type="password" name="smtp_password" placeholder="{e(password_hint)}" autocomplete="new-password"></label>
        </div>
        <p class="security">密码保存在本机设置文件中，文件权限为 600；不会提交到 Git 仓库。</p>
        <div class="actions">
          <button class="primary" type="submit" formaction="/save">保存设置</button>
          <button class="secondary" type="submit" formaction="/test-smtp">测试 SMTP 连接</button>
          <button class="secondary" type="submit" formaction="/send-test-email">发送测试邮件</button>
        </div>
      </form>
    </div>
  </main>
</body>
</html>
"""
