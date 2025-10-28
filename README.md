# 🚀 AWS Cost Optimizer

[![Demo Video](https://cdn.loom.com/sessions/thumbnails/9c91b2ece17847f38ba97f427bc2cf9f-with-play.gif)](https://www.loom.com/share/9c91b2ece17847f38ba97f427bc2cf9f)

A **serverless DevOps automation tool** that detects and remediates idle AWS EC2 instances to cut unnecessary cloud spend.  
Built to demonstrate **real-world cost optimization**, **Infrastructure as Code (IaC)**, and **CI/CD automation** — from Python prototype to production-ready cloud deployment.

---

## 💡 Overview

Cloud costs often skyrocket from forgotten dev environments and idle resources.  
**AWS Cost Optimizer** automatically:

- Analyzes EC2 CPU metrics via CloudWatch.
- Calculates last-30-day spend via Cost Explorer.
- Flags under-utilized instances (CPU < 5% for 72h).
- Optionally stops them (with a safe `DRY_RUN` toggle).
- Sends daily cost summary emails via SNS.
- Deploys fully automated using **Terraform** and **GitHub Actions**.

> “Built to prove I can design, automate, and deploy a full DevOps pipeline — combining cost efficiency, observability, and automation.”

---

## ⚙️ Key Features

| Category | Description |
|-----------|--------------|
| 💰 **Idle Detection** | Uses Boto3 + CloudWatch to find EC2s with < 5% average CPU utilization over 72 hours. |
| 🔧 **Remediation** | Optionally stops idle instances (dry-run or live mode). |
| 📊 **Dashboard** | Streamlit UI for visual metrics, charts, and simulated savings. |
| ⏰ **Automation** | EventBridge cron triggers Lambda daily at 2 AM UTC. |
| 📬 **Alerts** | SNS emails include cost summary, idle count, and Lambda log link. |
| ☁️ **Infrastructure as Code** | Terraform backend stored in encrypted S3 for reproducible deployments. |
| 🔄 **CI/CD Pipeline** | GitHub Actions builds, zips, and deploys Lambda automatically on push. |
| 🔒 **Security First** | Uses least-privilege IAM and encrypted backend state. |

---

## 🧱 Architecture

### **Event Flow**
`EventBridge → Lambda (scan + remediate + alert) → SNS Email → Dashboard UI`

┌────────────┐ ┌──────────────┐ ┌────────┐
│ Schedule │──▶─▶│ Lambda Scan │──▶─▶│ SNS │
│ (2 AM UTC) │ │ + Cost Eval │ │ Email │
└────────────┘ └──────────────┘ └────────┘
│
▼

**Core Stack:**  
Python 3.10 · Boto3 · Terraform 1.9+ · AWS Lambda · EventBridge · SNS · GitHub Actions · Streamlit

---

## 🧠 Why It Matters

- **Cost Awareness:** Demonstrates measurable ROI — even a single idle t2.micro = ~$0.30/month saved.
- **DevOps Showcase:** End-to-end automation with monitoring, alerts, and CI/CD.
- **Scalable Blueprint:** Extend to EBS, RDS, or multi-account setups for real enterprise savings.

**Test Run Example:**  
1 idle t2.micro → 100% detected → ~$0.30/month saved (dry-run mode) → scalable to 25–40% total cost reduction.

---

## 🧩 Local Quick Start

```bash
# 1. Clone and install
git clone https://github.com/amara200169/aws-cost-optimizer.git
cd aws-cost-optimizer
pip install boto3 streamlit

# 2. Configure AWS
aws configure  # enter your keys and region (us-east-2)

# 3. Run scanner manually
python scanner.py
# → Output: "Total spend: $2.07 | Idle: i-013... | DRY_RUN: Would stop..."

# 4. Launch Streamlit dashboard
streamlit run dashboard.py
# → Opens http://localhost:8501

🧑‍💻 About the Developer

Built by Amara Sheriff — DevOps Engineer passionate about automation, cloud efficiency, and CI/CD excellence.
This project showcases my ability to design, automate, and deploy scalable systems end-to-end using AWS, Terraform, and GitHub Actions.

📫 Connect on LinkedIn linkedin.com/in/amara-sheriff-989016389
 or open an issue.
💼 Actively seeking DevOps / Cloud Engineering roles.