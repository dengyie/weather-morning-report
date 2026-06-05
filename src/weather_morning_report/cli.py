"""Command-line entry point."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from weather_morning_report.config import Config
from weather_morning_report.providers.base import ProviderError
from weather_morning_report.service import preview


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="weather-report")
    parser.add_argument(
        "command",
        choices=("preview", "send", "validate-config"),
        help="Operation to perform",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = Config.from_env()
        if args.command == "validate-config":
            print("Configuration is valid.")
            return 0
        if args.command == "preview":
            print(preview(config), end="")
            return 0
        raise SystemExit("'send' is not implemented yet")
    except (ProviderError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    main()
