# Deploying the Global‑User Report Automation

This guide explains how to deploy **run\_global\_user\_report.py**—a thin wrapper around `daily_odin_report.py`—so that a daily CSV containing *all* BroadWorks users is automatically generated, uploaded to an SFTP server, and e‑mailed to your operations team.

---

## 1. What the Script Does

* **Authenticates** against your Rev.io Odin (BroadWorks) API.
* **Retrieves** every user record across *all* Service Providers.
* **Transforms** the raw data into a clean pandas DataFrame.
* **Exports** the final dataset to one or more CSV files *(split for size, if needed)*.
* **Uploads** those CSVs to the configured SFTP location.
* **E‑mails** the same CSVs as attachments to a recipient list.
* **Logs** each step to stdout **and** to a rotating file in `OUTPUT_DIR`.

All heavy lifting (API, DataFrame logic, retry logic, SFTP, SMTP) is handled by `daily_odin_report.py`; the wrapper only wires the pieces together.

---

## 2. Prerequisites

| Item                   | Notes                                                   |
| ---------------------- | ------------------------------------------------------- |
| Python                 | 3.9 or newer                                            |
| `daily_odin_report.py` | Must reside in the **same** directory as the wrapper    |
| External libraries     | `pandas`, `requests`, `paramiko`, `python-dateutil`     |
| Network                | Outbound access to Odin API, SFTP server, and SMTP host |

---

## 3. Installation Steps

```bash
# 1 — Put all scripts in one folder
sudo mkdir -p /opt/odin
sudo chown $USER /opt/odin
cp run_global_user_report.py daily_odin_report.py /opt/odin/

# 2 — Create a virtual environment (recommended)
python -m venv /opt/odin/venv
source /opt/odin/venv/bin/activate

# 3 — Install dependencies
pip install pandas requests paramiko python-dateutil

# 4 — Make the wrapper executable
chmod +x /opt/odin/run_global_user_report.py
```

---

## 4. Configuration

All runtime options are supplied via **environment variables**. A simple way to manage them is a `.env` file placed next to the scripts.

```dotenv
# ── Odin API ────────────────────────────────────────
ODIN_API_BASE_URL=https://bw-odin.example.com
ODIN_API_USERNAME=bw-api-svc
ODIN_API_PASSWORD=SuperSecret!

# ── SFTP (optional) ─────────────────────────────────
SFTP_HOST=sftp.reporting.example.com
SFTP_PORT=22
SFTP_USERNAME=odin-report
SFTP_PASSWORD=AnotherSecret
SFTP_REMOTE_PATH=/incoming/odin/global_users

# ── SMTP (optional) ─────────────────────────────────
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=reports@yourco.com
SMTP_PASSWORD=EmailSecret
SMTP_FROM=reports@yourco.com
SMTP_TO=ops@yourco.com, noc@yourco.com

# ── Misc tuning ─────────────────────────────────────
OUTPUT_DIR=/var/tmp/odin-global-user-reports
BATCH_SIZE=500          # users per page when calling the API
MAX_RETRIES=3           # network/API retry attempts
RETRY_DELAY=5           # seconds between retries
LOG_LEVEL=INFO          # DEBUG for verbose output
```

> **Security tip:** keep `.env` out of version control (`.gitignore`).

### 4.1 Variable Reference

