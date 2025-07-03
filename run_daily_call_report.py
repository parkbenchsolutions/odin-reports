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

def load_dotenv(dotenv_path: str):
    """Very small .env reader so you don’t have to install python-dotenv."""
    if not Path(dotenv_path).exists():
        return
    with open(dotenv_path) as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            k, _, v = line.partition("=")
            if k and v:
                os.environ.setdefault(k.strip(), v.strip())

def main() -> int:
    args = parse_args()
    load_dotenv(args.config)
    cfg = Config()        # pulls every setting from environment variables
    logging.getLogger().setLevel(logging.INFO)

    if args.report == "daily":
        ok = DailyCallReportGenerator(cfg).run()
    else:
        ok = GlobalUserDataExtractor(cfg).run()

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
