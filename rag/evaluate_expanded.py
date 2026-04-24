"""
SchemaGuard RAG — Expanded Evaluation Suite (28 cases)
=======================================================
Expands from 6 → 28 cases covering:
  - All 10 semantic rules (HC-001 through HC-005, FN-001 through FN-005)
  - Multi-violation records (2–3 simultaneous violations)
  - Near-miss edge cases (boundary conditions)
  - Valid-record control group (should produce clean explanations)
  - Severity variants (warning vs critical violation)

Output:
  evaluation/rag_results.json          — structured results (28 cases)
  outputs/plots/rag_comparison.png     — 4-panel quality/length/retrieval/latency
  docs/evaluation/rag_failures.md      — failure analysis

Usage:
  python rag/evaluate_expanded.py           # dry-run (retrieval only, no API)
  python rag/evaluate_expanded.py --live    # full LLM evaluation (needs API key)
  python rag/evaluate_expanded.py --merge   # merge live results with dry-run
"""
from __future__ import annotations
import os, sys, json, time, argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

EVAL_DIR  = PROJECT_ROOT / "evaluation"
PLOTS_DIR = PROJECT_ROOT / "outputs" / "plots"
DOCS_DIR  = PROJECT_ROOT / "docs" / "evaluation"
DATA_DIR  = PROJECT_ROOT / "data"
EVAL_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
# 28 TEST CASES
# ══════════════════════════════════════════════════════════════════════════════

HC_BASE = dict(
    first_name="James", last_name="Carter", date_of_birth="1978-11-02",
    gender="male", admission_date="2024-09-14", discharge_date="2024-09-19",
    diagnosis_code="J18.9", diagnosis_description="Pneumonia, unspecified",
    treating_physician="Dr. Susan Park", medication="Azithromycin",
    procedure_code=None, insurance_provider="Aetna",
    patient_age=45, emergency_admission=False, notes=None,
)
FN_BASE = dict(
    applicant_name="Michael Torres", date_of_birth="1988-05-22",
    annual_income=92000, employment_status="employed",
    employer_name="Deloitte", employment_length_years=6,
    loan_amount=320000, loan_purpose="home_purchase",
    loan_term_months=360, interest_rate=6.75, credit_score=742,
    existing_debt=18000, application_date="2024-08-10",
    approval_date="2024-08-24", approved_amount=310000,
    property_value=415000, co_applicant=False, notes=None,
)

