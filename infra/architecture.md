# 🏗️ Architecture & Infrastructure

> Detailed AWS resource inventory and design decisions for the Travel Intelligence Platform.

---

## 📐 High-Level Architecture
┌──────────────────────┐                  ┌──────────────────────┐
│   DATA SOURCES       │                  │   END USERS          │
│ ─────────────        │                  │ ─────────────        │
│ • Kaggle BTS         │                  │ • Streamlit dashboard│
│   (3M historical)    │                  │ • B2B API consumers  │
│ • Aviationstack API  │                  │ • Internal analysts  │
│   (live flights)     │                  │                      │
└──────────┬───────────┘                  └──────────▲───────────┘
│                                         │
▼                                         │
┌──────────────────────────────────────────────────────────────┐
│                      AWS CLOUD                               │
│                                                              │
│  ┌────────────────┐    ┌────────────────┐                    │
│  │  EventBridge   │───>│  Lambda        │                    │
│  │  cron(0 0,12   │    │  (ingestion)   │                    │
│  │   * * ? *)     │    └────────┬───────┘                    │
│  └────────────────┘             │                            │
│                                 ▼                            │
│  ┌────────────────────────────────────────┐                  │
│  │            S3 Data Lake                │                  │
│  │  ┌──────────────┐  ┌──────────────┐    │                  │
│  │  │ Raw (CSV)    │  │ Processed    │    │                  │
│  │  │ + Live(JSON) │  │ (ML models)  │    │                  │
│  │  └──────────────┘  └──────────────┘    │                  │
│  └──────────┬─────────────────────────────┘                  │
│             │                                                │
│             ▼                                                │
│  ┌────────────────────────────────────────┐                  │
│  │       Athena (Serverless SQL)          │                  │
│  │  Database: travel_intel                │                  │
│  │   ├─ flights (external table)          │                  │
│  │   ├─ flights_clean (view)              │                  │
│  │   ├─ route_performance (view)          │                  │
│  │   ├─ airline_performance (view)        │                  │
│  │   ├─ hourly_patterns (view)            │                  │
│  │   └─ covid_impact (view)               │                  │
│  └──────────┬─────────────────────────────┘                  │
│             │                                                │
│             ▼                                                │
│  ┌────────────────────────────────────────┐                  │
│  │   ML Model (Random Forest, AUC 0.67)   │                  │
│  │   Stored in S3, served via Streamlit   │                  │
│  └────────────────────────────────────────┘                  │
│                                                              │
│  ┌────────────────┐    ┌────────────────┐                    │
│  │ Secrets Mgr    │    │  CloudWatch    │                    │
│  │ (API key)      │    │  Logs (7-day)  │                    │
│  └────────────────┘    └────────────────┘                    │
└──────────────────────────────────────────────────────────────┘
---

## 📋 AWS Resource Inventory

### S3 Buckets (3 total)

| Bucket | Purpose | Size | Versioning |
|---|---|---|---|
| `airline-raw-flight-data` | Historical CSVs + live JSONs | ~590 MB | Enabled |
| `airline-processed-flight-data` | ML models, future Parquet | ~10 MB | Enabled |
| `airline-athena-results-{account}` | Athena query result cache | Auto-managed | 30-day lifecycle |

**Partitioning strategy:**
airline-raw-flight-data/
├── bts/
│   ├── flights/year=2019/flights.csv  (148.6 MB)
│   ├── flights/year=2020/flights.csv  (92.4 MB)
│   ├── flights/year=2021/flights.csv  (119.3 MB)
│   ├── flights/year=2022/flights.csv  (134.3 MB)
│   ├── flights/year=2023/flights.csv  (91.1 MB)
│   ├── airlines/airlines.csv
│   └── airports/airports.csv
└── aviationstack/
└── year=2026/month=05/day=DD/hour=HH/flights_*.json
### Lambda Functions

| Function | Runtime | Memory | Trigger | Purpose |
|---|---|---|---|---|
| `travel-intel-aviationstack-ingestion` | Python 3.12 | 512 MB | EventBridge (12h cron) | Fetch live flight data |

### EventBridge Schedules

