# AI Financial Close Intelligence Agent

An end-to-end AI agent that analyzes a company's monthly financial close package — journal entries, trial balance, and account reconciliations — to automatically detect control risks, flag anomalies, and recommend remediation and automation opportunities. Output is delivered as a professional 6-tab executive report.

Built by Shuang Shi | April 2026

---

## What It Does

Big 4 advisory managers spend significant time each close cycle manually reviewing journal entries for anomalies, comparing trial balance movements, and checking reconciliation completeness. This agent automates that entire review workflow.

You upload an Excel close package. The agent:

1. Parses journal entries, trial balance, and reconciliation tracker from SAP
2. Detects JE anomalies — SOD violations, round numbers, off-hours postings, duplicates, unusual account pairings
3. Flags trial balance accounts with unusual period-over-period movements
4. Identifies reconciliation control failures — overdue accounts, aged items, missing approvals
5. Maps findings to control risk categories with evidence
6. Recommends immediate fixes, process redesigns, and automation opportunities
7. Delivers a professional 6-tab executive report in the browser

**Tested on:** APEX Insurance Co. mock close package (SAP, March 2025 monthly close)

---

## Project Structure

```
financial-close-agent/
├── app.py                  # Flask web app — main entry point
├── templates/
│   ├── index.html          # File upload page
│   └── report.html         # 6-tab executive report page
├── .env                    # API keys (not committed)
├── requirements.txt        # Python dependencies
└── README.md
```

---

## How to Run

### Prerequisites
- Python 3.9+
- An Anthropic API key (get one at console.anthropic.com)

### Setup

```bash
# Clone the repo
git clone https://github.com/shuang-shi/financial-close-agent.git
cd financial-close-agent

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configure API Key

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=your_api_key_here
```

### Run the App

```bash
python app.py
```

Open your browser and go to `http://localhost:5000`

Upload your Excel close package and click **Analyze Close Package**.

### Input File Format

The Excel file must contain 4 sheets:
- `Chart_of_Accounts` — SAP account codes and descriptions
- `Trial_Balance` — current and prior period balances with variance calculations
- `Journal_Entries` — SAP document-level JE log with preparer, approver, posting time
- `Reconciliation_Tracker` — balance sheet account reconciliation status and aging

### Cost

Each analysis costs approximately $0.50–$1.00 in Anthropic API credits depending on close package size.

---

## Key Product Decisions

### 1. Domain-specific anomaly detection over generic pattern matching
The agent detects insurance-specific control risks — SOD violations on reserve entries, round-number actuarial adjustments, off-hours investment reclassifications, reinsurance cut-off entries. These reflect how financial close controls actually work in a regulated insurance environment, not generic accounting patterns.

### 2. Evidence-based findings over conclusions only
Every finding references specific SAP document numbers, account codes, preparer names, posting times, and amounts. An auditor or CFO can trace every finding back to the source data. This mirrors Big 4 advisory methodology where conclusions without evidence are unacceptable.

### 3. Cross-dataset analysis over siloed review
The agent analyzes journal entries, trial balance, and reconciliations simultaneously and identifies connections across datasets. For example: a round-number JE posting to a reserve account, combined with an unsupported reconciliation on the same account, and a SOD violation — three separate findings that together indicate a potential material weakness. Siloed review would miss this pattern.

### 4. Actionable recommendations over findings only
Each control risk includes three levels of recommendation — immediate fix (what to do today), process redesign (how to change the workflow), and automation opportunity (which specific tool eliminates the risk). This mirrors how Big 4 advisory deliverables are structured and gives the CFO a clear path to resolution.

### 5. Professional report format over raw output
Output is structured as a 6-tab executive report with an introduction cover page, individual finding tabs, and a remediation section — exactly how a Big 4 close review deliverable would be presented to a CFO or audit committee.

---

## Pipeline Architecture