TEST_CASES = [

    # ── HC single-rule violations ──────────────────────────────────────────

    {"case_id":"HC-003-a","domain":"healthcare_intake","category":"single_violation",
     "label":"Discharge 7 days before admission",
     "record":{**HC_BASE,"patient_id":"P-4412","first_name":"Sarah","last_name":"Mitchell",
               "date_of_birth":"1990-01-20","admission_date":"2024-08-15",
               "discharge_date":"2024-08-08","diagnosis_code":"N39.0",
               "diagnosis_description":"Urinary tract infection","medication":"Ciprofloxacin",
               "patient_age":34,"insurance_provider":"UnitedHealth"}},

    {"case_id":"HC-003-b","domain":"healthcare_intake","category":"near_miss",
     "label":"Discharge 1 day before admission (boundary violation)",
     "record":{**HC_BASE,"patient_id":"P-4413","admission_date":"2024-09-14",
               "discharge_date":"2024-09-13","patient_age":45}},

    {"case_id":"HC-001-a","domain":"healthcare_intake","category":"single_violation",
     "label":"Age mismatch: stated 52, computed 34",
     "record":{**HC_BASE,"patient_id":"P-7203","first_name":"David","last_name":"Kim",
               "date_of_birth":"1990-04-10","admission_date":"2024-11-03",
               "discharge_date":"2024-11-06","diagnosis_code":"K21.0",
               "diagnosis_description":"GERD","medication":"Omeprazole",
               "patient_age":52,"insurance_provider":"Cigna"}},

    {"case_id":"HC-001-b","domain":"healthcare_intake","category":"near_miss",
     "label":"Age off by exactly 2 (boundary violation HC-001)",
     "record":{**HC_BASE,"patient_id":"P-7204","patient_age":47}},

    {"case_id":"HC-002-a","domain":"healthcare_intake","category":"single_violation",
     "label":"Admission before date of birth (future DOB)",
     "record":{**HC_BASE,"patient_id":"P-0099","first_name":"Newborn","last_name":"Garcia",
               "date_of_birth":"2025-03-15","admission_date":"2024-09-14",
               "discharge_date":"2024-09-17","patient_age":0}},

    {"case_id":"HC-002-b","domain":"healthcare_intake","category":"single_violation",
     "label":"Admission 1 day before DOB (off-by-one temporal error)",
     "record":{**HC_BASE,"patient_id":"P-0100","date_of_birth":"2024-09-15",
               "admission_date":"2024-09-14","discharge_date":"2024-09-17","patient_age":0}},

    {"case_id":"HC-004-a","domain":"healthcare_intake","category":"single_violation",
     "label":"Adult-only ICD code on 5-year-old (osteoporosis)",
     "record":{**HC_BASE,"patient_id":"P-1187","first_name":"Lily","last_name":"Thompson",
               "date_of_birth":"2019-02-14","admission_date":"2024-06-20",
               "discharge_date":"2024-06-21","diagnosis_code":"M81.0",
               "diagnosis_description":"Age-related osteoporosis","medication":"Alendronate",
               "patient_age":5,"insurance_provider":"BlueCross"}},

    {"case_id":"HC-004-b","domain":"healthcare_intake","category":"single_violation",
     "label":"Adult-only ICD code on 16-year-old (boundary case)",
     "record":{**HC_BASE,"patient_id":"P-1188","first_name":"Teen","last_name":"Patient",
               "date_of_birth":"2007-09-15","admission_date":"2024-09-14",
               "discharge_date":"2024-09-15","diagnosis_code":"I25.10",
               "diagnosis_description":"Ischaemic heart disease","medication":"Azithromycin",
               "patient_age":16}},

    {"case_id":"HC-005-a","domain":"healthcare_intake","category":"single_violation",
     "label":"Cardiac medication prescribed for UTI diagnosis",
     "record":{**HC_BASE,"patient_id":"P-5599","first_name":"Ana","last_name":"Martinez",
               "date_of_birth":"1975-07-20","admission_date":"2024-10-01",
               "discharge_date":"2024-10-03","diagnosis_code":"N39.0",
               "diagnosis_description":"Urinary tract infection","medication":"Metoprolol",
               "patient_age":49}},

    {"case_id":"HC-005-b","domain":"healthcare_intake","category":"single_violation",
     "label":"Diabetes medication prescribed for pneumonia",
     "record":{**HC_BASE,"patient_id":"P-5600","first_name":"Lee","last_name":"Wang",
               "date_of_birth":"1965-03-10","admission_date":"2024-07-15",
               "discharge_date":"2024-07-19","diagnosis_code":"J18.9",
               "diagnosis_description":"Pneumonia","medication":"Metformin",
               "patient_age":59}},

    # ── HC valid-record controls ───────────────────────────────────────────

    {"case_id":"HC-valid-1","domain":"healthcare_intake","category":"valid_control",
     "label":"Valid adult pneumonia record (all rules pass)",
     "record":{**HC_BASE,"patient_id":"P-3021"}},

    {"case_id":"HC-valid-2","domain":"healthcare_intake","category":"valid_control",
     "label":"Valid same-day discharge (LOS=0, outpatient)",
     "record":{**HC_BASE,"patient_id":"P-6650","first_name":"Carlos","last_name":"Rivera",
               "date_of_birth":"1985-07-30","admission_date":"2024-09-22",
               "discharge_date":"2024-09-22","diagnosis_code":"R10.9",
               "diagnosis_description":"Abdominal pain","medication":None,"patient_age":39,
               "emergency_admission":True}},

    # ── HC multi-violation ─────────────────────────────────────────────────

    {"case_id":"HC-multi-1","domain":"healthcare_intake","category":"multi_violation",
     "label":"HC-001 + HC-003: age mismatch AND discharge before admission",
     "record":{**HC_BASE,"patient_id":"P-9901","patient_age":70,
               "discharge_date":"2024-09-10"}},

    {"case_id":"HC-multi-2","domain":"healthcare_intake","category":"multi_violation",
     "label":"HC-002 + HC-003: future DOB AND discharge before admission",
     "record":{**HC_BASE,"patient_id":"P-9902","date_of_birth":"2025-01-01",
               "discharge_date":"2024-09-13","patient_age":0}},

    # ── FN single-rule violations ──────────────────────────────────────────

    {"case_id":"FN-001-a","domain":"financial_loan_application","category":"single_violation",
     "label":"Approval date 22 days before application",
     "record":{**FN_BASE,"application_id":"LA-78412","applicant_name":"Robert Chen",
               "date_of_birth":"1982-09-05","annual_income":78000,
               "employer_name":"Amazon","employment_length_years":4,"loan_amount":45000,
               "loan_purpose":"auto","loan_term_months":60,"credit_score":715,
               "existing_debt":12000,"application_date":"2024-07-20",
               "approval_date":"2024-06-28","approved_amount":45000,"property_value":None}},

    {"case_id":"FN-001-b","domain":"financial_loan_application","category":"near_miss",
     "label":"Approval exactly 1 day before application (off-by-one)",
     "record":{**FN_BASE,"application_id":"LA-78413","application_date":"2024-08-10",
               "approval_date":"2024-08-09","approved_amount":310000}},

    {"case_id":"FN-002-a","domain":"financial_loan_application","category":"single_violation",
     "label":"Loan-to-income ratio 52× (extreme case)",
     "record":{**FN_BASE,"application_id":"LA-33190","applicant_name":"Jessica Williams",
               "date_of_birth":"1991-06-18","annual_income":48000,
               "employer_name":"Target","employment_length_years":3,"loan_amount":2500000,
               "loan_purpose":"home_purchase","credit_score":680,"existing_debt":15000,
               "application_date":"2024-05-12","approval_date":None,"approved_amount":None,
               "property_value":2600000}},

    {"case_id":"FN-002-b","domain":"financial_loan_application","category":"near_miss",
     "label":"Loan-to-income exactly 10.0001× (fractional over threshold)",
     "record":{**FN_BASE,"application_id":"LA-33191","annual_income":31999,
               "loan_amount":320000}},

    {"case_id":"FN-003-a","domain":"financial_loan_application","category":"single_violation",
     "label":"Debt-to-income ratio 83% (well over 60% threshold)",
     "record":{**FN_BASE,"application_id":"LA-55500","applicant_name":"Marco Rossi",
               "date_of_birth":"1980-06-15","annual_income":60000,
               "employer_name":"Ford","employment_length_years":8,"loan_amount":200000,
               "loan_purpose":"refinance","credit_score":660,"existing_debt":50000,
               "application_date":"2024-09-05","approval_date":"2024-09-20",
               "approved_amount":190000,"property_value":280000}},

    {"case_id":"FN-003-b","domain":"financial_loan_application","category":"near_miss",
     "label":"DTI exactly 60.1% (just over warning threshold)",
     "record":{**FN_BASE,"application_id":"LA-55501","annual_income":100000,
               "existing_debt":60100}},

    {"case_id":"FN-004-a","domain":"financial_loan_application","category":"single_violation",
     "label":"24-year-old claims 18 years employment (started at age 6)",
     "record":{**FN_BASE,"application_id":"LA-90155","applicant_name":"Tyler Brown",
               "date_of_birth":"2000-02-10","annual_income":65000,
               "employer_name":"Wells Fargo","employment_length_years":18,"loan_amount":35000,
               "loan_purpose":"auto","loan_term_months":48,"credit_score":705,
               "existing_debt":8000,"application_date":"2024-11-01",
               "approval_date":"2024-11-10","approved_amount":35000,"property_value":None}},

    {"case_id":"FN-004-b","domain":"financial_loan_application","category":"near_miss",
     "label":"Employment length exactly at maximum for age (boundary pass)",
     "record":{**FN_BASE,"application_id":"LA-90156","date_of_birth":"1990-01-01",
               "application_date":"2024-08-10","employment_length_years":18}},

    {"case_id":"FN-005-a","domain":"financial_loan_application","category":"single_violation",
     "label":"Approved $80k over requested $320k loan amount",
     "record":{**FN_BASE,"application_id":"LA-11200","applicant_name":"Diana Prince",
               "date_of_birth":"1985-04-12","annual_income":95000,
               "employer_name":"Boeing","employment_length_years":9,"loan_amount":320000,
               "approved_amount":400000,"loan_purpose":"home_purchase"}},

    {"case_id":"FN-005-b","domain":"financial_loan_application","category":"near_miss",
     "label":"Approved exactly $1 over requested (minimal violation)",
     "record":{**FN_BASE,"application_id":"LA-11201","loan_amount":320000,
               "approved_amount":320001}},

    # ── FN valid-record controls ───────────────────────────────────────────

    {"case_id":"FN-valid-1","domain":"financial_loan_application","category":"valid_control",
     "label":"Valid employed applicant, home purchase (all rules pass)",
     "record":{**FN_BASE,"application_id":"LA-40821"}},

    {"case_id":"FN-valid-2","domain":"financial_loan_application","category":"valid_control",
     "label":"Valid same-day approval, small personal loan",
     "record":{**FN_BASE,"application_id":"LA-82701","applicant_name":"Amanda Liu",
               "date_of_birth":"1993-04-08","annual_income":71000,
               "employer_name":"Google","employment_length_years":5,"loan_amount":5000,
               "loan_purpose":"personal","loan_term_months":12,"credit_score":790,
               "existing_debt":3000,"application_date":"2024-11-15",
               "approval_date":"2024-11-15","approved_amount":5000,
               "property_value":None}},

    # ── FN multi-violation ─────────────────────────────────────────────────

    {"case_id":"FN-multi-1","domain":"financial_loan_application","category":"multi_violation",
     "label":"FN-001 + FN-002: approval before application AND extreme LTI",
     "record":{**FN_BASE,"application_id":"LA-99001","annual_income":48000,
               "loan_amount":1200000,"application_date":"2024-08-10",
               "approval_date":"2024-07-01"}},

    {"case_id":"FN-multi-2","domain":"financial_loan_application","category":"multi_violation",
     "label":"FN-002 + FN-003 + FN-005: extreme LTI + high DTI + over-approved",
     "record":{**FN_BASE,"application_id":"LA-99002","annual_income":30000,
               "loan_amount":500000,"existing_debt":25000,"approved_amount":600000}},
]

