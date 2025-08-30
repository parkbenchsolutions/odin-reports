#!/usr/bin/env python3
"""
Light-weight wrapper that turns daily_odin_report.py into a pure CLI/cron
utility.  --help shows all options.

Usage examples
--------------
❯ python run_daily_call_report.py --report daily        # default (=call report)
❯ python run_daily_call_report.py --report users        # global user export
"""

import argparse, sys, logging
from pathlib import Path
from dotenv import load_dotenv

# Import the two orchestrators already defined in daily_odin_report.py
from daily_odin_report import (
    Config,
    DailyCallReportGenerator,
    GlobalUserDataExtractor,
)

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
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
    return p.parse_args()

def main() -> int:
    args = _parse_args()
    
    # Load environment variables FIRST, before creating Config
    load_dotenv(args.config)
    
    # Debug: Print loaded environment variables
    if args.debug:
        print(f"DEBUG: ODIN_API_BASE_URL = '{os.getenv('ODIN_API_BASE_URL')}'")
        print(f"DEBUG: ODIN_API_USERNAME = '{os.getenv('ODIN_API_USERNAME')}'")
        print(f"DEBUG: Config file loaded: {args.config}")

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

