# AWS Cost Optimizer

[![Deploy Cost Optimizer](https://github.com/amara200169/aws-cost-optimizer/actions/workflows/deploy.yml/badge.svg)](https://github.com/amara200169/aws-cost-optimizer/actions/workflows/deploy.yml)
[![Demo Video](https://cdn.loom.com/sessions/thumbnails/9c91b2ece17847f38ba97f427bc2cf9f-with-play.gif)](https://www.loom.com/share/9c91b2ece17847f38ba97f427bc2cf9f)

A **serverless DevOps automation tool** that detects and remediates idle AWS EC2 instances to cut unnecessary cloud spend. Built to demonstrate real-world cost optimization, Infrastructure as Code, and CI/CD automation — from Python prototype to production-ready cloud deployment.

---

## Overview

Cloud costs skyrocket from forgotten dev environments and idle resources. **AWS Cost Optimizer** automatically:

- Scans all running EC2 instances and checks average CPU via CloudWatch (fully paginated)
- Flags under-utilized instances (CPU < 5% over 72 hours)
- Calculates last-30-day total spend via Cost Explorer
- Optionally stops idle instances with a safe `DRY_RUN` toggle
- Sends daily cost summary alerts via SNS email
- Routes Lambda failures to an SQS dead-letter queue
- Deploys fully automated with Terraform and GitHub Actions

---

## Key Features

| Category | Description |
|----------|-------------|
| **Idle Detection** | Paginated CloudWatch scan — finds every running instance regardless of account size |
| **Accurate Cost Estimates** | Per-instance-type pricing lookup (t2, t3, m5, c5, r5 families) |
| **Safe Remediation** | `DRY_RUN=true` by default; live mode requires explicit opt-in |
| **Streamlit Dashboard** | Visual metrics table with avg CPU %, estimated savings, and one-click dry-run simulation |
| **SNS Alerts** | Lambda publishes a cost report email after every scan |
| **Failure Handling** | SQS dead-letter queue captures silent Lambda failures for investigation |
| **Observability** | CloudWatch log group (30-day retention) + error-rate alarm that emails on failure |
| **Infrastructure as Code** | Terraform with encrypted S3 backend and DynamoDB state locking |
| **CI/CD Pipeline** | GitHub Actions runs tests on every PR and deploys on merge to `main` |
| **Least-Privilege IAM** | Scoped IAM policy — EC2, CloudWatch, Cost Explorer, SNS, SQS only |

---

## Architecture

```
EventBridge (2 AM UTC)
        │
        ▼
  Lambda Function  ──────────────────────► SQS Dead-Letter Queue (on failure)
  ┌─────────────────────────┐
  │  scanner.py             │
  │  • describe_instances() │──── CloudWatch (CPU metrics)
  │  • get_cost_summary()   │──── Cost Explorer
  │  • auto_remediate()     │──── EC2 stop_instances()
  └─────────────────────────┘
        │
        ▼
    SNS Topic ──► Email Alert
                  └──► CloudWatch Alarm (on Lambda errors)

  Streamlit Dashboard (local)
  └── scanner.py (cached, read-only)
```

**Core Stack:** Python 3.12 · Boto3 · Terraform 1.9+ · AWS Lambda · EventBridge · SNS · SQS · GitHub Actions · Streamlit

---

## Project Structure

```
aws-cost-optimizer/
├── scanner.py                        # Local CLI scanner (used by dashboard)
├── dashboard.py                      # Streamlit UI
├── requirements.txt                  # Runtime dependencies
├── requirements-dev.txt              # Test dependencies
├── main.tf                           # Terraform — all AWS resources
├── variables.tf                      # Terraform input variables
├── tests/
│   └── test_scanner.py               # Unit tests (pytest + mocks)
└── lambda_src/
    ├── scanner.py                    # Lambda-bundled scanner
    └── lambda_handler.py             # Lambda entry point
```

---

## Local Quick Start

```bash
# 1. Clone and install
git clone https://github.com/amara200169/aws-cost-optimizer.git
cd aws-cost-optimizer
pip install -r requirements.txt

# 2. Configure AWS credentials
aws configure  # region: us-east-2

# 3. Run the scanner (dry run by default)
python scanner.py

# 4. Run with live remediation
python scanner.py --remediate

# 5. Launch the Streamlit dashboard
streamlit run dashboard.py
# → Opens http://localhost:8501
```

---

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Tests cover `get_idle_instances`, `get_cost_summary`, `_estimate_monthly_cost`, and `auto_remediate` using mocks — no real AWS calls required.

---

## Terraform Deployment

### Prerequisites

**1. Create the DynamoDB table for state locking (one-time setup):**

```bash
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-2
```

**2. Add these secrets to your GitHub repository** (`Settings → Secrets → Actions`):

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | IAM user access key with deploy permissions |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key |
| `ALERT_EMAIL` | Email address to receive SNS cost alerts |

### Deploy manually

```bash
terraform init
terraform plan -var="alert_email=you@example.com"
terraform apply -var="alert_email=you@example.com"
```

### Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | `us-east-2` | AWS region for all resources |
| `alert_email` | *(required)* | Email address for SNS cost alert notifications |
| `dry_run` | `true` | Set to `false` to enable live instance stopping |
| `idle_cpu_threshold_days` | `3` | Days of CPU data to evaluate for idle detection |
| `lambda_timeout` | `300` | Lambda timeout in seconds |
| `lambda_memory` | `256` | Lambda memory in MB |
| `log_retention_days` | `30` | CloudWatch log retention in days |

---

## How It Works

1. **EventBridge** triggers the Lambda daily at 2:00 AM UTC
2. Lambda calls `get_idle_instances()` — paginates all running EC2s and checks CloudWatch CPU metrics
3. Any instance averaging < 5% CPU over 72 hours is flagged as idle
4. If `DRY_RUN=false`, idle instances are stopped via `ec2:StopInstances`
5. A cost report is published to SNS — subscribers receive an email with 30-day spend, idle count, and per-instance savings
6. If the Lambda itself fails, the invocation is routed to an SQS dead-letter queue and a CloudWatch alarm fires an alert email

---

## CI/CD Pipeline

Every push triggers the GitHub Actions workflow:

- **On pull requests:** installs dependencies, runs the full test suite
- **On merge to `main`:** runs tests → `terraform init` → `terraform plan` → `terraform apply`

The Lambda deployment is fully managed by Terraform via `source_code_hash` — no manual zip/upload step required.

---

## Why It Matters

- **Measurable ROI** — a single idle `t3.medium` wastes ~$30/month; at scale, savings compound quickly
- **End-to-end DevOps** — observability, automation, alerting, IaC, CI/CD, and testing in one project
- **Scalable Blueprint** — extend to EBS snapshots, RDS idle detection, or multi-account with AWS Organizations

---

## About the Developer

Built by **Amara Sheriff** — DevOps Engineer focused on cloud automation, cost efficiency, and CI/CD excellence.

- LinkedIn: [linkedin.com/in/amara-sheriff-989016389](https://linkedin.com/in/amara-sheriff-989016389)
- GitHub Issues: open one on this repo
- Actively seeking DevOps / Cloud Engineering roles
