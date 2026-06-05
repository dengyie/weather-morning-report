"""Command-line entry point."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from weather_morning_report.config import Config
from weather_morning_report.providers.base import ProviderError
from weather_morning_report.service import preview


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="weather-report")
    subparsers = parser.add_subparsers(dest="command", required=True)
    preview_parser = subparsers.add_parser(
        "preview",
        help="Render a live report preview",
    )
    preview_parser.add_argument(
        "--format",
        choices=("text", "html"),
        default="text",
        help="Preview output format",
    )
    subparsers.add_parser("send", help="Send the report (not implemented yet)")
    subparsers.add_parser("validate-config", help="Validate local configuration")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = Config.from_env()
        if args.command == "validate-config":
            print("Configuration is valid.")
            return 0
        if args.command == "preview":
            print(preview(config, output_format=args.format), end="")
            return 0
        raise SystemExit("'send' is not implemented yet")
    except (ProviderError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    main()