| Variable            | Required | Default    | Description                          |
| ------------------- | -------- | ---------- | ------------------------------------ |
| `ODIN_API_BASE_URL` | **Yes**  | —          | Base URL of your Odin/BroadWorks API |
| `ODIN_API_USERNAME` | **Yes**  | —          | API user name                        |
| `ODIN_API_PASSWORD` | **Yes**  | —          | API password                         |
| `SFTP_HOST`         | No       | —          | Hostname of target SFTP server       |
| `SFTP_PORT`         | No       | 22         | Port number                          |
| `SFTP_USERNAME`     | No       | —          | SFTP login                           |
| `SFTP_PASSWORD`     | No       | —          | SFTP password or key passphrase      |
| `SFTP_REMOTE_PATH`  | No       | `/`        | Remote directory for CSVs            |
| `SMTP_HOST`         | No       | —          | SMTP relay for e‑mails               |
| `SMTP_PORT`         | No       | 25         | Port (25, 465, 587 supported)        |
| `SMTP_USERNAME`     | No       | —          | SMTP login                           |
| `SMTP_PASSWORD`     | No       | —          | SMTP password                        |
| `SMTP_FROM`         | No       | —          | Sender address                       |
| `SMTP_TO`           | No       | —          | Comma‑separated recipient list       |
| `OUTPUT_DIR`        | No       | `./output` | Local workspace & log location       |
| `BATCH_SIZE`        | No       | `500`      | Users fetched per API call           |
| `MAX_RETRIES`       | No       | `3`        | Network retry attempts               |
| `RETRY_DELAY`       | No       | `5`        | Seconds between retries              |
| `LOG_LEVEL`         | No       | `INFO`     | `DEBUG`, `INFO`, `WARNING`, `ERROR`  |

---

## 5. Manual Execution

Activate your virtualenv first, then run:

```bash
cd /opt/odin
source venv/bin/activate
python run_global_user_report.py                # normal run
python run_global_user_report.py --debug        # verbose logging
python run_global_user_report.py -c /path/to/prod.env
```

Exit status `0` indicates success; `1` signals an error (useful for CI or health checks).

---

## 6. Scheduling with Cron

1. **Open** the crontab for the user that owns the credentials:

   ```bash
   crontab -e
   ```
2. **Add** the following entry (adjust paths and times):

   ```cron
   # Global user export every day at 02:45 America/New_York
   CRON_TZ=America/New_York
   45 2 * * * /usr/bin/env bash -c 'cd /opt/odin && source venv/bin/activate && ./run_global_user_report.py >> /var/log/odin/global_users.log 2>&1'
   ```
3. **Save** and exit. Cron will pick up the job automatically.

---

## 7. Logging

* **Stdout / Stderr**: captured by cron and appended to the log file you specify in the cron line.
* **Rotating file**: `run_global_user_report.py` also writes to `OUTPUT_DIR/global_user_data.log` with daily rotation (handled by `daily_odin_report.py`).

---

## 8. Troubleshooting

| Symptom                                 | Possible Cause                         | Remedy                                                   |
| --------------------------------------- | -------------------------------------- | -------------------------------------------------------- |
| CSV created locally but missing on SFTP | Incorrect `SFTP_*` variables; firewall | Verify host/port/user/pass; test with `sftp` CLI         |
| E‑mail arrives but has no attachment    | `SMTP_*` okay but `SMTP_TO` empty      | Provide at least one recipient                           |
| "Authentication failed" in logs         | Wrong `ODIN_API_*` credentials         | Reset password; confirm API base URL                     |
| Script exits `1` in cron                | Virtualenv not activated               | Use full venv path or `source venv/bin/activate` in cron |

---

## 9. Updating the Deployment

Whenever `daily_odin_report.py` or the wrapper changes:

```bash
cd /opt/odin
# optional: pull from version‑control
cp /path/to/new/run_global_user_report.py .
cp /path/to/new/daily_odin_report.py .
source venv/bin/activate
pip install --upgrade -r requirements.txt   # if dependencies changed
```

No change to cron or `.env` is needed unless new config keys are introduced.

---

## 10. Security & Compliance Notes

* **Least privilege**: The SFTP and SMTP credentials should be restricted to the minimal permissions required.
* **Secrets management**: Consider injecting variables via a secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault) instead of a plain `.env`.
* **PII handling**: The CSV contains subscriber information—store and transmit it according to your data‑protection policies.

---

### You’re all set!

With the script deployed, configured, and scheduled, your operations team will receive a fresh global‑user CSV every morning, also safely archived on your SFTP server for downstream ingest or audit retention.
