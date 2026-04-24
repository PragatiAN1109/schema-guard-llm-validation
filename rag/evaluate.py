"""
SchemaGuard RAG — Evaluation & Comparison
==========================================
Runs 6 representative test cases (3 healthcare + 3 finance), generates
baseline and RAG explanations for each, and saves structured comparison output.

Usage:
    python rag/evaluate.py                 # full eval (requires API key)
    python rag/evaluate.py --dry-run       # show retrieval only, no LLM call
    python rag/evaluate.py --case HC-003   # single case

Output:
    data/rag_evaluation.json              — structured results
    data/rag_evaluation_samples.md        — human-readable comparison report
    outputs/plots/rag_comparison.png      — chart: explanation length + retrieval scores
"""

from __future__ import annotations
import os, sys, json, time, argparse, textwrap
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR  = PROJECT_ROOT / "data"
PLOTS_DIR = PROJECT_ROOT / "outputs" / "plots"
DATA_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
# TEST CASES — representative failing records for each rule
# ══════════════════════════════════════════════════════════════════════════════

TEST_CASES = [
    {
        "case_id":   "HC-003",
        "domain":    "healthcare_intake",
        "label":     "Discharge before admission",
        "record": {
            "patient_id": "P-4412", "first_name": "Sarah", "last_name": "Mitchell",
            "date_of_birth": "1990-01-20", "gender": "female",
            "admission_date": "2024-08-15", "discharge_date": "2024-08-08",
            "diagnosis_code": "N39.0",
            "diagnosis_description": "Urinary tract infection, site not specified",
            "treating_physician": "Dr. Mark Evans", "medication": "Ciprofloxacin",
            "procedure_code": None, "insurance_provider": "UnitedHealth",
            "patient_age": 34, "emergency_admission": False,
            "notes": "Treated for recurrent UTI.",
        },
    },
    {
        "case_id":   "HC-001",
        "domain":    "healthcare_intake",
        "label":     "Age mismatch (stated vs computed)",
        "record": {
            "patient_id": "P-7203", "first_name": "David", "last_name": "Kim",
            "date_of_birth": "1990-04-10", "gender": "male",
            "admission_date": "2024-11-03", "discharge_date": "2024-11-06",
            "diagnosis_code": "K21.0",
            "diagnosis_description": "Gastro-oesophageal reflux disease with oesophagitis",
            "treating_physician": "Dr. Angela Ruiz", "medication": "Omeprazole",
            "procedure_code": None, "insurance_provider": "Cigna",
            "patient_age": 52,   # actual computed age = 34
            "emergency_admission": False, "notes": None,
        },
    },
    {
        "case_id":   "HC-004",
        "domain":    "healthcare_intake",
        "label":     "Age-inappropriate diagnosis (paediatric + adult-only code)",
        "record": {
            "patient_id": "P-1187", "first_name": "Lily", "last_name": "Thompson",
            "date_of_birth": "2019-02-14", "gender": "female",
            "admission_date": "2024-06-20", "discharge_date": "2024-06-21",
            "diagnosis_code": "M81.0",
            "diagnosis_description": "Age-related osteoporosis without current pathological fracture",
            "treating_physician": "Dr. James Wu", "medication": "Alendronate",
            "procedure_code": None, "insurance_provider": "BlueCross",
            "patient_age": 5, "emergency_admission": False, "notes": None,
        },
    },
    {
        "case_id":   "FN-002",
        "domain":    "financial_loan_application",
        "label":     "Extreme loan-to-income ratio (52×)",
        "record": {
            "application_id": "LA-33190", "applicant_name": "Jessica Williams",
            "date_of_birth": "1991-06-18", "annual_income": 48000,
            "employment_status": "employed", "employer_name": "Target",
            "employment_length_years": 3, "loan_amount": 2500000,
            "loan_purpose": "home_purchase", "loan_term_months": 360,
            "interest_rate": 6.5, "credit_score": 680, "existing_debt": 15000,
            "application_date": "2024-05-12", "approval_date": None,
            "approved_amount": None, "property_value": 2600000,
            "co_applicant": False, "notes": None,
        },
    },
    {
        "case_id":   "FN-001",
        "domain":    "financial_loan_application",
        "label":     "Approval date before application date",
        "record": {
            "application_id": "LA-78412", "applicant_name": "Robert Chen",
            "date_of_birth": "1982-09-05", "annual_income": 78000,
            "employment_status": "employed", "employer_name": "Amazon",
            "employment_length_years": 4, "loan_amount": 45000,
            "loan_purpose": "auto", "loan_term_months": 60,
            "interest_rate": 7.2, "credit_score": 715, "existing_debt": 12000,
            "application_date": "2024-07-20", "approval_date": "2024-06-28",
            "approved_amount": 45000, "property_value": None,
            "co_applicant": False, "notes": None,
        },
    },
    {
        "case_id":   "FN-004",
        "domain":    "financial_loan_application",
        "label":     "Employment length impossible for applicant age",
        "record": {
            "application_id": "LA-90155", "applicant_name": "Tyler Brown",
            "date_of_birth": "2000-02-10", "annual_income": 65000,
            "employment_status": "employed", "employer_name": "Wells Fargo",
            "employment_length_years": 18,  # impossible: age ~24, max = 8 yrs
            "loan_amount": 35000, "loan_purpose": "auto",
            "loan_term_months": 48, "interest_rate": 6.9,
            "credit_score": 705, "existing_debt": 8000,
            "application_date": "2024-11-01", "approval_date": "2024-11-10",
            "approved_amount": 35000, "property_value": None,
            "co_applicant": False, "notes": None,
        },
    },
]

