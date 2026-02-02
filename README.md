# Odin Daily Reporting Toolkit

This repository provides a robust solution for generating daily reports from BroadWorks systems, including both a standalone Python script and interactive Jupyter/Colab notebooks. Clients can automate daily reporting via cron jobs or use the notebooks for ad-hoc analysis and exploration.

---

## Features

- **Automated Daily Call Reports**: Fetches and aggregates call records from all Service Providers.
- **Global User Data Extraction**: Extracts comprehensive user data across all Service Providers.
- **Per Service Provider User Reports**: Fetches comprehensive user data across select Service Providers.
- **Flexible Output**: Export results to CSV, upload via SFTP, and send summary emails.
- **Interactive Notebooks**: Jupyter/Colab notebooks wrap the script for step-by-step, testable workflows.
- **Easy Configuration**: All credentials and settings are managed via environment variables or notebook cells.

---

## Contents

- **`daily_odin_report.py`** — Main Python script for automated reporting (cron/job-friendly).

### 🧑‍💻 Interactive Jupyter/Colab Notebooks
For interactive, step-by-step reporting, data exploration, and ad-hoc analysis, this repository provides ready-to-use Jupyter/Colab notebooks:

- **`odin_daily_call_report_{colab/vscode}_v##.ipynb`** — Colab/Jupyter notebook for daily call reports. Lets you configure, run, and analyze daily call detail records interactively.
- **`odin_global_user_report_{colab/vscode}_v##.ipynb`** — Colab/Jupyter notebook for global user data extraction. Extracts and explores user data across all Service Providers.
- **`odin_user_report_data_{colab/vscode}_v##.ipynb`** — Colab/Jupyter notebook for per-service-provider user reports. Generate and analyze user reports for individual Service Providers.

Each notebook:
- Wraps the core logic in `daily_odin_report.py` for modular, testable execution
- Allows configuration of variables and environment in the notebook UI
- Supports exporting results to CSV, SFTP, and email (where configured)
- Is ideal for development, troubleshooting, and custom reporting workflows

### 🚦 Cron Automation Wrappers & Deployment

To simplify production automation and scheduling, this repository includes **thin wrapper Python scripts** around `daily_odin_report.py` for direct use in cron jobs and server environments:

- **`run_daily_call_report.py`** — Automates daily call detail record (CDR) reporting for all Service Providers. Designed for cron, with SFTP/email delivery. See [deploy_Daily‑Call-Report.md](./deploy_Daily‑Call-Report.md) for setup.
- **`run_user_report.py`** — Exports user data for all or selected Service Providers. Flexible for global or per-SP reporting. See [deploy_SP‑User-Report.md](./deploy_SP‑User-Report.md) for deployment instructions.
- **`run_global_user_report.py`** — Generates a global user export (all Service Providers) and delivers via SFTP/email. See [deploy_Global‑User-Report.md](./deploy_Global‑User-Report.md) for details.

Each wrapper script:
- Loads configuration from environment variables or a `.env` file
- Handles all orchestration, logging, and error handling
- Calls into `daily_odin_report.py` for the core reporting logic
- Is ready for use in cron jobs or other automation tools

**Deployment Guides:**
- [Daily Call Report Deployment](./deploy_Daily‑Call-Report.md)
- [Global User Report Deployment](./deploy_Global‑User-Report.md)
- [Select/All-SP User Report Deployment](./deploy_SP‑User-Report.md)
---

## Quick Start

### Use in Google Colab (Interactive)

- Open any of the provided `.ipynb` notebooks in [Google Colab](https://colab.research.google.com/).
- Upload the latest `daily_odin_report.py` when prompted.
- Configure variables in the first cell.
- Run each cell step-by-step for interactive exploration and export.

---

## Output

- **CSV Reports**: Raw and aggregated data saved to the `reports/` directory.
- **SFTP Upload**: (Optional) Automatically uploads reports to a configured SFTP server.
- **Email Delivery**: (Optional) Sends summary and attachments to configured recipients.

---

## Security

- **Credentials**: Never commit sensitive credentials to the repository. Use environment variables or Colab secrets.
- **Client Data**: All data is processed locally or in your Colab session; no data is sent to third parties except as configured (SFTP/email).

---

## Support

For issues, feature requests, or questions, please open a GitHub Issue or contact your Odin support representative.

---

## License

[MIT License](LICENSE)

---

*Empowering Odin clients with flexible, transparent, and automated reporting.*