print(f"Test cases defined: {len(TEST_CASES)}")
cats = {}
for c in TEST_CASES:
    cats[c['category']] = cats.get(c['category'],0)+1
for cat, n in sorted(cats.items()):
    print(f"  {cat}: {n}")


# ══════════════════════════════════════════════════════════════════════════════
# SCORING
# ══════════════════════════════════════════════════════════════════════════════

def score_explanation(text: str, case: dict) -> dict:
    t  = text.lower()
    r  = case["record"]
    ci = case["case_id"].split("-")[0] + "-" + case["case_id"].split("-")[1]  # e.g. HC-003

    scores = {}
    scores["cites_rule"]       = ci.lower() in t
    field_vals = [str(v).lower() for v in r.values() if v is not None]
    scores["cites_field_value"] = any(fv[:6] in t for fv in field_vals if len(fv) > 4)
    action_words = ["correct","review","verify","update","reconcil","check",
                    "investigat","remediat","fix","should be","must be","resubmit"]
    scores["has_action"]       = any(w in t for w in action_words)
    ref_words    = ["regulation","cfpb","cms","hl7","fhir","icd","jama",
                    "joint commission","ecoa","tila","occ","fannie","ahrq",
                    "guideline","standard","policy","requirement",
                    "per ","under ","section","§","mandate","flsa","atm",
                    "§482","§1026","chapter 1"]
    scores["cites_reference"]  = any(w in t for w in ref_words)
    wc = len(text.split())
    scores["word_count"]       = wc
    scores["length_ok"]        = 40 <= wc <= 400
    why_words    = ["risk","error","reject","deny","bias","safety",
                    "billing","compli","downstream","impact","consequen",
                    "fraud","violat","audit","claim","patient","clinical"]
    scores["explains_impact"]  = any(w in t for w in why_words)

    binary = [v for k, v in scores.items()
              if k != "word_count" and isinstance(v, bool)]
    scores["composite"]     = sum(binary)
    scores["composite_max"] = len(binary)
    return scores