# ══════════════════════════════════════════════════════════════════════════════
# METRICS
# ══════════════════════════════════════════════════════════════════════════════

def score_explanation(text: str, case: dict) -> dict:
    """
    Lightweight qualitative scoring of an explanation (no LLM judge needed).
    Checks for presence of key signals that indicate a good explanation.
    """
    t  = text.lower()
    r  = case["record"]
    ci = case["case_id"]
    domain = case["domain"]

    scores = {}

    # 1. Mentions the violated rule ID
    scores["cites_rule"]       = ci.lower() in t

    # 2. Mentions at least one specific field value from the record
    field_vals = [str(v).lower() for v in r.values() if v is not None]
    scores["cites_field_value"] = any(fv[:6] in t for fv in field_vals if len(fv) > 4)

    # 3. Contains a remediation / action suggestion
    action_words = ["correct", "review", "verify", "update", "reconcil",
                    "check", "investigat", "remediat", "fix", "should be"]
    scores["has_action"]       = any(w in t for w in action_words)

    # 4. References a regulation, standard, or guideline
    ref_words = ["regulation", "cfpb", "cms", "hl7", "fhir", "icd", "jama",
                 "joint commission", "ecoa", "tila", "oms", "fannie", "occ",
                 "guideline", "standard", "policy", "requirement", "per ",
                 "under ", "section", "§", "mandate"]
    scores["cites_reference"]  = any(w in t for w in ref_words)

    # 5. Appropriate length (not too short, not bloated)
    wc = len(text.split())
    scores["word_count"]       = wc
    scores["length_ok"]        = 40 <= wc <= 300

    # 6. Explains WHY it matters (clinical/regulatory consequence)
    why_words = ["risk", "error", "reject", "deny", "bias", "safety",
                 "billing", "compli", "downstream", "impact", "consequen",
                 "fraud", "violat", "audit", "claim"]
    scores["explains_impact"]  = any(w in t for w in why_words)

    # Composite score 0-6
    binary = [v for k, v in scores.items() if k != "word_count" and isinstance(v, bool)]
    scores["composite"]        = sum(binary)
    scores["composite_max"]    = len(binary)

    return scores


