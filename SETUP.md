# 🛠️ Setup & Reproduction Guide

Complete instructions for reproducing the Travel Intelligence Platform from scratch.

**Estimated setup time:** 60-90 minutes (mostly AWS provisioning + data upload time).

---

## 📋 Prerequisites

Before starting, you must have:

- **AWS account** with admin or IAM user access (Free Tier eligible is sufficient)
- **Python 3.10 or higher** installed locally
- **Git** installed
- **AWS CLI v2** installed and configured
- **Kaggle account** (for the historical dataset download)
- **Aviationstack account** (free tier — for live data ingestion)

---

## 1️⃣ Local Environment Setup

```bash
# Clone the repository
git clone https://github.com/AkshatDhiman07/Airline-Intelligence.git
cd Airline-Intelligence

# Create and activate Python virtual environment
python -m venv venv
source venv/Scripts/activate    # Windows (Git Bash)
# OR
source venv/bin/activate         # macOS / Linux

# Install all dependencies
pip install -r requirements.txt
```

---

## 2️⃣ AWS Account Setup

### 2.1 Create an IAM User (do NOT use root)

In the AWS Console:
1. Go to **IAM → Users → Create user**
2. Username: `husky-user-1` (or any name)
3. Attach these managed policies:
   - `AmazonS3FullAccess`
   - `AmazonAthenaFullAccess`
   - `AWSLambda_FullAccess`
   - `AmazonEventBridgeFullAccess`
   - `SecretsManagerReadWrite`
   - `CloudWatchLogsFullAccess`
   - `AWSGlueConsoleFullAccess`
4. Create access key under **Security credentials → Create access key → CLI**
5. **Save** the Access Key ID and Secret Access Key

### 2.2 Configure AWS CLI

```bash
aws configure
# Enter when prompted:
# AWS Access Key ID:     [Will be provided to verified users]
# AWS Secret Access Key: [Will be provided to verified users]
# Default region:        us-east-1
# Default output format: json

# Verify
aws sts get-caller-identity
```

### 2.3 Create S3 Buckets

```bash
# Set your account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create the three buckets
aws s3 mb s3://airline-raw-flight-data --region us-east-1
aws s3 mb s3://airline-processed-flight-data --region us-east-1
aws s3 mb s3://airline-athena-results-${ACCOUNT_ID} --region us-east-1

# Verify
aws s3 ls
```

> ⚠️ S3 bucket names are globally unique. If `airline-raw-flight-data` or `airline-processed-flight-data` is already taken, append your initials (e.g., `airline-raw-flight-data-akshat`) and update all references in the code.

---

## 3️⃣ Load Historical Data (Kaggle BTS)

### 3.1 Get Kaggle API Token

1. Sign in at https://www.kaggle.com
2. Go to **Settings → API → Create New Token**
3. Save the downloaded `kaggle.json` somewhere safe

### 3.2 Download and Upload via AWS CloudShell

Open **AWS CloudShell** in the AWS Console (terminal icon in top nav bar):

```bash
# Install Kaggle CLI
pip install kaggle

# Set up Kaggle credentials (replace with YOUR token)
mkdir -p ~/.kaggle
echo "PASTE_YOUR_KAGGLE_TOKEN_HERE" > ~/.kaggle/access_token
chmod 600 ~/.kaggle/access_token

# Download the dataset
cd /tmp
kaggle datasets download -d patrickzel/flight-delay-and-cancellation-dataset-2019-2023
unzip -o flight-delay-and-cancellation-dataset-2019-2023.zip

# Split by year (Hive partitioning)
mkdir -p /tmp/by_year
HEADER=$(head -1 flights_sample_3m.csv)
tail -n +2 flights_sample_3m.csv | awk -F',' -v hdr="$HEADER" '
{
  year = substr($1, 1, 4)
  outfile = "/tmp/by_year/flights_" year ".csv"
  if (!(year in seen)) {
    print hdr > outfile
    seen[year] = 1
  }
  print >> outfile
}'

# Upload to S3 with year partitioning
RAW_BUCKET=airline-raw-flight-data
for f in /tmp/by_year/flights_*.csv; do
  year=$(basename "$f" .csv | sed 's/flights_//')
  aws s3 cp "$f" "s3://${RAW_BUCKET}/bts/flights/year=${year}/flights.csv"
done

# Upload lookup tables (also from a Kaggle dataset)
kaggle datasets download -d usdot/flight-delays
unzip -o flight-delays.zip airlines.csv airports.csv
aws s3 cp airlines.csv s3://${RAW_BUCKET}/bts/airlines/airlines.csv
aws s3 cp airports.csv s3://${RAW_BUCKET}/bts/airports/airports.csv
```

