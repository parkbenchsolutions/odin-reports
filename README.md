# Odin Daily Reporting Toolkit

This repository provides a robust solution for generating daily reports from BroadWorks systems, including both a standalone Python script and interactive Jupyter/Colab notebooks. Clients can automate daily reporting via cron jobs or use the notebooks for ad-hoc analysis and exploration.

---

## Features

- **Automated Daily Call Reports**: Fetches and aggregates call records from all Service Providers.
- **Global User Data Extraction**: Extracts comprehensive user data across all Service Providers.
- **Flexible Output**: Export results to CSV, upload via SFTP, and send summary emails.
- **Interactive Notebooks**: Jupyter/Colab notebooks wrap the script for step-by-step, testable workflows.
- **Easy Configuration**: All credentials and settings are managed via environment variables or notebook cells.

---

## Contents

- `daily_odin_report.py` — Main Python script for automated reporting (cron/job-friendly).
- `odin_daily_call_report_colab_v01.ipynb` — Colab/Jupyter notebook for daily call reports.
- `odin_global_user_report_colab_v01.ipynb` — Colab/Jupyter notebook for global user data extraction.
- `odin_user_report_data_colab_v01.ipynb` — Colab/Jupyter notebook for per-service-provider user reports.

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/odin-daily-reporting-toolkit.git
cd odin-daily-reporting-toolkit
```

### 2. Install Requirements

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Set the following environment variables (e.g., in your shell, `.env` file, or notebook cell):

- `ODIN_API_BASE_URL`
- `ODIN_API_USERNAME`
- `ODIN_API_PASSWORD`
- `REPORT_START_DATE` (optional, default: yesterday)
- `REPORT_END_DATE` (optional, default: yesterday)
- `SFTP_HOST`, `SFTP_USERNAME`, `SFTP_PASSWORD` (optional)
- `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TO` (optional)

### 4. Run the Script (Automated)

```bash
python odin-reports/daily_odin_report.py
```

Schedule with `cron` or Windows Task Scheduler for daily automation.

### 5. Use in Google Colab (Interactive)

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
