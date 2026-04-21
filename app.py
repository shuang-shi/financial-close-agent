from flask import Flask, render_template, request, jsonify
import anthropic
import pandas as pd
import json
import os
from dotenv import load_dotenv
from datetime import date

load_dotenv()

app = Flask(__name__)
client = anthropic.Anthropic()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def load_excel(filepath):
    xl = pd.ExcelFile(filepath)
    data = {}
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        data[sheet] = df
    return data

def summarize_trial_balance(df):
    summary = []
    for _, row in df.iterrows():
        if row.get("Variance_Pct", 0) and abs(float(row.get("Variance_Pct", 0))) > 10:
            summary.append(
                f"{row['Account_Code']} {row['Account_Name']}: "
                f"Current ${row['Current_Period_Balance']:,.0f} | "
                f"Prior ${row['Prior_Period_Balance']:,.0f} | "
                f"Variance {row['Variance_Pct']}%"
            )
    return "\n".join(summary[:30])

def summarize_journal_entries(df):
    total = len(df)
    off_hours = len(df[df["Posting_Time"].apply(
        lambda t: int(str(t).split(":")[0]) < 7 or int(str(t).split(":")[0]) > 18
        if pd.notna(t) else False
    )])
    sod = df[df["Preparer"] == df["Approver"]]
    def is_round(amt):
        try:
            return float(amt) % 100000 == 0
        except:
            return False
    round_nums = df[df["Amount_USD"].apply(is_round)]
    dups = df[df.duplicated(subset=["Amount_USD", "Debit_Account", "Credit_Account"], keep=False)]
    large = df[df["Amount_USD"].apply(lambda x: float(x) > 1_000_000 if pd.notna(x) else False)]

    summary = f"""
JOURNAL ENTRY STATISTICS:
- Total entries: {total}
- Off-hours postings (before 7am or after 6pm): {off_hours}
- SOD violations (preparer = approver): {len(sod)}
- Round number entries (multiples of $100,000): {len(round_nums)}
- Duplicate amount entries: {len(dups)}
- Large entries over $1M: {len(large)}

SOD VIOLATIONS:
{sod[['SAP_Document_Number','Description','Amount_USD','Preparer','Approver','Posting_Date']].to_string(index=False) if len(sod) > 0 else 'None'}

ROUND NUMBER ENTRIES:
{round_nums[['SAP_Document_Number','Description','Amount_USD','Debit_Account','Credit_Account','Preparer','Posting_Date']].to_string(index=False) if len(round_nums) > 0 else 'None'}

DUPLICATE AMOUNT ENTRIES:
{dups[['SAP_Document_Number','Description','Amount_USD','Debit_Account','Credit_Account','Preparer','Posting_Date']].to_string(index=False) if len(dups) > 0 else 'None'}

LARGE ENTRIES OVER $1M:
{large[['SAP_Document_Number','Description','Amount_USD','Debit_Account','Credit_Account','Preparer','Approver','Posting_Time']].to_string(index=False) if len(large) > 0 else 'None'}
"""
    return summary

def summarize_reconciliation(df):
    not_started = df[df["Status"] == "Not Started"]
    in_progress = df[df["Status"] == "In Progress"]
    sod_violations = df[df["SOD_Violation"] == "YES"]
    aged = df[df["Aged_Item_Flag"] == "YES"]

    summary = f"""
RECONCILIATION STATISTICS:
- Total accounts requiring reconciliation: {len(df)}
- Complete: {len(df[df['Status'] == 'Complete'])}
- In Progress: {len(in_progress)}
- Not Started: {len(not_started)}
- SOD violations: {len(sod_violations)}
- Accounts with items aged over 90 days: {len(aged)}

NOT STARTED (OVERDUE):
{not_started[['Account_Code','Account_Name','GL_Balance','Preparer','Notes']].to_string(index=False) if len(not_started) > 0 else 'None'}

IN PROGRESS WITH OPEN ITEMS:
{in_progress[['Account_Code','Account_Name','GL_Balance','Open_Reconciling_Items_USD','Oldest_Item_Age_Days','Notes']].to_string(index=False) if len(in_progress) > 0 else 'None'}

SOD VIOLATIONS IN RECONCILIATIONS:
{sod_violations[['Account_Code','Account_Name','Preparer','Approver','Notes']].to_string(index=False) if len(sod_violations) > 0 else 'None'}

AGED ITEMS OVER 90 DAYS:
{aged[['Account_Code','Account_Name','Open_Reconciling_Items_USD','Oldest_Item_Age_Days','Notes']].to_string(index=False) if len(aged) > 0 else 'None'}
"""
    return summary

def run_analysis(filepath):
    data = load_excel(filepath)
    tb_df    = data.get("Trial_Balance", pd.DataFrame())
    je_df    = data.get("Journal_Entries", pd.DataFrame())
    recon_df = data.get("Reconciliation_Tracker", pd.DataFrame())

    tb_summary    = summarize_trial_balance(tb_df)
    je_summary    = summarize_journal_entries(je_df)
    recon_summary = summarize_reconciliation(recon_df)

    prompt = f"""You are a Big 4 senior advisory manager reviewing an insurance company's
monthly financial close package. The company uses SAP as their ERP system.

Analyze the data below and produce a structured close intelligence report with exactly
these 5 sections. Be specific — reference account codes, document numbers, amounts,
and preparer names as evidence.

IMPORTANT: Complete ALL 5 sections fully. Do not truncate any section.

---

SECTION 1 — JOURNAL ENTRY ANOMALIES
List every anomaly found. For each one provide:
- Anomaly type
- SAP document number and amount
- Specific evidence
- Risk level: HIGH / MEDIUM / LOW

SECTION 2 — TRIAL BALANCE VARIANCES
Identify accounts with unusual movements vs prior period.
For each flagged account provide:
- Account code and name
- Current vs prior balance and variance %
- Why this movement is unusual
- Risk level: HIGH / MEDIUM / LOW

SECTION 3 — RECONCILIATION CONTROL RISKS
Identify control failures in the reconciliation process.
For each issue provide:
- Account code and name
- Control failure type
- Specific evidence
- Risk level: HIGH / MEDIUM / LOW

SECTION 4 — CONTROL RISK SUMMARY
- Top 3 highest priority risks requiring immediate action
- Overall control risk rating: HIGH / MEDIUM / LOW
- Key themes across all three data sets

SECTION 5 — REMEDIATION AND AUTOMATION RECOMMENDATIONS
For each control risk provide exactly three items:
- Immediate Fix
- Process Redesign
- Automation Opportunity (name specific tools: BlackLine, Workiva, SAP, RPA)

---

TRIAL BALANCE DATA (accounts with >10% variance):
{tb_summary}

JOURNAL ENTRY DATA:
{je_summary}

RECONCILIATION DATA:
{recon_summary}
"""

    print("Sending to Claude for analysis...")
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}]
    )

    result = message.content[0].text

    # Save to file so we never need to re-run for display testing
    with open("last_analysis.txt", "w") as f:
        f.write(result)
    print("Analysis saved to last_analysis.txt")

    return result

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if not file.filename.endswith((".xlsx", ".xls")):
        return jsonify({"error": "Please upload an Excel file (.xlsx)"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    try:
        analysis = run_analysis(filepath)
        return jsonify({
            "analysis": analysis,
            "generated_date": date.today().strftime("%B %d, %Y"),
            "filename": file.filename
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/report")
def report():
    return render_template("report.html")

if __name__ == "__main__":
    app.run(debug=True)