Verify with:
```bash
aws s3 ls s3://airline-raw-flight-data/bts/ --recursive --human-readable --summarize
```

---

## 4️⃣ Set Up Live Data Ingestion (Aviationstack)

### 4.1 Get an Aviationstack API Key

1. Sign up at https://aviationstack.com/signup/free
2. Verify email
3. Copy your API access key from the dashboard

### 4.2 Store the Key in AWS Secrets Manager

AWS Console → **Secrets Manager → Store a new secret**:
- Secret type: **Other type of secret**
- Key/value pair: Key=`AVIATIONSTACK_KEY`, Value=`[your key]`
- Secret name: `travel-intel/aviationstack`
- Save (rotation disabled)

### 4.3 Create the Lambda Function

AWS Console → **Lambda → Create function**:
- Name: `travel-intel-aviationstack-ingestion`
- Runtime: **Python 3.12**
- Memory: 512 MB
- Timeout: 60 sec
- Permissions: Allow S3 PutObject + Secrets Manager GetSecretValue + CloudWatch Logs

Paste the code from `ingestion/aviationstack_lambda.py` into the Lambda code editor.

Set environment variables:
| Key | Value |
|---|---|
| `RAW_BUCKET` | `airline-raw-flight-data` |
| `SECRET_NAME` | `travel-intel/aviationstack` |
| `API_LIMIT` | `100` |

Click **Deploy**, then **Test** with empty `{}` event to verify a successful ingestion.

### 4.4 Create EventBridge Schedule

AWS Console → **EventBridge → Schedules → Create schedule**:
- Name: `travel-intel-flight-ingestion-12h`
- Type: Recurring, cron-based
- Cron expression: `0 0,12 * * ? *`
- Target: Lambda → `travel-intel-aviationstack-ingestion`
- Payload: `{}`
- Save (let AWS auto-create the execution role)

### 4.5 Set CloudWatch Log Retention

AWS Console → **CloudWatch → Log groups → /aws/lambda/travel-intel-aviationstack-ingestion**:
- Actions → Edit retention setting → **1 week**

---

## 5️⃣ Set Up Athena Database

### 5.1 Configure Athena Query Results Location

AWS Console → **Athena → Settings → Manage**:
- Query result location: `s3://airline-athena-results-{your-account-id}/`
- Save

### 5.2 Run the SQL DDL

In Athena Query Editor, open `analytics/athena_queries.sql` from this repo and run each statement **one at a time** in this order:

1. `CREATE DATABASE travel_intel`
2. Switch the Database dropdown to `travel_intel`
3. `CREATE EXTERNAL TABLE flights` (with `use.null.for.invalid.data = 'true'` property)
4. `MSCK REPAIR TABLE flights` (registers 5 year partitions)
5. `CREATE OR REPLACE VIEW flights_clean`
6. `CREATE OR REPLACE VIEW route_performance`
7. `CREATE OR REPLACE VIEW airline_performance`
8. `CREATE OR REPLACE VIEW hourly_patterns`
9. `CREATE OR REPLACE VIEW covid_impact`

### 5.3 Verify

