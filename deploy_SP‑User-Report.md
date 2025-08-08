# Deploying the Select / All‑SP User Report Automation

This guide accompanies **run\_user\_report.py**, a flexible wrapper around `daily_odin_report.py` that can export

* **All Service Providers** (default) – equivalent to the global user export.
* **One or more explicit Service Providers** – pass their IDs with `-s` or `--service-providers`.

The wrapper then delivers the resulting CSVs via SFTP and/or e‑mail.

---

## 1. Key Capabilities

| Capability         | Details                                                                                           |
| ------------------ | ------------------------------------------------------------------------------------------------- |
| **Mode selection** | No flag = *all* SPs; `-s spA spB spC` = hand‑picked list                                          |
| **Data pipeline**  | Odin API → pandas → CSV(s)                                                                        |
| **Delivery**       | Uploads to SFTP (if `SFTP_*` variables set) and/or emails attachments (if `SMTP_*` variables set) |
| **Resilience**     | Network retries, credential validation, and comprehensive logging out‑of‑the‑box                  |

---

## 2. Installation Overview

These instructions will:
* Clone the `parkbenchsolutions-odin-reports` repository from GitHub.
* Deploy the scripts into `/opt/odin`.

---

### 1. **Clone the repository**

   ```bash
   git clone https://github.com/parkbenchsolutions/odin-reports.git ~/odin-reports
   ```

### 2. **Create deployment directory and copy scripts**

   ```bash
   sudo mkdir -p /opt/odin
   sudo chown $USER /opt/odin
   cp ~/odin-reports/deploy_SP-User-Report.md ~/odin-reports/run_user_report.py ~/odin-reports/daily_odin_report.py /opt/odin/
   ```

### 3. **Enter the deployment directory**

   ```bash
   cd /opt/odin
   ```

### 4. **Set up a Python virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

### 5. **Install required Python packages**

   ```bash
   pip install pandas requests paramiko python-dateutil
   ```

### 6. **Make the wrapper executable**

   ```bash
   chmod +x run_user_report.py
   ```

### 7. **Create your **\`\`** file with the necessary environment variables**

   ```bash
   cat > .env <<EOF
   # Odin API (required)
   ODIN_API_BASE_URL=https://bw-odin.example.com
   ODIN_API_USERNAME=bw-api-svc
   ODIN_API_PASSWORD=SuperSecret!

   # SFTP (optional)
   SFTP_HOST=sftp.reporting.example.com
   SFTP_PORT=22
   SFTP_USERNAME=odin-report
   SFTP_PASSWORD=AnotherSecret
   SFTP_REMOTE_PATH=/incoming/odin/users

   # SMTP (optional)
   SMTP_HOST=smtp.office365.com
   SMTP_PORT=587
   SMTP_USERNAME=reports@yourco.com
   SMTP_PASSWORD=EmailSecret
   SMTP_FROM=reports@yourco.com
   SMTP_TO=ops@yourco.com,noc@yourco.com

   # Misc
   OUTPUT_DIR=/var/tmp/odin-user-reports
   BATCH_SIZE=500
   MAX_RETRIES=3
   RETRY_DELAY=5
   INCLUDE_OPTIONAL_FIELDS=true
   LOG_LEVEL=INFO
   EOF
   ```

### 8. **Edit the **\`\`** file to customize your settings**

   ```bash
   nano .env
   ```

### 9. **Test the deployment for one or more SPs**

   ```bash
   source venv/bin/activate

   # Run report: ./run_user_report.py
   # No flag = all SPs
   # Flag { -s <SP_ID_1> <SP_ID_2> => hand picked list of Service Provider(s)

   # Run User Report for Service Providers ‘acme’ ‘contoso’
   ./run_user_report.py -s acme contoso
   ```

### 10. **Optional: Schedule a Cron job**

    ```bash
    crontab -e
    ```

