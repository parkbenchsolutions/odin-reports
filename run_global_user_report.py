#!/usr/bin/env python3
"""
Global-user export for Rev.io Odin

Calls the GlobalUserDataExtractor class in daily_odin_report.py, then
optionally ships the resulting CSV(s) via SFTP and/or e-mail.

Typical usage
-------------
# one-off, using .env for config
$ python run_global_user_report.py

# verbose run without .env
$ ODIN_API_BASE_URL=https://bw-odin.example.com \
  ODIN_API_USERNAME=bw-api-svc \
  ODIN_API_PASSWORD=SuperSecret! \
  python run_global_user_report.py --debug
"""

import argparse, logging, os, sys
from pathlib import Path
from dotenv import load_dotenv

from daily_odin_report import Config, GlobalUserDataExtractor      # noqa: E402

# --------------------------------------------------------------------------- #
# helpers                                                                     #
# --------------------------------------------------------------------------- #
def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("-c", "--config", default=".env",
                   help="Optional dotenv file with KEY=VALUE pairs")
    p.add_argument("--debug", action="store_true",
                   help="Enable DEBUG logging")
    return p.parse_args()


# --------------------------------------------------------------------------- #
# main                                                                        #
# --------------------------------------------------------------------------- #
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
    
    # Additional debug output for Config values
    if args.debug:
        print(f"DEBUG: Config loaded with:")
        print(f"  api_base_url: '{cfg.api_base_url}'")
        print(f"  api_username: '{cfg.api_username}'")
        print(f"  api_password: {'*' * len(cfg.api_password) if cfg.api_password else '(empty)'}")
      
    extractor = GlobalUserDataExtractor(cfg)

    ok = extractor.run()                          # handles SFTP + e-mail
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

