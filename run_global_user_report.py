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


def _load_dotenv(dotenv_path: str) -> None:
    """Tiny .env reader (avoids extra dependency)."""
    env_file = Path(dotenv_path)
    if not env_file.is_file():
        return
    for line in env_file.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        k, _, v = line.partition("=")
        if k and v:
            os.environ.setdefault(k.strip(), v.strip())


# --------------------------------------------------------------------------- #
# main                                                                        #
# --------------------------------------------------------------------------- #
def main() -> int:
    args = _parse_args()
    _load_dotenv(args.config)

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level,
                        format="%(asctime)s %(levelname)s %(message)s")

    cfg = Config()                                # pulls everything from env
    extractor = GlobalUserDataExtractor(cfg)

    ok = extractor.run()                          # handles SFTP + e-mail
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