# ══════════════════════════════════════════════════════════════════════════════
# SINGLE-CASE RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def run_case(case: dict, dry_run: bool = False) -> dict:
    from validator.pipeline import validate_record
    from rag.explainer import explain_with_rag, explain_baseline

    print(f"\n  Case {case['case_id']}: {case['label']}")

    # 1. Validate
    val = validate_record(case["record"], case["domain"],
                          record_id=f"eval-{case['case_id']}")
    violations = val.get("violated_rules", [])
    decision   = val["decision"]
    confidence = val["confidence_score"]

    print(f"    decision={decision}  confidence={confidence}  violations={[v['rule_id'] for v in violations]}")

    # 2. Baseline explanation
    baseline = explain_baseline(
        case["record"], case["domain"], violations, decision,
        record_id=f"eval-{case['case_id']}"
    )

    # 3. RAG explanation
    try:
        rag_result = explain_with_rag(
            record     = case["record"],
            domain     = case["domain"],
            violations = violations,
            decision   = decision,
            record_id  = f"eval-{case['case_id']}",
            top_k      = 3,
            dry_run    = dry_run,
        )
        rag_text       = rag_result.rag_explanation
        retrieved      = [
            {
                "chunk_id": c.chunk_id,
                "rule_id":  c.rule_id,
                "title":    c.title,
                "source":   c.source,
                "score":    round(c.score, 4),
                "preview":  c.text[:200],
            }
            for c in rag_result.retrieved_chunks
        ]
        latency_ms     = rag_result.latency_ms
        retrieval_query = rag_result.retrieval_query
    except Exception as e:
        print(f"    [RAG error] {e}")
        rag_text       = f"[RAG error: {e}]"
        retrieved      = []
        latency_ms     = 0
        retrieval_query = ""

    # 4. Score both
    baseline_scores = score_explanation(baseline, case)
    rag_scores      = score_explanation(rag_text, case)

    print(f"    baseline  : {baseline_scores['composite']}/{baseline_scores['composite_max']}  ({baseline_scores['word_count']} words)")
    print(f"    rag       : {rag_scores['composite']}/{rag_scores['composite_max']}  ({rag_scores['word_count']} words)")

    return {
        "case_id":          case["case_id"],
        "domain":           case["domain"],
        "label":            case["label"],
        "decision":         decision,
        "confidence_score": confidence,
        "violated_rules":   [v["rule_id"] for v in violations],
        "baseline": {
            "text":   baseline,
            "scores": baseline_scores,
        },
        "rag": {
            "text":            rag_text,
            "scores":          rag_scores,
            "retrieved_chunks": retrieved,
            "retrieval_query": retrieval_query,
            "latency_ms":      latency_ms,
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# REPORT WRITER
# ══════════════════════════════════════════════════════════════════════════════

def write_markdown_report(results: list[dict], path: Path) -> None:
    lines = [
        "# SchemaGuard RAG — Explanation Comparison Report",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
        f"Cases evaluated: {len(results)}",
        "",
        "---",
        "",
        "## Summary Table",
        "",
        "| Case | Domain | Violation | Decision | Baseline Score | RAG Score | "
        "Baseline Words | RAG Words | RAG Latency |",
        "|------|--------|-----------|----------|---------------|-----------|"
        "---------------|-----------|-------------|",
    ]

    for r in results:
        bs = r["baseline"]["scores"]
        rs = r["rag"]["scores"]
        lines.append(
            f"| {r['case_id']} | {'HC' if 'health' in r['domain'] else 'FN'} "
            f"| {r['label'][:35]} | {r['decision']} "
            f"| {bs['composite']}/{bs['composite_max']} "
            f"| {rs['composite']}/{rs['composite_max']} "
            f"| {bs['word_count']} "
            f"| {rs['word_count']} "
            f"| {r['rag']['latency_ms']:.0f} ms |"
        )

    lines += ["", "---", ""]

    # Scoring rubric
    lines += [
        "## Scoring Rubric",
        "",
        "Each explanation is scored 0–6 on these binary criteria:",
        "",
        "| # | Criterion | What it checks |",
        "|---|-----------|----------------|",
        "| 1 | **Cites rule ID** | Mentions the rule ID (e.g. HC-003) |",
        "| 2 | **Cites field value** | References specific data from the record |",
        "| 3 | **Has action** | Includes a remediation/correction suggestion |",
        "| 4 | **Cites reference** | Mentions a regulation, standard, or guideline |",
        "| 5 | **Length OK** | 40–300 words (not too brief, not bloated) |",
        "| 6 | **Explains impact** | States clinical or regulatory consequence |",
        "",
        "---",
        "",
    ]

    # Per-case detail
    for r in results:
        lines += [
            f"## Case {r['case_id']} — {r['label']}",
            "",
            f"**Domain:** {r['domain']}  |  "
            f"**Decision:** {r['decision']}  |  "
            f"**Confidence:** {r['confidence_score']}  |  "
            f"**Violated rules:** {', '.join(r['violated_rules'])}",
            "",
            "### Retrieved Context",
            "",
        ]
        for i, chunk in enumerate(r["rag"]["retrieved_chunks"], 1):
            lines += [
                f"**{i}. [{chunk['rule_id']}] {chunk['title']}**  ",
                f"*{chunk['source']}*  |  score: {chunk['score']:.4f}",
                "",
                f"> {chunk['preview']}…",
                "",
            ]

        bs = r["baseline"]["scores"]
        rs = r["rag"]["scores"]

        def _score_row(scores):
            return (
                f"cites_rule={scores['cites_rule']}  "
                f"cites_value={scores['cites_field_value']}  "
                f"has_action={scores['has_action']}  "
                f"cites_ref={scores['cites_reference']}  "
                f"length_ok={scores['length_ok']}  "
                f"explains_impact={scores['explains_impact']}  "
                f"→ **{scores['composite']}/6**"
            )

        lines += [
            "### Baseline Explanation",
            f"*Score: {_score_row(bs)}  |  {bs['word_count']} words*",
            "",
            f"> {r['baseline']['text']}",
            "",
            "### RAG Explanation",
            f"*Score: {_score_row(rs)}  |  {rs['word_count']} words  |  "
            f"latency: {r['rag']['latency_ms']:.0f} ms*",
            "",
        ]
        # wrap long rag text for markdown readability
        for para in r["rag"]["text"].split("\n\n"):
            lines.append(para.strip())
            lines.append("")

        lines += ["---", ""]

    path.write_text("\n".join(lines))
    print(f"  Saved: {path}")


def write_chart(results: list[dict], path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("  [skip chart] matplotlib not available")
        return

    plt.rcParams.update({
        "figure.facecolor": "#0d1117", "axes.facecolor": "#161b22",
        "axes.edgecolor": "#30363d", "axes.labelcolor": "#c9d1d9",
        "xtick.color": "#8b949e", "ytick.color": "#8b949e",
        "text.color": "#c9d1d9", "grid.color": "#21262d",
        "grid.linestyle": "--", "grid.alpha": 0.5,
    })
    BLUE, GREEN, RED, YELLOW = "#58a6ff", "#238636", "#da3633", "#d29922"

    case_ids      = [r["case_id"] for r in results]
    base_scores   = [r["baseline"]["scores"]["composite"] for r in results]
    rag_scores    = [r["rag"]["scores"]["composite"]      for r in results]
    base_words    = [r["baseline"]["scores"]["word_count"] for r in results]
    rag_words     = [r["rag"]["scores"]["word_count"]      for r in results]
    top_scores    = [
        max((c["score"] for c in r["rag"]["retrieved_chunks"]), default=0)
        for r in results
    ]
    latencies     = [r["rag"]["latency_ms"] / 1000 for r in results]

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.suptitle("SchemaGuard RAG — Explanation Quality Comparison", fontsize=14,
                 color=BLUE, y=1.01)

    x = np.arange(len(case_ids))
    w = 0.35

    # 1. Composite score comparison
    ax = axes[0][0]
    b1 = ax.bar(x - w/2, base_scores, w, label="Baseline", color=YELLOW, alpha=0.85, zorder=3)
    b2 = ax.bar(x + w/2, rag_scores,  w, label="RAG",      color=BLUE,   alpha=0.85, zorder=3)
    ax.set_title("Explanation Quality Score (0–6)", color="#c9d1d9", fontsize=11)
    ax.set_xticks(x); ax.set_xticklabels(case_ids, fontsize=9)
    ax.set_ylim(0, 7); ax.grid(axis="y", zorder=0)
    ax.legend(facecolor="#21262d", edgecolor="#30363d", labelcolor="#c9d1d9", fontsize=9)
    for bar in list(b1)+list(b2):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.05,
                str(int(bar.get_height())), ha="center", fontsize=9, color="#c9d1d9")

    # 2. Word count comparison
    ax = axes[0][1]
    ax.bar(x - w/2, base_words, w, label="Baseline", color=YELLOW, alpha=0.85, zorder=3)
    ax.bar(x + w/2, rag_words,  w, label="RAG",      color=BLUE,   alpha=0.85, zorder=3)
    ax.set_title("Explanation Length (words)", color="#c9d1d9", fontsize=11)
    ax.set_xticks(x); ax.set_xticklabels(case_ids, fontsize=9)
    ax.grid(axis="y", zorder=0)
    ax.legend(facecolor="#21262d", edgecolor="#30363d", labelcolor="#c9d1d9", fontsize=9)

    # 3. Top retrieval score per case
    ax = axes[1][0]
    colors_r = [GREEN if s > 0.5 else YELLOW if s > 0.35 else RED for s in top_scores]
    bars = ax.bar(case_ids, top_scores, color=colors_r, alpha=0.85, zorder=3)
    ax.axhline(0.5, color=GREEN,  linestyle="--", linewidth=1.2, label="Good (0.5+)")
    ax.axhline(0.35, color=YELLOW, linestyle="--", linewidth=1.2, label="Fair (0.35+)")
    ax.set_title("Top Retrieval Score (cosine)", color="#c9d1d9", fontsize=11)
    ax.set_ylim(0, 1); ax.grid(axis="y", zorder=0)
    ax.legend(facecolor="#21262d", edgecolor="#30363d", labelcolor="#c9d1d9", fontsize=9)
    for bar, s in zip(bars, top_scores):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.01,
                f"{s:.3f}", ha="center", fontsize=9, color="#c9d1d9")

    # 4. RAG latency
    ax = axes[1][1]
    colors_l = [GREEN if l < 3 else YELLOW if l < 6 else RED for l in latencies]
    bars = ax.bar(case_ids, latencies, color=colors_l, alpha=0.85, zorder=3)
    ax.set_title("RAG End-to-End Latency (seconds)", color="#c9d1d9", fontsize=11)
    ax.grid(axis="y", zorder=0)
    for bar, l in zip(bars, latencies):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.05,
                f"{l:.1f}s", ha="center", fontsize=9, color="#c9d1d9")

    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#0d1117")
    plt.close()
    print(f"  Saved: {path}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="SchemaGuard RAG Evaluation")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show retrieval only — no API calls")
    parser.add_argument("--case", type=str, default=None,
                        help="Run a single case (e.g. --case HC-003)")
    args = parser.parse_args()

    if not args.dry_run and not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set. Use --dry-run or export the key.")
        sys.exit(1)

    # Check FAISS index
    from rag.vector_store import INDEX_PATH
    if not INDEX_PATH.exists():
        print("ERROR: FAISS index not built. Run: python rag/vector_store.py --build")
        sys.exit(1)

    cases = TEST_CASES
    if args.case:
        cases = [c for c in TEST_CASES if c["case_id"] == args.case]
        if not cases:
            print(f"ERROR: case '{args.case}' not found. Available: {[c['case_id'] for c in TEST_CASES]}")
            sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  SchemaGuard RAG Evaluation")
    if args.dry_run:
        print(f"  Mode: DRY RUN (retrieval only, no LLM calls)")
    print(f"  Cases: {len(cases)}")
    print(f"{'='*60}")

    t0 = time.time()
    results = []
    for case in cases:
        result = run_case(case, dry_run=args.dry_run)
        results.append(result)

    # Save JSON
    json_path = DATA_DIR / "rag_evaluation.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved: {json_path}")

    # Save markdown report
    md_path = DATA_DIR / "rag_evaluation_samples.md"
    write_markdown_report(results, md_path)

    # Save chart
    chart_path = PLOTS_DIR / "rag_comparison.png"
    write_chart(results, chart_path)

    # Summary
    print(f"\n{'='*60}")
    print(f"  EVALUATION COMPLETE  ({time.time()-t0:.1f}s)")
    print(f"{'='*60}\n")
    print(f"  {'Case':<8} {'Baseline':>10} {'RAG':>10} {'Δ':>5}  {'Words (B→R)':>14}")
    print(f"  {'─'*8} {'─'*10} {'─'*10} {'─'*5}  {'─'*14}")
    for r in results:
        b = r["baseline"]["scores"]["composite"]
        g = r["rag"]["scores"]["composite"]
        bw = r["baseline"]["scores"]["word_count"]
        rw = r["rag"]["scores"]["word_count"]
        delta = f"+{g-b}" if g >= b else str(g-b)
        print(f"  {r['case_id']:<8} {b:>7}/6     {g:>7}/6  {delta:>5}  {bw:>5} → {rw:<5}")

    print()