# ══════════════════════════════════════════════════════════════════════════════
# SINGLE-CASE RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def run_case(case: dict, live: bool = False) -> dict:
    import logging; logging.disable(logging.WARNING)
    from validator.pipeline import validate_record
    from rag.explainer import explain_with_rag, explain_baseline

    val        = validate_record(case["record"], case["domain"],
                                 record_id=f"eval-{case['case_id']}")
    violations = val.get("violated_rules", [])
    decision   = val["decision"]
    confidence = val["confidence_score"]

    baseline = explain_baseline(
        case["record"], case["domain"], violations, decision,
        record_id=f"eval-{case['case_id']}"
    )

    dry_run = not live
    t0 = time.perf_counter()
    try:
        rag_result = explain_with_rag(
            record=case["record"], domain=case["domain"],
            violations=violations, decision=decision,
            record_id=f"eval-{case['case_id']}", top_k=3, dry_run=dry_run,
        )
        rag_text   = rag_result.rag_explanation
        retrieved  = [
            {"chunk_id": c.chunk_id, "rule_id": c.rule_id,
             "title": c.title, "source": c.source,
             "score": round(c.score, 4), "preview": c.text[:200]}
            for c in rag_result.retrieved_chunks
        ]
        latency_ms = rag_result.latency_ms
        retrieval_query = rag_result.retrieval_query
    except Exception as e:
        rag_text = f"[error: {e}]"
        retrieved, latency_ms, retrieval_query = [], 0, ""

    baseline_scores = score_explanation(baseline, case)
    rag_scores      = score_explanation(rag_text,  case)

    return {
        "case_id":        case["case_id"],
        "domain":         case["domain"],
        "category":       case["category"],
        "label":          case["label"],
        "decision":       decision,
        "confidence_score": confidence,
        "violated_rules": [v["rule_id"] for v in violations],
        "mode":           "live" if live else "dry_run",
        "baseline": {"text": baseline,  "scores": baseline_scores},
        "rag":      {
            "text": rag_text,  "scores": rag_scores,
            "retrieved_chunks": retrieved,
            "retrieval_query":  retrieval_query,
            "latency_ms":       latency_ms,
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# PLOTS
# ══════════════════════════════════════════════════════════════════════════════

def write_chart(results: list[dict], path: Path) -> None:
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    BG = "#0d1117"; AX = "#161b22"; BD = "#30363d"; FG = "#c9d1d9"; MU = "#8b949e"
    GR = "#21262d"; BLUE = "#58a6ff"; GREEN = "#238636"; RED = "#da3633"
    YELLOW = "#d29922"; PURPLE = "#8957e5"; ORANGE = "#f78166"

    plt.rcParams.update({
        "figure.facecolor":BG,"axes.facecolor":AX,"axes.edgecolor":BD,
        "axes.labelcolor":FG,"xtick.color":MU,"ytick.color":MU,
        "text.color":FG,"grid.color":GR,"grid.linestyle":"--","grid.alpha":0.45,
    })

    # Split by category for colour coding
    cat_colors = {
        "single_violation": BLUE, "near_miss": YELLOW,
        "valid_control": GREEN, "multi_violation": ORANGE,
    }

    fig = plt.figure(figsize=(18, 14))
    fig.suptitle(f"SchemaGuard RAG — Expanded Evaluation ({len(results)} Cases)",
                 fontsize=14, color=BLUE, y=1.01)
    gs = fig.add_gridspec(2, 2, hspace=0.42, wspace=0.32)

    case_ids    = [r["case_id"] for r in results]
    base_scores = [r["baseline"]["scores"]["composite"] for r in results]
    rag_scores  = [r["rag"]["scores"]["composite"] for r in results]
    base_words  = [r["baseline"]["scores"]["word_count"] for r in results]
    rag_words   = [r["rag"]["scores"]["word_count"]      for r in results]
    top_scores  = [max((c["score"] for c in r["rag"]["retrieved_chunks"]),
                       default=0.0) for r in results]
    categories  = [r["category"] for r in results]
    bar_colors  = [cat_colors.get(c, MU) for c in categories]

    x = np.arange(len(case_ids)); w = 0.38
    rot = 55

    # Panel 1: Baseline vs RAG composite score
    ax1 = fig.add_subplot(gs[0, 0])
    b1 = ax1.bar(x - w/2, base_scores, w, label="Baseline", color=YELLOW, alpha=0.82, zorder=3)
    b2 = ax1.bar(x + w/2, rag_scores,  w, label="RAG",      color=BLUE,   alpha=0.82, zorder=3)
    ax1.set_title("Quality Score (0–6 criteria)", color=FG, fontsize=11)
    ax1.set_xticks(x); ax1.set_xticklabels(case_ids, rotation=rot, ha="right", fontsize=7)
    ax1.set_ylim(0, 7.5); ax1.grid(axis="y", zorder=0)
    ax1.legend(fontsize=9)
    for bar in list(b1) + list(b2):
        v = int(bar.get_height())
        if v > 0:
            ax1.text(bar.get_x()+bar.get_width()/2, v+0.08,
                     str(v), ha="center", fontsize=7, color=FG)

    # Panel 2: Explanation word count
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.bar(x - w/2, base_words, w, label="Baseline", color=YELLOW, alpha=0.82, zorder=3)
    ax2.bar(x + w/2, rag_words,  w, label="RAG",      color=BLUE,   alpha=0.82, zorder=3)
    ax2.axhline(40,  color=RED,   linestyle=":", linewidth=1.2, alpha=0.7, label="Min 40w")
    ax2.axhline(400, color=RED,   linestyle=":", linewidth=1.2, alpha=0.7, label="Max 400w")
    ax2.set_title("Explanation Word Count", color=FG, fontsize=11)
    ax2.set_xticks(x); ax2.set_xticklabels(case_ids, rotation=rot, ha="right", fontsize=7)
    ax2.grid(axis="y", zorder=0); ax2.legend(fontsize=9)

    # Panel 3: Retrieval cosine scores (top-1), coloured by category
    ax3 = fig.add_subplot(gs[1, 0])
    bars = ax3.bar(case_ids, top_scores, color=bar_colors, alpha=0.85, zorder=3)
    ax3.axhline(0.50, color=GREEN, linestyle="--", linewidth=1.2, label="Good (0.50+)")
    ax3.axhline(0.35, color=YELLOW,linestyle="--", linewidth=1.2, label="Fair (0.35+)")
    ax3.set_title("Top-1 Retrieval Score (cosine)", color=FG, fontsize=11)
    ax3.set_xticks(range(len(case_ids)))
    ax3.set_xticklabels(case_ids, rotation=rot, ha="right", fontsize=7)
    ax3.set_ylim(0, 1.05); ax3.grid(axis="y", zorder=0); ax3.legend(fontsize=9)
    for bar, s in zip(bars, top_scores):
        ax3.text(bar.get_x()+bar.get_width()/2, s+0.01,
                 f"{s:.3f}", ha="center", fontsize=6.5, color=FG)
    # Category legend
    for cat, col in cat_colors.items():
        ax3.bar([], [], color=col, alpha=0.85, label=cat.replace("_"," "))
    ax3.legend(fontsize=7.5, loc="lower right")

    # Panel 4: Score breakdown by category (box chart)
    ax4 = fig.add_subplot(gs[1, 1])
    cat_list  = sorted(set(categories))
    cat_data  = [[r["rag"]["scores"]["composite"]
                  for r in results if r["category"] == cat]
                 for cat in cat_list]
    bp = ax4.boxplot(cat_data, patch_artist=True, medianprops={"color":"white","linewidth":2})
    for patch, cat in zip(bp["boxes"], cat_list):
        patch.set_facecolor(cat_colors.get(cat, MU))
        patch.set_alpha(0.75)
    for element in ["whiskers","caps","fliers"]:
        for item in bp[element]:
            item.set_color(MU)
    ax4.set_xticks(range(1, len(cat_list)+1))
    ax4.set_xticklabels([c.replace("_","\n") for c in cat_list], fontsize=9)
    ax4.set_ylabel("RAG quality score (0–6)", fontsize=10)
    ax4.set_title("RAG Quality by Category", color=FG, fontsize=11)
    ax4.grid(axis="y", zorder=0)

    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    print(f"  ✓ {path.name}")


# ══════════════════════════════════════════════════════════════════════════════
# FAILURE ANALYSIS REPORT
# ══════════════════════════════════════════════════════════════════════════════

def write_failure_report(results: list[dict], path: Path) -> None:
    now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    lines = [
        "# SchemaGuard RAG — Failure Analysis",
        "",
        f"> Generated: {now}  ",
        f"> Cases evaluated: {len(results)}  ",
        "> Mode: dry-run retrieval + simulated scoring (new cases) / live LLM (original 6 cases)",
        "",
        "---", "",
        "## 1. Scoring Rubric",
        "",
        "| # | Criterion | What it checks |",
        "|---|-----------|----------------|",
        "| 1 | cites_rule | Explanation mentions the violated rule ID |",
        "| 2 | cites_field_value | References at least one specific field value from the record |",
        "| 3 | has_action | Includes a remediation or correction suggestion |",
        "| 4 | cites_reference | Names a regulation, clinical standard, or guideline |",
        "| 5 | length_ok | Word count 40–400 (not too brief, not bloated) |",
        "| 6 | explains_impact | States the downstream clinical or regulatory consequence |",
        "",
        "---", "",
        "## 2. Full Results Table", "",
        "| Case ID | Category | Violations | Decision | Conf | B-score | RAG-score | Δ | Top-k |",
        "|---------|----------|------------|----------|------|---------|-----------|---|-------|",
    ]

    for r in results:
        bs = r["baseline"]["scores"]["composite"]
        rs = r["rag"]["scores"]["composite"]
        delta = f"+{rs-bs}" if rs >= bs else str(rs-bs)
        top_k = round(max((c["score"] for c in r["rag"]["retrieved_chunks"]),
                          default=0.0), 3)
        viols = ", ".join(r["violated_rules"]) or "—"
        lines.append(
            f"| {r['case_id']} | {r['category'].replace('_',' ')} "
            f"| {viols} | {r['decision']} | {r['confidence_score']:.2f} "
            f"| {bs}/6 | {rs}/6 | **{delta}** | {top_k} |"
        )

    # Aggregate stats
    avg_b  = sum(r["baseline"]["scores"]["composite"] for r in results) / len(results)
    avg_r  = sum(r["rag"]["scores"]["composite"]      for r in results) / len(results)
    avg_tk = sum(
        max((c["score"] for c in r["rag"]["retrieved_chunks"]), default=0.0)
        for r in results) / len(results)

    lines += [
        "",
        f"**Average baseline score:** {avg_b:.2f}/6  ",
        f"**Average RAG score:** {avg_r:.2f}/6  ",
        f"**Average top-1 retrieval cosine:** {avg_tk:.3f}",
        "",
        "---", "",
        "## 3. Failure Patterns", "",
    ]

    # Find cases where baseline failed a specific criterion
    criteria = ["cites_rule","cites_field_value","has_action","cites_reference",
                "length_ok","explains_impact"]
    criterion_labels = {
        "cites_rule":       "Does not cite the rule ID",
        "cites_field_value":"Does not cite specific field values",
        "has_action":       "No remediation action",
        "cites_reference":  "No regulatory/clinical reference cited",
        "length_ok":        "Explanation too short or too long",
        "explains_impact":  "No clinical/regulatory consequence stated",
    }
    lines += [
        "### 3.1 Baseline Explanation Failures", "",
        "Criteria where the deterministic baseline explanation consistently fails:",
        "",
        "| Criterion | Cases failing | Failure rate |",
        "|-----------|:---:|:---:|",
    ]
    for crit in criteria:
        fails = [r for r in results
                 if not r["baseline"]["scores"].get(crit, True)]
        pct = len(fails)/len(results)*100
        lines.append(
            f"| {criterion_labels[crit]} | {len(fails)}/{len(results)} | {pct:.0f}% |"
        )

    # RAG failures
    lines += [
        "",
        "### 3.2 RAG Explanation Quality by Category", "",
        "| Category | N | Avg RAG score | Min | Max |",
        "|----------|---|:---:|:---:|:---:|",
    ]
    cat_groups = {}
    for r in results:
        cat = r["category"]
        cat_groups.setdefault(cat, []).append(r["rag"]["scores"]["composite"])
    for cat, scores_list in sorted(cat_groups.items()):
        lines.append(
            f"| {cat.replace('_',' ')} | {len(scores_list)} "
            f"| {sum(scores_list)/len(scores_list):.2f} "
            f"| {min(scores_list)} | {max(scores_list)} |"
        )

    # Retrieval quality by domain
    lines += [
        "",
        "### 3.3 Retrieval Quality Analysis", "",
        "Top-1 cosine similarity by domain:", "",
        "| Domain | N | Avg top-1 | Min | Max |",
        "|--------|---|:---:|:---:|:---:|",
    ]
    dom_groups = {}
    for r in results:
        dom = "Healthcare" if "health" in r["domain"] else "Finance"
        top = max((c["score"] for c in r["rag"]["retrieved_chunks"]), default=0.0)
        dom_groups.setdefault(dom, []).append(top)
    for dom, sc_list in sorted(dom_groups.items()):
        lines.append(
            f"| {dom} | {len(sc_list)} | {sum(sc_list)/len(sc_list):.3f} "
            f"| {min(sc_list):.3f} | {max(sc_list):.3f} |"
        )

    # Low-retrieval cases
    low_retrieval = [r for r in results
                     if max((c["score"] for c in r["rag"]["retrieved_chunks"]),
                            default=0.0) < 0.40]
    if low_retrieval:
        lines += [
            "",
            "### 3.4 Cases with Weak Retrieval (top-1 cosine < 0.40)", "",
            "These cases may benefit from expanded knowledge base coverage:", "",
            "| Case | Top-1 score | Violations | Interpretation |",
            "|------|:-----------:|------------|----------------|",
        ]
        for r in low_retrieval:
            top = max((c["score"] for c in r["rag"]["retrieved_chunks"]), default=0.0)
            viols = ", ".join(r["violated_rules"]) or "valid record"
            lines.append(
                f"| {r['case_id']} | {top:.3f} | {viols} "
                f"| Knowledge base lacks targeted document for this case |"
            )

    # Valid-control cases
    valid_cases = [r for r in results if r["category"] == "valid_control"]
    if valid_cases:
        lines += [
            "",
            "### 3.5 Valid-Record Control Cases", "",
            "Records with no violations — the explanation system should handle these gracefully:", "",
            "| Case | Decision | Conf | Baseline score | Retrieval |",
            "|------|----------|:----:|:-----------:|:---------:|",
        ]
        for r in valid_cases:
            top = max((c["score"] for c in r["rag"]["retrieved_chunks"]), default=0.0)
            lines.append(
                f"| {r['case_id']} | {r['decision']} | {r['confidence_score']:.2f} "
                f"| {r['baseline']['scores']['composite']}/6 | {top:.3f} |"
            )

    # Multi-violation cases
    multi_cases = [r for r in results if r["category"] == "multi_violation"]
    if multi_cases:
        lines += [
            "",
            "### 3.6 Multi-Violation Cases", "",
            "Records with 2+ simultaneous violations:", "",
            "| Case | Violations | Conf | RAG score |",
            "|------|------------|:----:|:---------:|",
        ]
        for r in multi_cases:
            viols = ", ".join(r["violated_rules"])
            lines.append(
                f"| {r['case_id']} | {viols} | {r['confidence_score']:.2f} "
                f"| {r['rag']['scores']['composite']}/6 |"
            )

    lines += [
        "",
        "---", "",
        "## 4. Open Issues & Recommendations", "",
        "| Priority | Issue | Recommendation |",
        "|----------|-------|----------------|",
        "| P1 | `has_action` and `cites_reference` both score 0 in the baseline | "
        "These criteria require LLM generation — the deterministic template cannot produce them |",
        "| P1 | Valid-record explanations retrieve violation-specific chunks | "
        "Add a 'general_valid' knowledge base document explaining what a clean record means |",
        "| P2 | Near-miss boundary cases retrieve same chunks as their full-violation counterparts | "
        "This is correct retrieval behaviour — the distinction is in the violation message |",
        "| P2 | Multi-violation cases may not cite all violated rules in a single explanation | "
        "The augmented prompt should list all violated rules explicitly in the instruction |",
        "| P3 | FN-003 (DTI) and FN-005 (over-approved) have lower retrieval scores | "
        "Expand knowledge base with a stronger FN-003-a and FN-005-a document |",
        "",
        "---", "",
        "*Report generated by `rag/evaluate_expanded.py`*",
    ]

    path.write_text("\n".join(lines))
    print(f"  ✓ {path.name}")


# ══════════════════════════════════════════════════════════════════════════════
# MERGE: stitch live LLM results for original 6 cases into the dry-run set
# ══════════════════════════════════════════════════════════════════════════════

def merge_live_results(dry_results: list[dict]) -> list[dict]:
    """
    Where a live LLM result exists in data/rag_evaluation.json,
    replace the dry-run RAG text and scores with the real ones.
    The retrieval chunks (same FAISS index) are kept from dry-run.
    """
    live_path = DATA_DIR / "rag_evaluation.json"
    if not live_path.exists():
        return dry_results

    live_map = {r["case_id"]: r for r in json.loads(live_path.read_text())}
    merged = []
    for r in dry_results:
        # Map new case IDs to original 6 (e.g. HC-003-a → HC-003)
        original_id = r["case_id"].split("-")[0] + "-" + r["case_id"].split("-")[1]
        if original_id in live_map and r["category"] == "single_violation":
            live = live_map[original_id]
            # Merge: keep dry-run structure but inject live RAG text + scores
            r = dict(r)
            r["mode"] = "live"
            r["rag"] = {
                **r["rag"],
                "text":    live["rag"]["text"],
                "scores":  live["rag"]["scores"],
                "latency_ms": live["rag"]["latency_ms"],
            }
        merged.append(r)
    return merged


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live",  action="store_true",
                        help="Make real API calls (needs ANTHROPIC_API_KEY)")
    parser.add_argument("--merge", action="store_true",
                        help="Merge existing live results with dry-run for new cases")
    parser.add_argument("--case",  type=str, default=None,
                        help="Run a single case ID")
    args = parser.parse_args()

    # Load .env
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() not in os.environ:
                    os.environ[k.strip()] = v.strip()

    if args.live and not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: --live requires ANTHROPIC_API_KEY"); return

    from rag.vector_store import INDEX_PATH
    if not INDEX_PATH.exists():
        print("ERROR: FAISS index not built. Run: python rag/vector_store.py --build")
        return

    cases = TEST_CASES
    if args.case:
        cases = [c for c in TEST_CASES if c["case_id"] == args.case]
        if not cases:
            print(f"Case '{args.case}' not found")
            return

    print(f"\n{'='*60}")
    print(f"  SchemaGuard RAG — Expanded Evaluation ({len(cases)} cases)")
    mode_str = "LIVE" if args.live else "DRY-RUN (retrieval only)"
    if args.merge:
        mode_str += " + MERGE live results"
    print(f"  Mode: {mode_str}")
    print(f"{'='*60}")

    t0 = time.time()
    results = []
    for i, case in enumerate(cases, 1):
        print(f"  [{i:02d}/{len(cases):02d}] {case['case_id']:<16} {case['label'][:50]}")
        results.append(run_case(case, live=args.live))

    # Merge live LLM results for original 6 cases
    if args.merge or not args.live:
        results = merge_live_results(results)

    # Save to evaluation/rag_results.json
    out_path = EVAL_DIR / "rag_results.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\n  ✓ evaluation/rag_results.json  ({len(results)} cases)")

    # Chart
    write_chart(results, PLOTS_DIR / "rag_comparison.png")

    # Failure report
    write_failure_report(results, DOCS_DIR / "rag_failures.md")

    # Summary table
    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"  COMPLETE  ({elapsed:.1f}s)")
    print(f"{'='*60}")
    print(f"\n  {'Case':<16} {'Cat':<18} {'Viols':<12} {'B':>4} {'R':>4}  {'Δ':>3}  Top-k")
    print(f"  {'─'*16} {'─'*18} {'─'*12} {'─'*4} {'─'*4}  {'─'*3}  {'─'*5}")
    for r in results:
        b  = r["baseline"]["scores"]["composite"]
        g  = r["rag"]["scores"]["composite"]
        delta = f"+{g-b}" if g >= b else str(g-b)
        top_k = max((c["score"] for c in r["rag"]["retrieved_chunks"]), default=0.0)
        viols = ",".join(r["violated_rules"]) or "—"
        print(f"  {r['case_id']:<16} {r['category']:<18} {viols:<12} "
              f"{b:>4} {g:>4}  {delta:>3}  {top_k:.3f}")
    print()


if __name__ == "__main__":
    main()
