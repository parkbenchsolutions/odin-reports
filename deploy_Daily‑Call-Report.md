# Deploying the Daily Call‑Report Automation

This guide documents **run\_daily\_call\_report.py**, the thin wrapper around `daily_odin_report.py` that automatically delivers a **Daily Call Detail Record (CDR) report** for *all* Service Providers in your Rev.io Odin (BroadWorks) cluster.

---

## 1 · What the Script Does

| Stage            | Description                                                                                                                                                      |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Authenticate** | Logs in to the Odin API using service credentials.                                                                                                               |
| **Collect**      | Fetches previous day’s call data (start/end timestamps, caller, callee, duration, cost, trunk group, etc.).                                                      |
| **Transform**    | Builds a pandas DataFrame, applies friendly column names, converts timestamps to your local TZ, and splits large datasets into multiple CSVs when size > 100 MB. |
| **Export**       | Writes the CSV file(s) to `OUTPUT_DIR`, naming them `<YYYY‑MM‑DD>_call_report_[n].csv`.                                                                          |
| **Deliver**      | *If configured*—uploads the CSVs to your SFTP drop‑zone **and** sends them as e‑mail attachments.                                                                |
| **Log**          | Streams progress to stdout and to `OUTPUT_DIR/daily_call_report.log` (rotated daily).                                                                            |

All heavy lifting—API paging, retries, SFTP, SMTP—is implemented in `daily_odin_report.py`; the wrapper only wires things together.

---

## 2 · Prerequisites

| Requirement            | Notes                                                             |
| ---------------------- | ----------------------------------------------------------------- |
| Python ≥ 3.9           | CPython recommended                                               |
| `daily_odin_report.py` | Must reside in the *same* directory as `run_daily_call_report.py` |
| Libraries              | `pandas`, `requests`, `paramiko`, `python-dateutil`               |
| Network access         | Outbound to Odin API, SFTP host, and SMTP relay                   |

---

## 3 · Installation Steps

```bash
# 1 — Folder layout
sudo mkdir -p /opt/odin
sudo chown $USER /opt/odin
cp run_daily_call_report.py daily_odin_report.py /opt/odin/

# 2 — Virtualenv (recommended)
python -m venv /opt/odin/venv
source /opt/odin/venv/bin/activate
pip install pandas requests paramiko python-dateutil

# 3 — Make wrapper executable
chmod +x /opt/odin/run_daily_call_report.py
```

---

## 4 · Configuration (.env)

All runtime settings are environment variables. Place a `.env` next to the scripts (or point to another file with `-c`).

```dotenv
# ── Odin API ──────────────────────────────────────────
ODIN_API_BASE_URL=https://bw-odin.example.com
ODIN_API_USERNAME=bw-api-svc
ODIN_API_PASSWORD=SuperSecret!

# ── SFTP (optional) ───────────────────────────────────
SFTP_HOST=sftp.reporting.example.com
SFTP_PORT=22
SFTP_USERNAME=odin-report
SFTP_PASSWORD=AnotherSecret
SFTP_REMOTE_PATH=/incoming/odin/call_reports

# ── SMTP (optional) ───────────────────────────────────
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=reports@yourco.com
SMTP_PASSWORD=EmailSecret
SMTP_FROM=reports@yourco.com
SMTP_TO=ops@yourco.com, noc@yourco.com

# ── Misc tuning ───────────────────────────────────────
OUTPUT_DIR=/var/tmp/odin-call-reports
BATCH_SIZE=1000            # records per API page
MAX_RETRIES=3              # network/API retries
RETRY_DELAY=5              # seconds between retries
LOG_LEVEL=INFO             # DEBUG for full verbosity
DATE_OFFSET_DAYS=1         # 1 = yesterday (default)
```

> **Tip:** Add `.env` to `.gitignore` and restrict permissions (`chmod 600`).

### 4.1 Variable Reference