```sql
SELECT year, COUNT(*) AS total_flights
FROM travel_intel.flights
GROUP BY year
ORDER BY year;
```

Expected: 5 rows totaling 3,000,000 records.

---

## 6️⃣ Train the ML Model

```bash
# Make sure venv is active locally
source venv/Scripts/activate

# Run training
python ml/train_model.py
```

Expected output:
- Fetches 300,000 rows from Athena (~30 sec)
- Trains Random Forest (~3 sec)
- Reports AUC-ROC around 0.66-0.68
- Uploads model artifacts to `s3://airline-processed-flight-data/ml-models/`

---

## 7️⃣ Run the Dashboard

```bash
python -m streamlit run dashboard/streamlit_app.py
```

The dashboard opens automatically at `http://localhost:8501`.

First load takes 30-60 seconds while Athena queries populate. After that, queries are cached for 1 hour.

You should see:
- 4 KPI tiles at top
- 6 tabs: Hourly Patterns, Route Analysis, Airlines, COVID Impact, Delay Predictor, Live Pulse
- Live ML inference on the Delay Predictor tab

---

## 8️⃣ Optional — Test the API Stub

```bash
python api/handler.py
```

Runs a local prediction using the saved model. Useful for testing the deployable Lambda handler.

---

## 🛑 Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| `NoCredentialsError` | AWS CLI not configured | Run `aws configure` |
| `AccessDeniedException` (Athena) | IAM user missing Athena policy | Add `AmazonAthenaFullAccess` |
| `ModuleNotFoundError: plotly` | Plotly not installed | `pip install plotly` |
| `BAD_DATA error on dep_delay` | Empty string in CSV | Add `'use.null.for.invalid.data' = 'true'` to table |
| `usage_limit_reached` (Aviationstack) | Exhausted 100 free calls/month | Wait until next month |
| `bash: streamlit: command not found` | Streamlit not on PATH | Use `python -m streamlit run ...` |

---

## 💰 Expected Costs

| Service | Monthly | Reason |
|---|---|---|
| S3 storage | $0.00 | Free Tier covers 5GB |
| Lambda | $0.00 | Free Tier covers 1M requests |
| EventBridge | $0.00 | Free Tier |
| CloudWatch Logs | $0.00 | Free Tier (7-day retention) |
| **Secrets Manager** | **$0.40** | No free tier |
| Athena | ~$0.01 per dashboard load | $5 per TB scanned |
| **TOTAL** | **~$0.40-$0.50/month** | |

**Set a billing alarm at $5** to catch surprises.

---

## 📂 Repository File Reference

| File | Purpose |
|---|---|
| `ingestion/aviationstack_lambda.py` | Live API ingestion Lambda (deployed to AWS) |
| `analytics/athena_queries.sql` | All Athena DDL + analytics queries |
| `ml/train_model.py` | Random Forest training script |
| `ml/model_metrics.json` | Saved evaluation metrics |
| `dashboard/streamlit_app.py` | 6-tab interactive dashboard |
| `api/handler.py` | Lambda inference handler (stub, runs locally) |
| `docs/BUSINESS_CASE.md` | B2B monetization strategy |
| `infra/architecture.md` | Full AWS resource inventory |
| `requirements.txt` | Python dependencies |

---

## ✅ Verification Checklist

After complete setup, you should be able to:

- [ ] Run `aws s3 ls s3://airline-raw-flight-data/bts/` and see year partitions
- [ ] Query `SELECT COUNT(*) FROM travel_intel.flights` in Athena → returns 3,000,000
- [ ] See your Lambda firing every 12 hours in CloudWatch Logs
- [ ] Open `localhost:8501` and see all 6 tabs working
- [ ] Click "Predict" on the ML tab and get a delay probability back

If all of the above work, your reproduction is complete.

---

*Questions? Open an issue on GitHub or contact the authors via LinkedIn (links in main README).*
