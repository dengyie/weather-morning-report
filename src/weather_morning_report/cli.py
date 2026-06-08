"""Command-line entry point."""

from __future__ import annotations

import argparse
import getpass
import smtplib
from collections.abc import Sequence
from pathlib import Path

from weather_morning_report.config import Config
from weather_morning_report.database.core import DatabaseConfig
from weather_morning_report.database.operations import (
    create_admin,
    initialize_installation,
    reset_admin_password,
    restore_installation,
    upgrade_installation,
)
from weather_morning_report.providers.base import ProviderError
from weather_morning_report.service import preview, send_report, validate_configuration
from weather_morning_report.ui import serve_ui
from weather_morning_report.webui import serve_settings
from weather_morning_report.worker import WorkerAlreadyRunningError, serve_worker


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
    settings_parser.add_argument("--host", default="127.0.0.1")
    settings_parser.add_argument("--port", type=int, default=8766)
    settings_parser.add_argument("--no-browser", action="store_true")

    setup_parser = subparsers.add_parser("setup", help="Initialize or maintain v3 data")
    setup_parser.add_argument("--timezone", default="Asia/Shanghai")
    setup_subparsers = setup_parser.add_subparsers(dest="setup_command")
    setup_subparsers.add_parser("upgrade", help="Back up and upgrade the v3 database")
    restore_parser = setup_subparsers.add_parser(
        "restore",
        help="Restore and upgrade a v3 database backup",
    )
    restore_parser.add_argument("path", type=Path)

    admin_parser = subparsers.add_parser("admin", help="Manage the v3 administrator")
    admin_subparsers = admin_parser.add_subparsers(dest="admin_command", required=True)
    admin_subparsers.add_parser("create", help="Create the single administrator")
    admin_subparsers.add_parser(
        "reset-password",
        help="Reset the administrator password and revoke sessions",
    )
    subparsers.add_parser("serve-ui", help="Run the v3 administration UI")
    subparsers.add_parser("serve-worker", help="Run the v3 report worker")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "setup":
            database = DatabaseConfig.from_env()
            if args.setup_command == "upgrade":
                backup = upgrade_installation(database)
                print(f"Database upgraded; backup preserved at {backup}.")
                return 0
            if args.setup_command == "restore":
                backup = restore_installation(database, args.path)
                suffix = f"; previous database preserved at {backup}" if backup else ""
                print(f"Database restored and upgraded{suffix}.")
                return 0
            username, password = _prompt_new_admin()
            initialize_installation(
                database,
                username=username,
                password=password,
                default_timezone=args.timezone,
            )
            print(
                "Installation initialized. Start the UI and worker after "
                "configuration is complete."
            )
            return 0
        if args.command == "admin":
            database = DatabaseConfig.from_env()
            if args.admin_command == "create":
                username, password = _prompt_new_admin()
                create_admin(database, username, password)
                print("Administrator created.")
                return 0
            password = _prompt_new_password()
            reset_admin_password(database, password)
            print("Administrator password reset; all sessions revoked.")
            return 0
        if args.command == "serve-ui":
            serve_ui(DatabaseConfig.from_env())
            return 0
        if args.command == "serve-worker":
            serve_worker(DatabaseConfig.from_env())
            return 0

        config = Config.from_env()
        if args.command == "validate-config":
            print(validate_configuration(config))
            return 0
        if args.command == "preview":
            print(preview(config, output_format=args.format), end="")
            return 0
        if args.command == "settings":
            serve_settings(
                config.settings_path,
                host=args.host,
                port=args.port,
                open_browser=not args.no_browser,
            )
            return 0
        if args.command == "send":
            print(send_report(config))
            return 0
    except (
        OSError,
        ProviderError,
        ValueError,
        WorkerAlreadyRunningError,
        smtplib.SMTPException,
    ) as exc:
        print(f"Error: {exc}")
        return 1


def _prompt_new_admin() -> tuple[str, str]:
    username = input("Administrator username: ").strip()
    return username, _prompt_new_password()


def _prompt_new_password() -> str:
    password = getpass.getpass("Administrator password: ")
    confirmation = getpass.getpass("Confirm administrator password: ")
    if password != confirmation:
        raise ValueError("administrator passwords do not match")
    return password


if __name__ == "__main__":
    main()
