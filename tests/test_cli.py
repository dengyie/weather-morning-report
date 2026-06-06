from weather_morning_report import cli
from weather_morning_report.cli import build_parser, main


def test_parser_accepts_documented_commands() -> None:
    for command in ("preview", "send", "validate-config", "settings"):
        assert build_parser().parse_args([command]).command == command


def test_preview_parser_accepts_html_format() -> None:
    args = build_parser().parse_args(["preview", "--format", "html"])

    assert args.command == "preview"
    assert args.format == "html"


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