### 11. **Add the Cron entry - Examples**
    In the editor, add the following to schedule a nightly run at 02:20 AM Eastern:

    ```cron
    # America/New_York timezone for clarity
    CRON_TZ=America/New_York

    # 1) Nightly export across *all* SPs (02:20)
    20 2 * * * /usr/bin/env bash -c 'cd /opt/odin && source venv/bin/activate && ./run_user_report.py >> /var/log/odin/users_all.log 2>&1'

    # 2) Weekly export for ACME & CONTOSO every Monday (03:05)
    5 3 * * 1 /usr/bin/env bash -c 'cd /opt/odin && source venv/bin/activate && ./run_user_report.py -s acme contoso >> /var/log/odin/users_acme_contoso.log 2>&1'
    ```

---

## 3. Configuration via .env

Create `/opt/odin/.env` (or point to another file with `-c`). Only Odin API creds are mandatory; SFTP/SMTP are optional.

```dotenv
# Odin API
ODIN_API_BASE_URL=https://bw-odin.example.com
ODIN_API_USERNAME=bw-api-svc
ODIN_API_PASSWORD=SuperSecret!

# SFTP (optional)
SFTP_HOST=sftp.reporting.example.com
SFTP_PORT=22
SFTP_USERNAME=odin-report
SFTP_PASSWORD=AnotherSecret
SFTP_REMOTE_PATH=/incoming/odin/users

# SMTP (optional)
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=reports@yourco.com
SMTP_PASSWORD=EmailSecret
SMTP_FROM=reports@yourco.com
SMTP_TO=ops@yourco.com, noc@yourco.com

# Misc
OUTPUT_DIR=/var/tmp/odin-user-reports
BATCH_SIZE=500
MAX_RETRIES=3
RETRY_DELAY=5
INCLUDE_OPTIONAL_FIELDS=true
LOG_LEVEL=INFO
```

---

## 4. Command‑Line Usage

| Scenario                   | Command                                               |
| -------------------------- | ----------------------------------------------------- |
| All SPs *(default)*        | `python run_user_report.py`                           |
| Two specific SPs           | `python run_user_report.py -s acme contoso`           |
| Alternate env file + debug | `python run_user_report.py -c /path/prod.env --debug` |

Exit status `0` = success; `1` = failure.

---

## 5. Cron Scheduling Examples

```cron
# America/New_York timezone for clarity
CRON_TZ=America/New_York

# 1) Nightly export across *all* SPs (02:20)
20 2 * * * /usr/bin/env bash -c 'cd /opt/odin && source venv/bin/activate && ./run_user_report.py >> /var/log/odin/users_all.log 2>&1'

# 2) Weekly export for ACME & CONTOSO every Monday (03:05)
5 3 * * 1 /usr/bin/env bash -c 'cd /opt/odin && source venv/bin/activate && ./run_user_report.py -s acme contoso >> /var/log/odin/users_acme_contoso.log 2>&1'
```

---

## 6. Troubleshooting Quick‑Ref

| Symptom                              | Cause                              | Fix                                                      |
| ------------------------------------ | ---------------------------------- | -------------------------------------------------------- |
| CSVs present locally, absent on SFTP | Bad `SFTP_*` variables or firewall | Validate creds; test with CLI `sftp`                     |
| Email sent, but no attachments       | `SMTP_*` ok but `SMTP_TO` empty    | Provide at least one recipient                           |
| `Authentication failed` messages     | Wrong `ODIN_API_*` credentials     | Re‑enter creds; verify API URL                           |
| Cron exits with status 1             | Virtualenv not sourced             | Use full venv path or `source venv/bin/activate` in cron |

---

## 7. Updating

```bash
cd /opt/odin
cp /new/run_user_report.py .
cp /new/daily_odin_report.py .
source venv/bin/activate
pip install --upgrade -r requirements.txt   # if needed
```

No change to cron or `.env` required unless new variables are introduced.

---

## 8. Security Notes

* Store `.env` outside version control; restrict file permissions (`chmod 600`).
* Consider a secrets manager for production deployments.
* CSVs may contain PII—protect at rest and in transit.

---

### All set!

Your scheduled jobs will now generate user reports—either global or limited to specific Service Providers—and deliver them automatically each cycle.

