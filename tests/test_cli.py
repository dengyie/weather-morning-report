from pathlib import Path

from weather_morning_report import cli
from weather_morning_report.cli import build_parser, main


def test_parser_accepts_documented_commands() -> None:
    for command in ("preview", "send", "validate-config", "settings"):
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