if __name__ == "__main__":
    main()

# ══════════════════════════════════════════════════════════════════════════════
# METRICS
# ══════════════════════════════════════════════════════════════════════════════

def score_explanation(text: str, case: dict) -> dict:
    """Lightweight qualitative scoring — no LLM judge needed."""
    t  = text.lower()
    r  = case["record"]
    ci = case["case_id"]

    scores = {}
    scores["cites_rule"]        = ci.lower() in t
    field_vals = [str(v).lower() for v in r.values() if v is not None]
    scores["cites_field_value"] = any(fv[:6] in t for fv in field_vals if len(fv) > 4)
    action_words = ["correct","review","verify","update","reconcil",
                    "check","investigat","remediat","fix","should be","must be"]
    scores["has_action"]        = any(w in t for w in action_words)
    ref_words = ["regulation","cfpb","cms","hl7","fhir","icd","jama","joint commission",
                 "ecoa","tila","fannie","occ","guideline","standard","policy",
                 "requirement","per ","under ","section","§","mandate","act","rule"]
    scores["cites_reference"]   = any(w in t for w in ref_words)
    wc = len(text.split())
    scores["word_count"]        = wc
    scores["length_ok"]         = 40 <= wc <= 350
    why_words = ["risk","error","reject","deny","bias","safety","billing","compli",
                 "downstream","impact","consequen","fraud","violat","audit","claim",
                 "patient","legal","regulat"]
    scores["explains_impact"]   = any(w in t for w in why_words)

    binary = [v for k, v in scores.items() if k != "word_count" and isinstance(v, bool)]
    scores["composite"]     = sum(binary)
    scores["composite_max"] = len(binary)
    return scores


