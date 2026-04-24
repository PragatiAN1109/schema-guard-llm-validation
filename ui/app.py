"""
SchemaGuard — Dashboard UI

Modern SaaS-style validation control center.
Streamlit app with sidebar navigation, metric cards, and card-based layout.

Run:
    cd schema-guard-llm-validation
    streamlit run ui/app.py
"""

import sys, json, time
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from validator.pipeline import validate_record
from validator.batch_validation import validate_batch
from drift.drift_detector import generate_baseline

st.set_page_config(page_title="SchemaGuard", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

SEED_DIR = Path(__file__).parent.parent / "data_gen" / "sample_data"
DOMAINS = {"Healthcare Intake": "healthcare_intake", "Financial Loan Application": "financial_loan_application"}
SEED_FILES = {"healthcare_intake": "healthcare_seed_examples.json", "financial_loan_application": "finance_seed_examples.json"}


# ── Session state ──
if "history" not in st.session_state:
    st.session_state.history = []
if "totals" not in st.session_state:
    st.session_state.totals = {"total": 0, "trusted": 0, "flagged": 0, "quarantined": 0}

EXAMPLES = {
    "✅ Valid — Pneumonia patient (HC)": ("healthcare_intake", {"patient_id":"P-3021","first_name":"James","last_name":"Carter","date_of_birth":"1978-11-02","gender":"male","admission_date":"2024-09-14","discharge_date":"2024-09-19","diagnosis_code":"J18.9","diagnosis_description":"Pneumonia, unspecified organism","treating_physician":"Dr. Susan Park","medication":"Azithromycin","procedure_code":None,"insurance_provider":"Aetna","patient_age":45,"emergency_admission":False,"notes":None}),
    "❌ Discharge before admission (HC)": ("healthcare_intake", {"patient_id":"P-4412","first_name":"Sarah","last_name":"Mitchell","date_of_birth":"1990-01-20","gender":"female","admission_date":"2024-08-15","discharge_date":"2024-08-08","diagnosis_code":"N39.0","diagnosis_description":"Urinary tract infection","treating_physician":"Dr. Mark Evans","medication":"Ciprofloxacin","procedure_code":None,"insurance_provider":"UnitedHealth","patient_age":34,"emergency_admission":False,"notes":None}),
    "❌ Child with osteoporosis (HC)": ("healthcare_intake", {"patient_id":"P-1187","first_name":"Lily","last_name":"Thompson","date_of_birth":"2019-02-14","gender":"female","admission_date":"2024-06-20","discharge_date":"2024-06-21","diagnosis_code":"M81.0","diagnosis_description":"Age-related osteoporosis","treating_physician":"Dr. James Wu","medication":"Alendronate","procedure_code":None,"insurance_provider":"BlueCross","patient_age":5,"emergency_admission":False,"notes":None}),
    "✅ Valid — Home purchase loan (FN)": ("financial_loan_application", {"application_id":"LA-40821","applicant_name":"Michael Torres","date_of_birth":"1988-05-22","annual_income":92000,"employment_status":"employed","employer_name":"Deloitte","employment_length_years":6,"loan_amount":320000,"loan_purpose":"home_purchase","loan_term_months":360,"interest_rate":6.75,"credit_score":742,"existing_debt":18000,"application_date":"2024-08-10","approval_date":"2024-08-24","approved_amount":310000,"property_value":415000,"co_applicant":False,"notes":None}),
    "❌ Loan 52x income (FN)": ("financial_loan_application", {"application_id":"LA-33190","applicant_name":"Jessica Williams","date_of_birth":"1991-06-18","annual_income":48000,"employment_status":"employed","employer_name":"Target","employment_length_years":3,"loan_amount":2500000,"loan_purpose":"home_purchase","loan_term_months":360,"interest_rate":6.5,"credit_score":680,"existing_debt":15000,"application_date":"2024-05-12","approval_date":None,"approved_amount":None,"property_value":2600000,"co_applicant":False,"notes":None}),
    "❌ 18yr employment at age 24 (FN)": ("financial_loan_application", {"application_id":"LA-90155","applicant_name":"Tyler Brown","date_of_birth":"2000-02-10","annual_income":65000,"employment_status":"employed","employer_name":"Wells Fargo","employment_length_years":18,"loan_amount":35000,"loan_purpose":"auto","loan_term_months":48,"interest_rate":6.9,"credit_score":705,"existing_debt":8000,"application_date":"2024-11-01","approval_date":"2024-11-10","approved_amount":35000,"property_value":None,"co_applicant":False,"notes":None}),
}

def load_seeds(domain):
    p = SEED_DIR / SEED_FILES.get(domain, "")
    if not p.exists(): return []
    with open(p) as f: return json.load(f)

def dec_color(d):
    return {"trusted": "#238636", "flagged": "#d29922", "quarantined": "#da3633"}.get(d, "#666")

def dec_icon(d):
    return {"trusted": "🟢", "flagged": "🟡", "quarantined": "🔴"}.get(d, "⚪")


def card(label, value, color="#c9d1d9", prefix=""):
    st.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;border-radius:12px;padding:20px 24px;text-align:center">
    <div style="font-size:13px;color:#8b949e;text-transform:uppercase;letter-spacing:0.5px">{label}</div>
    <div style="font-size:36px;font-weight:800;color:{color};margin:4px 0">{prefix}{value}</div>
    </div>""", unsafe_allow_html=True)

def status_dot(label, active=True):
    c = "#238636" if active else "#da3633"
    return f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{c};margin-right:6px"></span>{label}'

def result_card(result):
    d = result["decision"]
    c = dec_color(d)
    st.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;border-left:4px solid {c};border-radius:8px;padding:16px 20px;margin-bottom:8px">
    <div style="display:flex;justify-content:space-between;align-items:center">
    <div><strong>{result.get('record_id','—')}</strong> &nbsp; <span style="color:{c};font-weight:700">{d.upper()}</span></div>
    <div style="font-size:22px;font-weight:700;color:{c}">{result['confidence_score']:.2f}</div>
    </div>
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="padding:8px 0 16px 0">
    <div style="font-size:1.6em;font-weight:800">🛡️ SchemaGuard</div>
    <div style="font-size:0.85em;color:#8b949e;margin-top:2px">Semantic Validation & Drift Detection</div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio("Navigation", ["Dashboard", "Validate", "Batch", "Use Cases", "Docs"],
                     label_visibility="collapsed")

    st.markdown("---")
    st.markdown(f"""
    <div style="font-size:12px;color:#8b949e">
    {status_dot("Validation Engine", True)}<br>
    {status_dot("Drift Detection", True)}<br>
    {status_dot("Scoring Pipeline", True)}<br>
    {status_dot("Async Queue", True)}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.caption("v0.3.0 · 2 domains · 10 rules")


# ═══════════════════════════════════════
# PAGE: DASHBOARD
# ═══════════════════════════════════════
if page == "Dashboard":
    st.markdown('<h2 style="margin-bottom:4px">Dashboard</h2>', unsafe_allow_html=True)
    st.caption("Real-time overview of validation activity")

    # Metric cards
    t = st.session_state.totals
    c1, c2, c3, c4 = st.columns(4)
    with c1: card("Total Validations", t["total"], "#58a6ff")
    with c2: card("Trusted", t["trusted"], "#238636")
    with c3: card("Flagged", t["flagged"], "#d29922")
    with c4: card("Quarantined", t["quarantined"], "#da3633")

    st.markdown("")

    # Two-column layout
    left, right = st.columns([3, 2])

    with left:
        st.markdown("#### Recent Activity")
        if st.session_state.history:
            for h in reversed(st.session_state.history[-8:]):
                result_card(h)
        else:
            st.markdown("""<div style="background:#161b22;border:1px solid #30363d;border-radius:12px;
            padding:40px;text-align:center;color:#8b949e">
            No validations yet. Go to <strong>Validate</strong> or <strong>Batch</strong> to get started.
            </div>""", unsafe_allow_html=True)


    with right:
        st.markdown("#### System Status")
        st.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;border-radius:12px;padding:20px">
        <div style="margin-bottom:12px">{status_dot("<strong>Validation Engine</strong> — operational", True)}</div>
        <div style="margin-bottom:12px">{status_dot("<strong>Drift Detection</strong> — operational", True)}</div>
        <div style="margin-bottom:12px">{status_dot("<strong>Confidence Scoring</strong> — operational", True)}</div>
        <div>{status_dot("<strong>Async Queue</strong> — operational", True)}</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("")
        st.markdown("#### Quick Stats")
        st.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;border-radius:12px;padding:20px">
        <div style="display:flex;justify-content:space-between;margin-bottom:8px">
            <span style="color:#8b949e">Domains</span><strong>2</strong></div>
        <div style="display:flex;justify-content:space-between;margin-bottom:8px">
            <span style="color:#8b949e">Semantic Rules</span><strong>10</strong></div>
        <div style="display:flex;justify-content:space-between;margin-bottom:8px">
            <span style="color:#8b949e">Drift Signals</span><strong>4</strong></div>
        <div style="display:flex;justify-content:space-between">
            <span style="color:#8b949e">Test Assertions</span><strong>135</strong></div>
        </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════
# PAGE: VALIDATE
# ═══════════════════════════════════════
elif page == "Validate":
    st.markdown('<h2 style="margin-bottom:4px">Validate Record</h2>', unsafe_allow_html=True)
    st.caption("Submit a single JSON record for full pipeline validation")

    input_col, result_col = st.columns([1, 1], gap="large")

    with input_col:
        st.markdown("#### Input")
        ex_choice = st.selectbox("Load example:", ["— Paste your own —"] + list(EXAMPLES.keys()), key="ex_sel")

        if ex_choice != "— Paste your own —":
            ex_domain, ex_record = EXAMPLES[ex_choice]
            default_json = json.dumps(ex_record, indent=2)
            domain = ex_domain
        else:
            domain = DOMAINS[st.selectbox("Domain:", list(DOMAINS.keys()), key="v_dom")]
            sample_key = list(EXAMPLES.keys())[0] if "healthcare" in domain else list(EXAMPLES.keys())[3]
            default_json = json.dumps(EXAMPLES[sample_key][1], indent=2)

        record_input = st.text_area("JSON Record:", value=default_json, height=320, key="v_input", label_visibility="collapsed")

        validate_btn = st.button("🔍  Validate Record", type="primary", use_container_width=True, key="v_btn")


    with result_col:
        st.markdown("#### Result")
        if validate_btn:
            try:
                record = json.loads(record_input)
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}"); st.stop()

            with st.spinner("Running pipeline..."):
                result = validate_record(record, domain)

            # Track
            st.session_state.history.append(result)
            st.session_state.totals["total"] += 1
            st.session_state.totals[result["decision"]] += 1

            # Decision badge
            d = result["decision"]; c = dec_color(d); s = result["confidence_score"]
            st.markdown(f"""<div style="background:{c};color:white;border-radius:12px;padding:20px;text-align:center;margin-bottom:16px">
            <div style="font-size:14px;text-transform:uppercase;letter-spacing:1px;opacity:0.85">Decision</div>
            <div style="font-size:32px;font-weight:800;margin:4px 0">{d.upper()}</div>
            <div style="font-size:18px;font-weight:600">Confidence: {s:.2f}</div>
            </div>""", unsafe_allow_html=True)


            # Status row
            s1, s2 = st.columns(2)
            with s1:
                if result["structural_valid"]: st.success("Structural: PASS")
                else: st.error("Structural: FAIL")
            with s2:
                if result["semantic_valid"]: st.success("Semantic: PASS")
                else: st.error("Semantic: FAIL")

            # Confidence bar
            st.progress(min(result["confidence_score"], 1.0))

            # Explanation
            st.markdown("##### Explanation")
            st.info(result["explanation"])

            # Violations
            if result["violated_rules"]:
                st.markdown("##### Violated Rules")
                for v in result["violated_rules"]:
                    sev = v["severity"]
                    ic = "🔴" if sev == "critical" else "🟡"
                    st.markdown(f"""{ic} **{v['rule_id']}** · `{sev}` · {v['rule_name']}
                    
&nbsp;&nbsp;&nbsp;&nbsp;Fields: `{', '.join(v['fields'])}` — {v['message']}""")

            with st.expander("Full JSON"):
                st.json({k: v for k, v in result.items() if k != "audit_entry"})
        else:
            st.markdown("""<div style="background:#161b22;border:1px solid #30363d;border-radius:12px;
            padding:60px;text-align:center;color:#8b949e">
            Select an example or paste JSON, then click <strong>Validate Record</strong>
            </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════
# PAGE: BATCH
# ═══════════════════════════════════════
elif page == "Batch":
    st.markdown('<h2 style="margin-bottom:4px">Batch Validation</h2>', unsafe_allow_html=True)
    st.caption("Process multiple records with drift detection")

    b_domain = DOMAINS[st.selectbox("Domain:", list(DOMAINS.keys()), key="b_dom")]

    # Upload section
    with st.container():
        up_col, opts_col = st.columns([2, 1])
        with up_col:
            uploaded = st.file_uploader("Upload JSON file:", type=["json"], key="b_up")
            batch_text = st.text_area("Or paste JSON array:", height=120, key="b_txt",
                                       placeholder='[{"patient_id": "P-1001", ...}, ...]')
        with opts_col:
            use_seeds = st.checkbox("Use seed data", value=True, key="b_seeds")
            st.markdown("")
            run_btn = st.button("📦  Run Batch", type="primary", use_container_width=True, key="b_run")

    if run_btn:
        records = None
        if uploaded:
            try:
                data = json.loads(uploaded.read().decode("utf-8"))
                records = data if isinstance(data, list) and all(isinstance(r, dict) for r in data) else [r["record"] for r in data if "record" in r]
            except Exception as e: st.error(f"Error: {e}"); st.stop()
        elif batch_text.strip():
            try:
                data = json.loads(batch_text)
                records = data if isinstance(data, list) else None
            except: st.error("Invalid JSON"); st.stop()


        if records is None and use_seeds:
            seeds = load_seeds(b_domain)
            if seeds:
                records = [s["record"] for s in seeds]
                st.info(f"Using {len(records)} seed records")

        if not records:
            st.warning("No input provided"); st.stop()

        # Auto-generate baseline
        all_seeds = load_seeds(b_domain)
        valid_recs = [s["record"] for s in all_seeds if s["category"] == "valid"]
        if valid_recs: generate_baseline(valid_recs, b_domain)

        with st.spinner(f"Validating {len(records)} records..."):
            batch_result = validate_batch(records, b_domain, run_drift=True)

        # Track
        for r in batch_result["results"]:
            st.session_state.history.append(r)
            st.session_state.totals["total"] += 1
            d = r.get("decision", "quarantined")
            st.session_state.totals[d] = st.session_state.totals.get(d, 0) + 1

        st.markdown("---")

        # Summary cards
        sm = batch_result["summary"]
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: card("Total", batch_result["total_records"], "#58a6ff")
        with c2: card("Trusted", sm["trusted"], "#238636")
        with c3: card("Flagged", sm["flagged"], "#d29922")
        with c4: card("Quarantined", sm["quarantined"], "#da3633")
        with c5: card("Avg Conf", f"{sm['mean_confidence']:.2f}", "#58a6ff")


        st.caption(f"Processed in {sm['processing_time_ms']:.1f}ms")

        # Results table
        st.markdown("#### Per-Record Results")
        for r in batch_result["results"]:
            result_card(r)
            if r.get("violated_rules"):
                for v in r["violated_rules"]:
                    st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;{v['rule_id']}: {v['message']}")

        # Drift alerts
        drift = batch_result.get("drift_summary")
        if drift:
            st.markdown("---")
            st.markdown("#### Drift Detection")
            if drift.get("drift_detected"):
                st.markdown(f"""<div style="background:#da363322;border:1px solid #da3633;border-radius:12px;padding:16px 20px">
                <strong style="color:#da3633">⚠️ Drift Detected — {len(drift['alerts'])} alert(s)</strong>
                </div>""", unsafe_allow_html=True)
                for a in drift["alerts"]:
                    ic = "🔴" if a["severity"] == "high" else "🟡"
                    st.markdown(f"{ic} **[{a['severity'].upper()}]** {a['message']}")
            elif drift.get("note"):
                st.info(drift["note"])
            else:
                st.success(f"✅ No drift detected ({drift.get('checked_fields', 0)} fields checked)")
            with st.expander("Drift Metrics"):
                st.json(drift.get("drift_metrics", {}))


# ═══════════════════════════════════════
# PAGE: USE CASES
# ═══════════════════════════════════════
elif page == "Use Cases":
    st.markdown('<h2 style="margin-bottom:4px">Use Cases</h2>', unsafe_allow_html=True)
    st.caption("Real-world scenarios where SchemaGuard prevents data quality failures")

    def use_case_card(icon, title, problem, bullets, outcome, color="#30363d"):
        items = "".join(f"<li style='margin-bottom:4px'>{b}</li>" for b in bullets)
        st.markdown(f"""<div style="background:#161b22;border:1px solid {color};border-radius:12px;padding:24px;margin-bottom:16px">
        <div style="font-size:20px;font-weight:700;margin-bottom:8px">{icon} {title}</div>
        <div style="color:#8b949e;margin-bottom:12px">{problem}</div>
        <ul style="margin:0 0 12px 16px;padding:0;color:#c9d1d9">{items}</ul>
        <div style="background:#23863622;border:1px solid #238636;border-radius:8px;padding:10px 14px;font-size:13px">
        <strong style="color:#238636">Outcome:</strong> {outcome}</div>
        </div>""", unsafe_allow_html=True)

    uc1, uc2 = st.columns(2)
    with uc1:
        use_case_card("🏥", "Healthcare Intake Validation",
            "LLMs generating patient records produce temporal contradictions and implausible diagnoses that pass schema checks.",
            ["Catches discharge before admission (HC-003)", "Flags adult diagnoses on pediatric patients (HC-004)", "Validates medication matches diagnosis (HC-005)"],
            "Bad records quarantined before entering EHR. Valid records flow with audit trail.", "#238636")

        use_case_card("🤖", "LLM Pipeline Quality Gate",
            "Teams using GPT-4/Claude for structured generation rely on schema validation alone. Output quality degrades silently.",
            ["Semantic rules catch cross-field contradictions", "Drift detection alerts on behavioral shifts", "Three-tier routing enables automated triage"],
            "Insert between LLM API and database. Trusted auto-insert, flagged to review queue, quarantined blocked.", "#58a6ff")


    with uc2:
        use_case_card("💰", "Loan Application Validation",
            "LLM-generated financial records contain extreme ratio violations and impossible employment timelines.",
            ["Blocks $2.5M loans on $48K income (FN-002)", "Catches 18yr employment at age 24 (FN-004)", "Validates approval dates after application (FN-001)"],
            "Impossible applications quarantined. Edge cases flagged for human review.", "#d29922")

        use_case_card("📊", "Batch Monitoring & Drift",
            "No single record is wrong, but the population shifts — younger patients, higher incomes, fewer edge cases.",
            ["z-score tracks numeric field mean shifts", "PSI monitors categorical distribution changes", "Null-rate and violation-rate signals catch slow degradation"],
            "Drift alerts fire on first shifted batch. Operations team investigates before data quality incident.", "#da3633")


# ═══════════════════════════════════════
# PAGE: DOCS
# ═══════════════════════════════════════
elif page == "Docs":
    st.markdown('<h2 style="margin-bottom:4px">Documentation</h2>', unsafe_allow_html=True)
    st.caption("Technical reference for SchemaGuard")

    with st.expander("**How It Works** — Pipeline overview", expanded=True):
        st.markdown("""Every record passes through a 4-stage pipeline:
1. **Structural** — JSON Schema Draft 7 (types, formats, required fields)
2. **Semantic** — 10 cross-field rules checking logical consistency
3. **Confidence** — Severity-weighted score (0.0–1.0)
4. **Decision** — Trusted (≥0.85) / Flagged (0.50–0.84) / Quarantined (<0.50)

For batches, drift detection runs after all records are validated.""")

    with st.expander("**Input Format** — Example payloads"):
        i1, i2 = st.columns(2)
        with i1:
            st.markdown("**Healthcare**")
            st.code(json.dumps({"patient_id":"P-3021","first_name":"James","date_of_birth":"1978-11-02","gender":"male","admission_date":"2024-09-14","discharge_date":"2024-09-19","diagnosis_code":"J18.9","medication":"Azithromycin","patient_age":45}, indent=2), language="json")
        with i2:
            st.markdown("**Finance**")
            st.code(json.dumps({"application_id":"LA-40821","applicant_name":"Michael Torres","annual_income":92000,"loan_amount":320000,"credit_score":742,"application_date":"2024-08-10"}, indent=2), language="json")


    with st.expander("**Output Format** — Validation response"):
        st.code(json.dumps({"record_id":"HC-val-a3f8c1","structural_valid":True,"semantic_valid":False,"violated_rules":[{"rule_id":"HC-003","severity":"critical","message":"Discharge precedes admission"}],"confidence_score":0.70,"decision":"quarantined"}, indent=2), language="json")

    with st.expander("**API Usage** — curl examples"):
        st.markdown("**Start server:**")
        st.code("uvicorn api.main:app --reload --port 8000", language="bash")
        st.markdown("**Sync validation:**")
        st.code('curl -X POST http://localhost:8000/validate \\\n  -H "Content-Type: application/json" \\\n  -d \'{"domain": "healthcare", "record": {...}}\'', language="bash")
        st.markdown("**Async flow:**")
        st.code('# Submit → returns job_id\ncurl -X POST http://localhost:8000/async/submit \\\n  -H "Authorization: Bearer sg-key-demo-000" \\\n  -d \'{"domain": "healthcare", "record": {...}}\'\n\n# Process queue\ncurl -X POST http://localhost:8000/async/process \\\n  -H "Authorization: Bearer sg-key-demo-000"\n\n# Fetch result\ncurl http://localhost:8000/async/result/{job_id} \\\n  -H "Authorization: Bearer sg-key-demo-000"', language="bash")

    with st.expander("**Rules Reference** — All 10 semantic rules"):
        r1, r2 = st.columns(2)
        with r1:
            st.markdown("**Healthcare Intake**")
            for rid, sev, desc in [("HC-001","critical","Age matches DOB vs admission"),("HC-002","critical","Admission after birth"),("HC-003","critical","Discharge after admission"),("HC-004","warning","Age-appropriate diagnosis"),("HC-005","warning","Medication plausibility")]:
                ic = "🔴" if sev == "critical" else "🟡"
                st.markdown(f"{ic} **{rid}** `{sev}` — {desc}")
        with r2:
            st.markdown("**Financial Loan**")
            for rid, sev, desc in [("FN-001","critical","Approval after application"),("FN-002","critical","Loan-to-income ≤ 10x"),("FN-003","warning","DTI ≤ 60%"),("FN-004","critical","Employment length vs age"),("FN-005","critical","Approved ≤ requested")]:
                ic = "🔴" if sev == "critical" else "🟡"
                st.markdown(f"{ic} **{rid}** `{sev}` — {desc}")

    with st.expander("**Scoring Logic** — How confidence is computed"):
        st.markdown("""```
Base: 1.0
  - Structural failure  → 0.0 (immediate)
  - Critical violation   → -0.30 each
  - Warning violation    → -0.12 each
  - Info violation       → -0.05 each
  - No rules evaluated   → -0.05
  - Drift alert (batch)  → -0.03 each (max -0.15)
  = Clamp to [0.0, 1.0]
```""")

    st.markdown("---")
    st.caption("SchemaGuard · Semantic Validation & Drift Detection for LLM Outputs")
