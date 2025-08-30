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
* Deploy the scripts into `./odin-reports`.

---

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
   chmod +x run_user_report.py
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

### 4. Command‑Line Usage
Run report: `python run_user_report.py` \
No flag = all SPs \
Flag { -s <SP_ID_1> <SP_ID_2> => hand picked list of Service Provider(s)

| Scenario                   | Command                                               |
| -------------------------- | ----------------------------------------------------- |
| All SPs *(default)*        | `python run_user_report.py`                           |
| Two specific SPs           | `python run_user_report.py -s acme contoso`           |
| Alternate env file + debug | `python run_user_report.py -c /path/prod.env --debug` |

### 8. **Deployment for one or more SPs**

   ```bash
   source myvenv/bin/activate

   # Run User Report for Service Providers ‘acme’ ‘contoso’
   python run_user_report.py -s acme contoso
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

# Appendix

## Troubleshooting Quick‑Ref

| Symptom                              | Cause                              | Fix                                                      |
| ------------------------------------ | ---------------------------------- | -------------------------------------------------------- |
| CSVs present locally, absent on SFTP | Bad `SFTP_*` variables or firewall | Validate creds; test with CLI `sftp`                     |
| Email sent, but no attachments       | `SMTP_*` ok but `SMTP_TO` empty    | Provide at least one recipient                           |
| `Authentication failed` messages     | Wrong `ODIN_API_*` credentials     | Re‑enter creds; verify API URL                           |
| Cron exits with status 1             | Virtualenv not sourced             | Use full venv path or `source venv/bin/activate` in cron |

---

### All set!

Your scheduled jobs will now generate user reports—either global or limited to specific Service Providers—and deliver them automatically each cycle.


