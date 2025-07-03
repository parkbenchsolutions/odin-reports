#!/usr/bin/env python3
"""
User-report automation for Rev.io Odin

Fetches user data from Odin, exports to CSV, uploads to SFTP, and e-mails
attachments.  Choose between:

  • *All* Service Providers    (default)
  • One or more Service Providers  (-s spA spB …)

-------------------------------------------------------------------------
Usage examples
-------------------------------------------------------------------------
# Global (all SPs)
$ python run_user_report.py

# Two specific SPs
$ python run_user_report.py -s acme contoso

# Verbose debug run with alternate env file
$ python run_user_report.py -c /etc/odin/prod.env --debug
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List

from daily_odin_report import (
    Config,
    OdinAPIClient,
    GlobalUserDataProcessor,
    ReportExporter,
    GlobalUserDataExtractor,
)

# ----------------------------------------------------------------------#
# helpers                                                               #
# ----------------------------------------------------------------------#
def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument(
        "-s",
        "--service-providers",
        nargs="+",
        metavar="SP_ID",
        help="Space-separated list of Service-Provider IDs. Omit for ALL SPs.",
    )
    p.add_argument(
        "-c",
        "--config",
        default=".env",
        help="Optional dotenv-style file containing KEY=VALUE pairs",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="Enable DEBUG logging",
    )
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


def _run_single_sp(
    client: OdinAPIClient,
    processor: GlobalUserDataProcessor,
    exporter: ReportExporter,
    sp_id: str,
) -> List[str]:
    """Return list of produced CSV file paths for one SP."""
    logging.info("▶ Fetching users for SP %s", sp_id)
    users = client.get_user_report_for_service_provider(sp_id)
    df_users, df_summary = processor.process_user_data(users)
    csv_paths = list(exporter.export_user_data_to_csv(df_users, df_summary, sp_id))
    logging.info("✓ Finished SP %s  (files: %s)", sp_id, ", ".join(csv_paths))
    return csv_paths


# ----------------------------------------------------------------------#
# main                                                                   #
# ----------------------------------------------------------------------#
def main() -> int:
    args = _parse_args()
    _load_dotenv(args.config)

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s %(levelname)s %(message)s"
    )

    cfg = Config()  # pulls from environment
    if args.service_providers:
        # ----------  Per-SP mode (one or many) ----------
        client = OdinAPIClient(cfg)
        if not client.authenticate():
            logging.error("API authentication failed – aborting.")
            return 1

        proc = GlobalUserDataProcessor(cfg.include_optional_fields)
        exporter = ReportExporter(cfg)

        all_csvs: List[str] = []
        for sp_id in args.service_providers:
            try:
                csvs = _run_single_sp(client, proc, exporter, sp_id)
                all_csvs.extend(csvs)
            except Exception as exc:  # noqa: BLE001
                logging.exception("Error while processing SP %s: %s", sp_id, exc)

        # Deliver combined results (if any)
        if all_csvs:
            if cfg.sftp_host:
                exporter.upload_to_sftp(all_csvs)
            if cfg.smtp_host:
                exporter.send_email_report(
                    all_csvs,
                    {
                        "selected_service_providers": len(args.service_providers),
                        "total_csv_files": len(all_csvs),
                    },
                )
        else:
            logging.warning("No CSVs generated – nothing to deliver.")
            return 1
    else:
        # ----------  Global mode (all SPs) ----------
        ok = GlobalUserDataExtractor(cfg).run()
        if not ok:
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
