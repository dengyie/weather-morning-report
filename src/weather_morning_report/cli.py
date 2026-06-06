"""Command-line entry point."""

from __future__ import annotations

import argparse
import smtplib
from collections.abc import Sequence

from weather_morning_report.config import Config
from weather_morning_report.providers.base import ProviderError
from weather_morning_report.service import preview, send_report
from weather_morning_report.webui import serve_settings


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
    subparsers.add_parser("send", help="Generate and send the weather report")
    subparsers.add_parser("validate-config", help="Validate local configuration")
    settings_parser = subparsers.add_parser(
        "settings",
        help="Open the local delivery settings UI",
    )
    settings_parser.add_argument("--port", type=int, default=8766)
    settings_parser.add_argument("--no-browser", action="store_true")
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
        if args.command == "settings":
            serve_settings(
                config.settings_path,
                port=args.port,
                open_browser=not args.no_browser,
            )
            return 0
        if args.command == "send":
            print(send_report(config))
            return 0
    except (OSError, ProviderError, ValueError, smtplib.SMTPException) as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    main()
