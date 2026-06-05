from weather_morning_report.cli import build_parser, main


def test_parser_accepts_documented_commands() -> None:
    for command in ("preview", "send", "validate-config"):
        assert build_parser().parse_args([command]).command == command


def test_validate_config_succeeds(capsys) -> None:
    assert main(["validate-config"]) == 0
    assert capsys.readouterr().out == "Configuration is valid.\n"