# ══════════════════════════════════════════════════════════════════════════════
# SINGLE-CASE RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def run_case(case: dict, dry_run: bool = False) -> dict:
    from validator.pipeline import validate_record
    from rag.explainer import explain_with_rag, explain_baseline

    print(f"\n  Case {case['case_id']}: {case['label']}")

    val        = validate_record(case["record"], case["domain"],
                                 record_id=f"eval-{case['case_id']}")
    violations = val.get("violated_rules", [])
    decision   = val["decision"]
    confidence = val["confidence_score"]

    print(f"    decision={decision}  confidence={confidence}  "
          f"violations={[v['rule_id'] for v in violations]}")

    baseline = explain_baseline(case["record"], case["domain"],
                                violations, decision, record_id=f"eval-{case['case_id']}")

    try:
        rag_result = explain_with_rag(
            record=case["record"], domain=case["domain"],
            violations=violations, decision=decision,
            record_id=f"eval-{case['case_id']}", top_k=3, dry_run=dry_run,
        )
        rag_text        = rag_result.rag_explanation
        retrieved       = [
            {"chunk_id": c.chunk_id, "rule_id": c.rule_id, "title": c.title,
             "source": c.source, "score": round(c.score, 4), "preview": c.text[:200]}
            for c in rag_result.retrieved_chunks
        ]
        latency_ms      = rag_result.latency_ms
        retrieval_query = rag_result.retrieval_query
    except Exception as e:
        print(f"    [RAG error] {e}")
        rag_text = f"[RAG error: {e}]"
        retrieved, latency_ms, retrieval_query = [], 0, ""

    baseline_scores = score_explanation(baseline, case)
    rag_scores      = score_explanation(rag_text,  case)

    print(f"    baseline: {baseline_scores['composite']}/{baseline_scores['composite_max']}  "
          f"({baseline_scores['word_count']} words)")
    print(f"    rag     : {rag_scores['composite']}/{rag_scores['composite_max']}  "
          f"({rag_scores['word_count']} words)")

    return {
        "case_id": case["case_id"], "domain": case["domain"],
        "label": case["label"], "decision": decision,
        "confidence_score": confidence,
        "violated_rules": [v["rule_id"] for v in violations],
        "baseline": {"text": baseline, "scores": baseline_scores},
        "rag":      {"text": rag_text, "scores": rag_scores,
                     "retrieved_chunks": retrieved,
                     "retrieval_query": retrieval_query,
                     "latency_ms": latency_ms},
    }


