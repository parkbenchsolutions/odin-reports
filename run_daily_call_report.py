#!/usr/bin/env python3
"""
Light-weight wrapper that turns daily_odin_report.py into a pure CLI/cron
utility.  --help shows all options.

Usage examples
--------------
❯ python run_daily_call_report.py --report daily        # default (=call report)
❯ python run_daily_call_report.py --report users        # global user export
❯ python run_daily_call_report.py --start-date 2026-01-26 --end-date 2026-01-27
"""

import argparse, sys, logging, os, re
from pathlib import Path
from dotenv import load_dotenv

# Import the two orchestrators already defined in daily_odin_report.py
from daily_odin_report import (
    Config,
    DailyCallReportGenerator,
    GlobalUserDataExtractor,
)

# Regex patterns for date validation
DATE_ONLY_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
DATETIME_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')


def normalize_date(value: str, is_start: bool) -> str:
    """
    Normalize a date string to 'YYYY-MM-DD HH:MM:SS' format.
    
    - If value is 'YYYY-MM-DD', expand to '00:00:00' (start) or '23:59:59' (end).
    - If value is already 'YYYY-MM-DD HH:MM:SS', return as-is.
    - Otherwise raise ValueError.
    """
    if DATE_ONLY_PATTERN.match(value):
        suffix = "00:00:00" if is_start else "23:59:59"
        return f"{value} {suffix}"
    if DATETIME_PATTERN.match(value):
        return value
    raise ValueError(
        f"Invalid date format: '{value}'. "
        "Use 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'."
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run Odin daily call report or global user data extraction"
    )
    p.add_argument(
        "-r", "--report",
        choices=["daily", "users"],
        default="daily",
        help="Which report to run: daily (call records) or users (global user data)"
    )
    p.add_argument(
        "-c", "--config",
        default=".env",
        help="Optional dotenv-style file with KEY=VALUE pairs"
    )
    p.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    p.add_argument(
        "--start-date",
        dest="start_date",
        default=None,
        metavar="DATE",
        help="Report start date (YYYY-MM-DD or 'YYYY-MM-DD HH:MM:SS'). Requires --end-date."
    )
    p.add_argument(
        "--end-date",
        dest="end_date",
        default=None,
        metavar="DATE",
        help="Report end date (YYYY-MM-DD or 'YYYY-MM-DD HH:MM:SS'). Requires --start-date."
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # ---------- Validate date flags ----------
    has_start = args.start_date is not None
    has_end = args.end_date is not None

    if has_start != has_end:
        sys.exit("Error: --start-date and --end-date must be used together.")

    if (has_start or has_end) and args.report == "users":
        sys.exit("Error: --start-date/--end-date apply only to the 'daily' report, not 'users'.")

    # ---------- Normalize and set date env vars ----------
    start_dt: str | None = None
    end_dt: str | None = None

    if has_start and has_end:
        try:
            start_dt = normalize_date(args.start_date, is_start=True)
            end_dt = normalize_date(args.end_date, is_start=False)
        except ValueError as e:
            sys.exit(f"Error: {e}")

        os.environ['REPORT_START_DATE'] = start_dt
        os.environ['REPORT_END_DATE'] = end_dt

    # ---------- Load .env (won't overwrite vars already set) ----------
    load_dotenv(args.config)

    # ---------- Debug output ----------
    if args.debug:
        print(f"DEBUG: ODIN_API_BASE_URL = '{os.getenv('ODIN_API_BASE_URL')}'")
        print(f"DEBUG: ODIN_API_USERNAME = '{os.getenv('ODIN_API_USERNAME')}'")
        print(f"DEBUG: Config file loaded: {args.config}")
        print(f"DEBUG: REPORT_START_DATE = '{os.getenv('REPORT_START_DATE', '(default: yesterday)')}'")
        print(f"DEBUG: REPORT_END_DATE   = '{os.getenv('REPORT_END_DATE', '(default: yesterday)')}'")

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s %(levelname)s %(message)s"
    )

    cfg = Config()  # pulls from environment

    if args.report == "daily":
        ok = DailyCallReportGenerator(cfg).run()
    else:
        ok = GlobalUserDataExtractor(cfg).run()

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