```
Excel Upload (.xlsx)
     │
     ▼
Pandas Parser ──► Chart of Accounts
              ──► Trial Balance (54 accounts)
              ──► Journal Entries (230+ entries)
              ──► Reconciliation Tracker (30 accounts)
     │
     ▼
Python Analysis Layer
  ├── JE anomaly pre-processing
  │     ├── Off-hours detection (before 7am / after 6pm)
  │     ├── SOD violation detection (preparer = approver)
  │     ├── Round number detection (multiples of $100,000)
  │     ├── Duplicate amount detection
  │     └── Large entry flagging (> $1M)
  ├── Trial balance variance calculation (> 10% threshold)
  └── Reconciliation status aggregation
     │
     ▼
Claude API (Anthropic) ──► 5-section close intelligence report
     │                       Section 1: JE Anomalies
     │                       Section 2: TB Variances
     │                       Section 3: Recon Control Risks
     │                       Section 4: Risk Summary & Priorities
     │                       Section 5: Remediation & Automation
     ▼
Flask + HTML ──► 6-tab executive report in browser
                 Tab 0: Introduction (cover page)
                 Tab 1: JE Anomalies
                 Tab 2: TB Variances
                 Tab 3: Recon Risks
                 Tab 4: Risk Summary
                 Tab 5: Recommendations
```

---

## Mock Data

A realistic mock close package for APEX Insurance Co. is available for testing. The dataset contains:

**Company:** APEX Insurance Co. | SAP Company Code: APEX01
**Period:** March 2025 (Monthly Close)
**ERP System:** SAP S/4HANA

**What's included:**
- 54 SAP-coded accounts across P&L and balance sheet
- 231 journal entries including 11 deliberately planted anomalies
- 30 balance sheet account reconciliations with realistic statuses

**Planted anomalies include:**
- SOD violation — preparer self-approving a $1.84M IBNR reserve posting
- Round number entries — $5M loss reserve adjustment, $3M tax provision
- Off-hours postings — investment reclass at 2:27 AM, reinsurance accrual at 11:22 PM
- Duplicate entries — same $847,320 premium receipt posted twice
- Unusual account pairing — expenses posted directly to retained earnings
- Large manual override — $4.75M labeled "override" bypassing controls
- Infrequent user — unknown preparer with no other postings in period

**Planted reconciliation issues include:**
- One account not started (Other Assets, $6.3M balance, 23.5% variance)
- SOD violation in reconciliation (preparer = approver on Deferred Tax Liability)
- Aged item over 90 days (Intangible Assets)
- $2.1M unsupported on IBNR Reserve

---

## Sample Output

The agent detected the following in the March 2025 APEX Insurance close:

**Overall Control Risk Rating: HIGH**

| Risk Category | Count |
|---------------|-------|
| HIGH risk findings | 16 |
| MEDIUM risk findings | 7 |
| LOW risk findings | 0 |

**Top 3 Priority Findings:**
1. Management override of loss reserve controls — offsetting $5M and $4.75M reserve entries by different preparers netting to $250K, with SOD violation on IBNR posting
2. Unreconciled Other Assets balance — $6.3M with 23.5% unexplained variance, zero reconciliation progress
3. Systemic SOD failures — violations in both journal entry and reconciliation processes, SAP workflow controls not enforced

**Key Automation Recommendations:**
- BlackLine Journal Entry Management — enforce dual-control workflow, block self-approval in real time
- BlackLine Account Reconciliation — SOD enforcement at account level, auto-escalation
- SAP Workflow Controls (PFCG) — prevent same user ID from posting and approving
- Workiva — link actuarial workbooks to GL entries for auditable chain from calculation to posting

---

## Roadmap

### V2 — Multi-period trend analysis
- Compare 3 months of close packages to identify recurring anomalies
- Flag accounts with consistent control failures across periods
- Trend charts showing control risk improvement or deterioration over time

### V3 — Real-time close monitoring
- Connect directly to SAP via API instead of Excel upload
- Flag anomalies as journal entries are posted during the close
- Alert controller when SOD violations or large manual entries occur

### V4 — Benchmarking
- Compare close metrics against industry benchmarks
- Days to close, manual entry rate, reconciliation completion rate
- Peer comparison for insurance companies of similar size

---

## About

Built by **Shuang Shi**, a finance and advisory manager with 9+ years of experience at Ernst & Young and KPMG, specializing in financial reporting transformation and close process optimization for large insurance and asset management clients.

This project applies Big 4 close review methodology — the same framework used in EY financial transformation engagements — to demonstrate how AI can automate the most time-consuming parts of a monthly close review.

**Relevant background:** Led cross-functional teams of 30+ on complex financial transformation projects, acted as product owner on close process redesign engagements, and directly identified opportunities to automate repetitive accounting and reporting workflows — the direct inspiration for this agent.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.14 |
| AI Model | Claude (Anthropic API) |
| Web Framework | Flask |
| Data Processing | Pandas |
| File Parsing | openpyxl |
| Environment | python-dotenv |
| Target ERP | SAP S/4HANA |

---

## License

MIT License — free to use and modify.