# ══════════════════════════════════════════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════════════════════════════════════════

def write_markdown_report(results: list[dict], path: Path) -> None:
    lines = [
        "# SchemaGuard RAG — Explanation Comparison Report",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
        f"Cases evaluated: {len(results)}", "",
        "---", "",
        "## Summary Table", "",
        "| Case | Domain | Violation | Decision | Baseline | RAG | Δ | B-words | R-words |",
        "|------|--------|-----------|----------|----------|-----|---|---------|---------|",
    ]
    for r in results:
        bs = r["baseline"]["scores"];  rs = r["rag"]["scores"]
        delta = f"+{rs['composite']-bs['composite']}" if rs['composite'] >= bs['composite'] \
                else str(rs['composite']-bs['composite'])
        lines.append(
            f"| {r['case_id']} "
            f"| {'HC' if 'health' in r['domain'] else 'FN'} "
            f"| {r['label'][:35]} "
            f"| {r['decision']} "
            f"| {bs['composite']}/6 "
            f"| {rs['composite']}/6 "
            f"| {delta} "
            f"| {bs['word_count']} "
            f"| {rs['word_count']} |"
        )

    lines += ["", "---", "",
        "## Scoring Rubric (0–6 binary criteria)", "",
        "| # | Criterion | What it checks |",
        "|---|-----------|----------------|",
        "| 1 | **Cites rule ID** | Mentions the rule ID (e.g. HC-003) |",
        "| 2 | **Cites field value** | References specific data from the record |",
        "| 3 | **Has action** | Includes a remediation / correction suggestion |",
        "| 4 | **Cites reference** | Mentions a regulation, standard, or guideline |",
        "| 5 | **Length OK** | 40–350 words (not too brief, not bloated) |",
        "| 6 | **Explains impact** | States clinical or regulatory consequence |",
        "", "---", "",
    ]

    for r in results:
        bs = r["baseline"]["scores"];  rs = r["rag"]["scores"]

        def _sc(s):
            return (f"cites_rule={s['cites_rule']}  "
                    f"cites_value={s['cites_field_value']}  "
                    f"has_action={s['has_action']}  "
                    f"cites_ref={s['cites_reference']}  "
                    f"length_ok={s['length_ok']}  "
                    f"explains_impact={s['explains_impact']}  "
                    f"→ **{s['composite']}/6**")

        lines += [
            f"## Case {r['case_id']} — {r['label']}", "",
            f"**Domain:** {r['domain']}  |  **Decision:** {r['decision']}  "
            f"|  **Confidence:** {r['confidence_score']}  "
            f"|  **Violated:** {', '.join(r['violated_rules'])}", "",
            "### Retrieved Context", "",
        ]
        for i, ch in enumerate(r["rag"]["retrieved_chunks"], 1):
            lines += [
                f"**{i}. [{ch['rule_id']}] {ch['title']}**  ",
                f"*{ch['source']}*  |  score: {ch['score']:.4f}", "",
                f"> {ch['preview']}…", "",
            ]

        lines += [
            "### Baseline Explanation",
            f"*{_sc(bs)}  |  {bs['word_count']} words*", "",
            f"> {r['baseline']['text']}", "",
            "### RAG-Augmented Explanation",
            f"*{_sc(rs)}  |  {rs['word_count']} words  |  "
            f"latency: {r['rag']['latency_ms']:.0f} ms*", "",
        ]
        for para in r["rag"]["text"].split("\n\n"):
            lines.append(para.strip()); lines.append("")
        lines += ["---", ""]

    path.write_text("\n".join(lines))
    print(f"  Saved: {path}")


