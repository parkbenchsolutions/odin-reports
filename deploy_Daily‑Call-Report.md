# Deploying the Daily Call‑Report Automation

This guide documents **run\_daily\_call\_report.py**, the thin wrapper around `daily_odin_report.py` that automatically delivers a **Daily Call Detail Record (CDR) report** for *all* Service Providers in your Rev.io Odin (BroadWorks) cluster.

---

## A) · What the Script Does

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

## B) · Prerequisites

| Requirement            | Notes                                                             |
| ---------------------- | ----------------------------------------------------------------- |
| Python ≥ 3.9           | CPython recommended                                               |
| `daily_odin_report.py` | Must reside in the *same* directory as `run_daily_call_report.py` |
| Libraries              | `pandas`, `requests`, `paramiko`, `python-dateutil`               |
| Network access         | Outbound to Odin API, SFTP host, and SMTP relay                   |

---

## C) · Installation Steps

### 1. **Clone the repository from desired deployment directory**

   ```bash
   git clone https://github.com/parkbenchsolutions/odin-reports.git
   ```

### 2. **Navigate to the Odin Reports deployment directory**

   ```bash
   sudo chown $USER ./odin-reports
   cd odin-reports
   ```

### 3. **Set up a Python virtual environment**

   ```bash
   sudo apt install python3-venv
   python3 -m venv myvenv
   source myvenv/bin/activate
   ```

### 4. **Install required Python packages**

   ```bash
   pip install -r requirements.txt
   ```

### 5. **Make the wrapper executable**

   ```bash
   chmod +x run_daily_call_report.py
   ```

### 6. **Create your **\`.env\`** file with the necessary environment variables**

   ```bash
   cat > .env <<EOF
   # Odin API (required)
   ODIN_API_BASE_URL=https://bw-odin.example.com
   ODIN_API_USERNAME=bw-api-svc
   ODIN_API_PASSWORD=SuperSecret!

   # SFTP (optional) - remove comment '#'
   #SFTP_HOST=sftp.reporting.example.com
   #SFTP_USERNAME=odin-report
   #SFTP_PASSWORD=AnotherSecret
   #SFTP_PORT=22
   #SFTP_REMOTE_PATH=/odin/reports

   # SMTP (optional) - remove comment '#'
   #SMTP_HOST="mail.smtp2go.com" 
   #SMTP_PORT=2525
   #SMTP_USERNAME=reports@yourco.com
   #SMTP_PASSWORD=EmailSecret
   #SMTP_FROM=reports@yourco.com
   #SMTP_TO=ops@yourco.com,noc@yourco.com

   # Misc
   OUTPUT_DIR=./reports
   BATCH_SIZE=500
   MAX_RETRIES=3
   RETRY_DELAY=5
   INCLUDE_OPTIONAL_FIELDS=true
   LOG_LEVEL=INFO
   EOF
   ```

### 7. **Edit the **\`\`** file to customize your settings**

   ```bash
   nano .env
   ```

---

### 7.1 Variable Reference

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
| `LOG_LEVEL`         | —    | `INFO`     | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### 7.2 CLI Parameters

| Flag           | Required | Default   | Description                                                                                                  |
| -------------- | -------- | --------- | ------------------------------------------------------------------------------------------------------------ |
| `--start-date` | —        | yesterday | Report window start. Accepts `YYYY-MM-DD` (expands to `00:00:00`) or `YYYY-MM-DD HH:MM:SS`. Requires `--end-date`. |
| `--end-date`   | —        | yesterday | Report window end. Accepts `YYYY-MM-DD` (expands to `23:59:59`) or `YYYY-MM-DD HH:MM:SS`. Requires `--start-date`. |
| `-c, --config` | —        | `.env`    | Path to a dotenv‑style config file.                                                                          |
| `-r, --report` | —        | `daily`   | Report type: `daily` (call records) or `users` (global user data).                                           |
| `-d, --debug`  | —        | off       | Enable verbose debug output.                                                                                 |

---

## D) · Manual Execution

```bash
cd ./odin-reports
source venv/bin/activate

# Standard run (yesterday's calls)
python run_daily_call_report.py

# Explicit date range (date-only; times auto-expand)
python run_daily_call_report.py --start-date 2026-01-26 --end-date 2026-01-27

# Explicit datetime range (full control)
python run_daily_call_report.py --start-date "2026-01-26 00:00:00" --end-date "2026-01-27 23:59:59"

# Debug with alternate env file and custom date range
python run_daily_call_report.py -c /etc/odin/staging.env --debug --start-date 2026-01-01 --end-date 2026-01-31
```

Exit 0 = success, Exit 1 = failure (useful for CI or health checks).

---

## E) · Scheduling with Cron

    ```cron
    # America/New_York timezone for clarity
    CRON_TZ=America/New_York

    # 1) Nightly export across *all* SPs (02:20)
    20 2 * * * /usr/bin/env bash -c 'cd /opt/odin && source venv/bin/activate && ./run_user_report.py >> /var/log/odin/users_all.log 2>&1'

    # 2) Weekly export for ACME & CONTOSO every Monday (03:05)
    5 3 * * 1 /usr/bin/env bash -c 'cd /opt/odin && source venv/bin/activate && ./run_user_report.py -s acme contoso >> /var/log/odin/users_acme_contoso.log 2>&1'
    ```

## F) · Logging

* **Stdout / Stderr**: collected by cron and appended to the logfile path specified.
* **Rotating log file**: `OUTPUT_DIR/daily_call_report.log` (one per day, handled by `daily_odin_report.py`).

---

## G) · Troubleshooting

| Symptom             | Likely Cause                    | Action                                           |
| ------------------- | ------------------------------- | ------------------------------------------------ |
| No CSV on SFTP      | Wrong `SFTP_*` vars or firewall | Verify with CLI `sftp`; check IP allow‑list      |
| Email arrives empty | `SMTP_TO` missing               | Add recipients                                   |
| API auth failure    | Bad `ODIN_API_*` creds          | Re‑enter creds; test with `curl`                 |
| Cron exit 1         | venv not activated              | Use full venv path or `source venv/bin/activate` |

---

## 10 · Security & Compliance

* Principle of least privilege for SFTP/SMTP accounts.
* Secrets management (Vault, AWS SM, etc.) instead of flat `.env`, in production.
* CDRs are potentially sensitive PII. Follow company data‑retention and encryption policies.

---

### You’re Good to Go!

With the wrapper deployed, configured, and scheduled, a fresh, fully‑automated Daily Call Report will reach your SFTP server **and** your mailbox every morning—hands‑free.