| Schedule | Cron | Target | Status |
|---|---|---|---|
| `travel-intel-flight-ingestion-12h` | `0 0,12 * * ? *` | Lambda | Enabled |

### IAM

| Principal | Type | Permissions |
|---|---|---|
| `husky-user-1` | IAM User | Athena Full, S3 Full, Glue Console Full |
| `lambda-flight-ingestion-role` | IAM Role | S3 PutObject, Secrets GetSecretValue, CloudWatch Logs |
| EventBridge scheduler role | IAM Role (auto) | Lambda Invoke |

### Secrets Manager

| Secret | Stored | Encryption |
|---|---|---|
| `travel-intel/aviationstack` | API key | AWS-managed KMS |

### Athena

| Component | Detail |
|---|---|
| Database | `travel_intel` |
| Engine version | v3 |
| Result location | `s3://airline-athena-results-{account}/` |
| Tables | 1 external table (`flights`), 5 views |
| Partitioned by | `year` (5 partitions) |

### CloudWatch

| Log Group | Retention |
|---|---|
| `/aws/lambda/travel-intel-aviationstack-ingestion` | 7 days |

---

## 🔐 Security Posture

- ✅ No root user for daily work — using dedicated IAM user `husky-user-1`
- ✅ MFA enabled on root account
- ✅ All S3 buckets: encryption (SSE-S3), block public access, versioning
- ✅ API keys in Secrets Manager (not env vars, not in code)
- ✅ Lambda IAM role: least-privilege per service (S3 write to specific bucket, secret read to specific secret)
- ⚠️ IAM user uses `*FullAccess` policies — should be scoped to specific resources in production
- ⚠️ Aviationstack API uses HTTP (HTTPS requires paid tier)

---

## 💰 Cost Architecture

| Service | Monthly Cost | Free Tier? |
|---|---|---|
| S3 storage (~590 MB) | $0.00 | Yes (5 GB free) |
| Lambda (60 invocations) | $0.00 | Yes (1M free) |
| EventBridge (60 events) | $0.00 | Yes (14M free) |
| Secrets Manager (1 secret) | $0.40 | No |
| CloudWatch Logs (~60 KB) | $0.00 | Yes (5 GB free) |
| Athena (per dashboard load) | ~$0.01 | No, but $5/TB scanned |
| **Total (sustained)** | **~$0.40/mo** | |

**3-week MVP total spend: < $1.00**

---

## 🎯 Design Decisions

### Why S3 + Athena instead of RDS or Redshift?
- **Cost:** Athena scales to zero; RDS/Redshift have constant compute charges
- **Simplicity:** No database to provision, manage, or back up
- **Storage:** S3 is the most durable storage in AWS (11 9s); also the cheapest
- **Skill match:** SQL on S3 is genuinely the modern data engineering pattern

### Why Lambda instead of EC2 for ingestion?
- **Cost:** $0 on Free Tier vs $7+/mo for smallest EC2
- **Reliability:** AWS handles availability, retries
- **Resume signal:** Serverless is the modern pattern

### Why CSV instead of Parquet?
- **MVP speed:** Source data is CSV; conversion adds 2+ hours
- **Acknowledged trade-off:** 5x slower/costlier queries
- **Documented as Future Work**

### Why a separate IAM user instead of root?
- **Security best practice:** Root cannot have permissions limited
- **Compliance:** SOC 2, ISO 27001 forbid daily root use
- **Audit trail:** Per-user CloudTrail logs

---

## 🚀 Production Hardening Roadmap

Items not implemented in MVP but designed for v1.0:

1. **Infrastructure as Code:** Migrate from console-clicks to Terraform/CDK
2. **Parquet conversion:** Glue ETL job to materialize cleaned data
3. **CI/CD:** GitHub Actions for Lambda deployment + dbt-style SQL versioning
4. **Cross-region replication:** S3 buckets replicated to us-west-2
5. **IAM tightening:** Per-resource ARN scoping
6. **WAF + API Gateway throttling:** When the API layer launches
7. **Cost alarms:** CloudWatch billing alarms at $5, $10, $25
8. **Data quality checks:** Great Expectations or Soda for ingestion validation