def write_chart(results: list[dict], path: Path) -> None:
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("  [skip chart] matplotlib not available"); return

    plt.rcParams.update({
        "figure.facecolor":"#0d1117","axes.facecolor":"#161b22",
        "axes.edgecolor":"#30363d","axes.labelcolor":"#c9d1d9",
        "xtick.color":"#8b949e","ytick.color":"#8b949e",
        "text.color":"#c9d1d9","grid.color":"#21262d",
        "grid.linestyle":"--","grid.alpha":0.5,
    })
    BLUE,GREEN,RED,YELLOW="#58a6ff","#238636","#da3633","#d29922"

    case_ids    = [r["case_id"] for r in results]
    base_scores = [r["baseline"]["scores"]["composite"] for r in results]
    rag_scores  = [r["rag"]["scores"]["composite"]      for r in results]
    base_words  = [r["baseline"]["scores"]["word_count"] for r in results]
    rag_words   = [r["rag"]["scores"]["word_count"]      for r in results]
    top_scores  = [max((c["score"] for c in r["rag"]["retrieved_chunks"]), default=0)
                   for r in results]
    latencies   = [r["rag"]["latency_ms"]/1000 for r in results]

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.suptitle("SchemaGuard RAG — Explanation Quality Comparison",
                 fontsize=14, color=BLUE, y=1.01)
    x = np.arange(len(case_ids)); w = 0.35

    ax = axes[0][0]
    b1 = ax.bar(x-w/2, base_scores, w, label="Baseline", color=YELLOW, alpha=0.85, zorder=3)
    b2 = ax.bar(x+w/2, rag_scores,  w, label="RAG",      color=BLUE,   alpha=0.85, zorder=3)
    ax.set_title("Quality Score (0–6)", color="#c9d1d9", fontsize=11)
    ax.set_xticks(x); ax.set_xticklabels(case_ids, fontsize=9)
    ax.set_ylim(0,7); ax.grid(axis="y",zorder=0)
    ax.legend(facecolor="#21262d",edgecolor="#30363d",labelcolor="#c9d1d9",fontsize=9)
    for bar in list(b1)+list(b2):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.05,
                str(int(bar.get_height())), ha="center", fontsize=9, color="#c9d1d9")

    ax = axes[0][1]
    ax.bar(x-w/2, base_words, w, label="Baseline", color=YELLOW, alpha=0.85, zorder=3)
    ax.bar(x+w/2, rag_words,  w, label="RAG",      color=BLUE,   alpha=0.85, zorder=3)
    ax.set_title("Explanation Length (words)", color="#c9d1d9", fontsize=11)
    ax.set_xticks(x); ax.set_xticklabels(case_ids, fontsize=9)
    ax.grid(axis="y",zorder=0)
    ax.legend(facecolor="#21262d",edgecolor="#30363d",labelcolor="#c9d1d9",fontsize=9)

    ax = axes[1][0]
    colors_r = [GREEN if s>0.5 else YELLOW if s>0.35 else RED for s in top_scores]
    bars = ax.bar(case_ids, top_scores, color=colors_r, alpha=0.85, zorder=3)
    ax.axhline(0.5,  color=GREEN,  linestyle="--", linewidth=1.2, label="Good (0.5+)")
    ax.axhline(0.35, color=YELLOW, linestyle="--", linewidth=1.2, label="Fair (0.35+)")
    ax.set_title("Top Retrieval Score (cosine)", color="#c9d1d9", fontsize=11)
    ax.set_ylim(0,1); ax.grid(axis="y",zorder=0)
    ax.legend(facecolor="#21262d",edgecolor="#30363d",labelcolor="#c9d1d9",fontsize=9)
    for bar, s in zip(bars, top_scores):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.01,
                f"{s:.3f}", ha="center", fontsize=9, color="#c9d1d9")

    ax = axes[1][1]
    colors_l = [GREEN if l<3 else YELLOW if l<6 else RED for l in latencies]
    bars = ax.bar(case_ids, latencies, color=colors_l, alpha=0.85, zorder=3)
    ax.set_title("RAG End-to-End Latency (seconds)", color="#c9d1d9", fontsize=11)
    ax.grid(axis="y",zorder=0)
    for bar, l in zip(bars, latencies):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.05,
                f"{l:.1f}s", ha="center", fontsize=9, color="#c9d1d9")

    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#0d1117")
    plt.close()
    print(f"  Saved: {path}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="SchemaGuard RAG Evaluation")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show retrieval only — no API calls")
    parser.add_argument("--case", type=str, default=None,
                        help="Run a single case (e.g. --case HC-003)")
    args = parser.parse_args()

    # Load .env if present
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() not in os.environ:
                    os.environ[k.strip()] = v.strip()

    if not args.dry_run and not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set.")
        print("  Either: export ANTHROPIC_API_KEY=sk-ant-...")
        print("  Or:     add it to .env and re-run")
        print("  Or:     use --dry-run for retrieval-only mode")
        sys.exit(1)

    from rag.vector_store import INDEX_PATH
    if not INDEX_PATH.exists():
        print("ERROR: FAISS index not built. Run: python rag/vector_store.py --build")
        sys.exit(1)

    cases = TEST_CASES
    if args.case:
        cases = [c for c in TEST_CASES if c["case_id"] == args.case]
        if not cases:
            ids = [c["case_id"] for c in TEST_CASES]
            print(f"ERROR: case '{args.case}' not found. Available: {ids}")
            sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  SchemaGuard RAG Evaluation")
    if args.dry_run:
        print(f"  Mode: DRY RUN (retrieval only)")
    print(f"  Cases: {len(cases)}")
    print(f"{'='*60}")

    t0 = time.time()
    results = []
    for case in cases:
        results.append(run_case(case, dry_run=args.dry_run))

    # Save outputs
    json_path = DATA_DIR / "rag_evaluation.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved: {json_path}")

    write_markdown_report(results, DATA_DIR / "rag_evaluation_samples.md")
    write_chart(results, PLOTS_DIR / "rag_comparison.png")

    # Print summary table
    print(f"\n{'='*60}")
    print(f"  EVALUATION COMPLETE  ({time.time()-t0:.1f}s)")
    print(f"{'='*60}\n")
    print(f"  {'Case':<8} {'Baseline':>10} {'RAG':>10} {'Δ':>5}  {'Words (B→R)':>14}")
    print(f"  {'─'*8} {'─'*10} {'─'*10} {'─'*5}  {'─'*14}")
    for r in results:
        b  = r["baseline"]["scores"]["composite"]
        g  = r["rag"]["scores"]["composite"]
        bw = r["baseline"]["scores"]["word_count"]
        rw = r["rag"]["scores"]["word_count"]
        delta = f"+{g-b}" if g >= b else str(g-b)
        print(f"  {r['case_id']:<8} {b:>7}/6     {g:>7}/6  {delta:>5}  {bw:>5} → {rw:<5}")
    print()


if __name__ == "__main__":
    main()
