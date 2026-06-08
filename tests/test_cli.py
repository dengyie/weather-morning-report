from pathlib import Path

from weather_morning_report import cli
from weather_morning_report.cli import build_parser, main


def test_parser_accepts_documented_commands() -> None:
    for command in (
        "preview",
        "send",
        "validate-config",
        "settings",
        "setup",
        "serve-ui",
        "serve-worker",
    ):
        assert build_parser().parse_args([command]).command == command


def test_preview_parser_accepts_html_format() -> None:
    args = build_parser().parse_args(["preview", "--format", "html"])

    assert args.command == "preview"
    assert args.format == "html"


def test_settings_parser_accepts_container_host() -> None:
    args = build_parser().parse_args(
        ["settings", "--host", "0.0.0.0", "--port", "9999", "--no-browser"]
    )

    assert args.command == "settings"
    assert args.host == "0.0.0.0"
    assert args.port == 9999
    assert args.no_browser is True


def test_settings_command_passes_container_host(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        cli,
        "serve_settings",
        lambda path, *, host, port, open_browser: calls.append(
            (path, host, port, open_browser)
        ),
    )

    assert main(["settings", "--host", "0.0.0.0", "--no-browser"]) == 0
    assert calls == [(Path("var/settings.json"), "0.0.0.0", 8766, False)]


def test_validate_config_succeeds(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        cli,
        "validate_configuration",
        lambda config: "Configuration is valid; weather provider reachable via fixture.",
    )

    assert main(["validate-config"]) == 0
    assert (
        capsys.readouterr().out
        == "Configuration is valid; weather provider reachable via fixture.\n"
    )


def test_invalid_timezone_returns_cli_error(capsys, monkeypatch) -> None:
    monkeypatch.setenv("TIMEZONE", "Invalid/Timezone")

    assert main(["preview"]) == 1
    assert capsys.readouterr().out == "Error: TIMEZONE is invalid: Invalid/Timezone\n"


def test_setup_command_does_not_load_legacy_config(capsys, monkeypatch, tmp_path) -> None:
    calls = []
    monkeypatch.setenv("TIMEZONE", "Invalid/Timezone")
    monkeypatch.setenv("WEATHER_REPORT_DB_PATH", str(tmp_path / "report.db"))
    monkeypatch.setenv("WEATHER_REPORT_SECRET_KEY_FILE", str(tmp_path / "secret.key"))
    monkeypatch.setattr(cli, "_prompt_new_admin", lambda: ("admin", "secure password"))
    monkeypatch.setattr(
        cli,
        "initialize_installation",
        lambda config, **values: calls.append((config, values)),
    )

    assert main(["setup", "--timezone", "Asia/Shanghai"]) == 0
    assert calls[0][1]["default_timezone"] == "Asia/Shanghai"
    assert "Installation initialized" in capsys.readouterr().out


def test_admin_reset_password_uses_v3_database_config(capsys, monkeypatch, tmp_path) -> None:
    calls = []
    monkeypatch.setenv("WEATHER_REPORT_DB_PATH", str(tmp_path / "report.db"))
    monkeypatch.setenv("WEATHER_REPORT_SECRET_KEY_FILE", str(tmp_path / "secret.key"))
    monkeypatch.setattr(cli, "_prompt_new_password", lambda: "secure password")
    monkeypatch.setattr(
        cli,
        "reset_admin_password",
        lambda config, password: calls.append((config, password)),
    )

    assert main(["admin", "reset-password"]) == 0
    assert calls[0][1] == "secure password"
    assert "sessions revoked" in capsys.readouterr().out