| Var                 | Req. | Default    | Purpose                             |
| ------------------- | ---- | ---------- | ----------------------------------- |
| `ODIN_API_BASE_URL` | ✅    | —          | Base REST endpoint                  |
| `ODIN_API_USERNAME` | ✅    | —          | API user                            |
| `ODIN_API_PASSWORD` | ✅    | —          | Password/token                      |
| `SFTP_HOST`         | —    | —          | Hostname/IP of SFTP target          |
| `SFTP_PORT`         | —    | 22         | Port                                |
| `SFTP_USERNAME`     | —    | —          | Login name                          |
| `SFTP_PASSWORD`     | —    | —          | Password or key passphrase          |
| `SFTP_REMOTE_PATH`  | —    | `/`        | Target directory                    |
| `SMTP_HOST`         | —    | —          | SMTP relay                          |
| `SMTP_PORT`         | —    | 25         | 25/465/587                          |
| `SMTP_USERNAME`     | —    | —          | SMTP auth user                      |
| `SMTP_PASSWORD`     | —    | —          | SMTP auth pass                      |
| `SMTP_FROM`         | —    | —          | Sender address                      |
| `SMTP_TO`           | —    | —          | Comma‑separated recipients          |
| `OUTPUT_DIR`        | —    | `./output` | Local workspace + logs              |
| `BATCH_SIZE`        | —    | `1000`     | Call records per API call           |
| `MAX_RETRIES`       | —    | `3`        | Retry attempts                      |
| `RETRY_DELAY`       | —    | `5`        | Seconds between retries             |
| `DATE_OFFSET_DAYS`  | —    | `1`        | 0 = today, 1 = yesterday, etc.      |
| `LOG_LEVEL`         | —    | `INFO`     | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## 5 · Manual Execution

```bash
cd /opt/odin
source venv/bin/activate

# Standard run (yesterday’s calls)
python run_daily_call_report.py

# Custom date range: export two days ago
DATE_OFFSET_DAYS=2 python run_daily_call_report.py

# Debug with alternate env file
python run_daily_call_report.py -c /etc/odin/staging.env --debug
```

Exit 0 = success, Exit 1 = failure (useful for CI or health checks).

---

## 6 · Scheduling with Cron

```cron
# America/New_York timezone
CRON_TZ=America/New_York

# Daily call report at 02:30 local time
30 2 * * * /usr/bin/env bash -c 'cd /opt/odin && source venv/bin/activate && ./run_daily_call_report.py >> /var/log/odin/calls.log 2>&1'
```

*The script automatically fetches the previous day’s calls, so running just after midnight works nicely.*

---

## 7 · Logging

* **Stdout / Stderr**: collected by cron and appended to the logfile path specified.
* **Rotating log file**: `OUTPUT_DIR/daily_call_report.log` (one per day, handled by `daily_odin_report.py`).

---

## 8 · Troubleshooting

| Symptom             | Likely Cause                    | Action                                           |
| ------------------- | ------------------------------- | ------------------------------------------------ |
| No CSV on SFTP      | Wrong `SFTP_*` vars or firewall | Verify with CLI `sftp`; check IP allow‑list      |
| Email arrives empty | `SMTP_TO` missing               | Add recipients                                   |
| API auth failure    | Bad `ODIN_API_*` creds          | Re‑enter creds; test with `curl`                 |
| Cron exit 1         | venv not activated              | Use full venv path or `source venv/bin/activate` |

---

## 9 · Updating Scripts

```bash
cd /opt/odin
cp /new/run_daily_call_report.py .
cp /new/daily_odin_report.py .
source venv/bin/activate
pip install --upgrade -r requirements.txt   # only if deps changed
```

Cron and `.env` stay valid unless new vars appear.

---

## 10 · Security & Compliance

* Principle of least privilege for SFTP/SMTP accounts.
* Secrets management (Vault, AWS SM, etc.) instead of flat `.env`, in production.
* CDRs are potentially sensitive PII. Follow company data‑retention and encryption policies.

---

### You’re Good to Go!

With the wrapper deployed, configured, and scheduled, a fresh, fully‑automated Daily Call Report will reach your SFTP server **and** your mailbox every morning—hands‑free.
