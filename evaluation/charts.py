"""
SchemaGuard — Chart Generation

Generates evaluation charts as static HTML with embedded data for the project report.
Uses no external plotting dependencies — produces self-contained HTML charts.

Usage:
    cd schema-guard-llm-validation
    python -m evaluation.charts
"""

import json
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"


def generate_confidence_chart_html(hc_metrics: dict, fn_metrics: dict) -> str:
    """Generate an HTML bar chart comparing confidence scores across domains."""
    hc_valid = hc_metrics.get("mean_confidence_valid", 0) or 0
    hc_invalid = hc_metrics.get("mean_confidence_invalid", 0) or 0
    fn_valid = fn_metrics.get("mean_confidence_valid", 0) or 0
    fn_invalid = fn_metrics.get("mean_confidence_invalid", 0) or 0

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>SchemaGuard — Confidence Separation</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 700px; margin: 40px auto; padding: 20px; background: #0d1117; color: #c9d1d9; }}
h2 {{ color: #58a6ff; margin-bottom: 30px; }}
.chart {{ display: flex; flex-direction: column; gap: 12px; }}
.row {{ display: flex; align-items: center; gap: 12px; }}
.label {{ width: 180px; font-size: 13px; text-align: right; color: #8b949e; }}
.bar-bg {{ flex: 1; height: 28px; background: #21262d; border-radius: 6px; overflow: hidden; position: relative; }}
.bar {{ height: 100%; border-radius: 6px; display: flex; align-items: center; padding-left: 10px; font-size: 12px; font-weight: 600; color: #fff; }}
.bar.green {{ background: #238636; }}
.bar.red {{ background: #da3633; }}
.bar.yellow {{ background: #d29922; }}
.legend {{ margin-top: 20px; font-size: 12px; color: #8b949e; }}
</style></head><body>
<h2>Confidence Score Separation</h2>
<div class="chart">
  <div class="row"><span class="label">HC Valid</span><div class="bar-bg"><div class="bar green" style="width:{hc_valid*100:.0f}%">{hc_valid:.2f}</div></div></div>
  <div class="row"><span class="label">HC Invalid</span><div class="bar-bg"><div class="bar red" style="width:{hc_invalid*100:.0f}%">{hc_invalid:.2f}</div></div></div>
  <div class="row"><span class="label">FN Valid</span><div class="bar-bg"><div class="bar green" style="width:{fn_valid*100:.0f}%">{fn_valid:.2f}</div></div></div>
  <div class="row"><span class="label">FN Invalid</span><div class="bar-bg"><div class="bar red" style="width:{fn_invalid*100:.0f}%">{fn_invalid:.2f}</div></div></div>
</div>
<div class="legend">Higher = more confident the record is valid. Wide gap = good separation between valid and invalid records.</div>
</body></html>"""


def generate_metrics_table_html(hc_metrics: dict, fn_metrics: dict) -> str:
    """Generate an HTML metrics comparison table."""
    def row(label, hc_val, fn_val, fmt=".4f"):
        hc = f"{hc_val:{fmt}}" if hc_val is not None else "—"
        fn = f"{fn_val:{fmt}}" if fn_val is not None else "—"
        return f"<tr><td>{label}</td><td>{hc}</td><td>{fn}</td></tr>"

    rows = "\n".join([
        row("Precision", hc_metrics["precision"], fn_metrics["precision"]),
        row("Recall", hc_metrics["recall"], fn_metrics["recall"]),
        row("F1 Score", hc_metrics["f1_score"], fn_metrics["f1_score"]),
        row("Accuracy", hc_metrics["accuracy"], fn_metrics["accuracy"]),
        row("False Quarantine Rate", hc_metrics["false_quarantine_rate"], fn_metrics["false_quarantine_rate"]),
        row("Mean Conf (valid)", hc_metrics["mean_confidence_valid"], fn_metrics["mean_confidence_valid"]),
        row("Mean Conf (invalid)", hc_metrics["mean_confidence_invalid"], fn_metrics["mean_confidence_invalid"]),
    ])

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>SchemaGuard — Evaluation Metrics</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 700px; margin: 40px auto; padding: 20px; background: #0d1117; color: #c9d1d9; }}
h2 {{ color: #58a6ff; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
th, td {{ padding: 10px 16px; text-align: left; border-bottom: 1px solid #21262d; }}
th {{ color: #58a6ff; font-size: 13px; text-transform: uppercase; }}
td {{ font-size: 14px; font-family: monospace; }}
tr:hover {{ background: #161b22; }}
</style></head><body>
<h2>Evaluation Metrics</h2>
<table>
<tr><th>Metric</th><th>Healthcare</th><th>Finance</th></tr>
{rows}
</table>
</body></html>"""


def generate_decision_distribution_html(hc_results: list, fn_results: list) -> str:
    """Generate an HTML chart showing decision distribution per domain."""
    def counts(results):
        t = sum(1 for r in results if r["decision"] == "trusted")
        f = sum(1 for r in results if r["decision"] == "flagged")
        q = sum(1 for r in results if r["decision"] == "quarantined")
        return t, f, q

    hc_t, hc_f, hc_q = counts(hc_results)
    fn_t, fn_f, fn_q = counts(fn_results)
    hc_n = len(hc_results)
    fn_n = len(fn_results)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>SchemaGuard — Decision Distribution</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 700px; margin: 40px auto; padding: 20px; background: #0d1117; color: #c9d1d9; }}
h2 {{ color: #58a6ff; margin-bottom: 30px; }}
.domain {{ margin-bottom: 30px; }}
.domain-label {{ font-size: 14px; color: #8b949e; margin-bottom: 8px; }}
.stacked {{ display: flex; height: 36px; border-radius: 8px; overflow: hidden; }}
.seg {{ display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; color: white; }}
.seg.trusted {{ background: #238636; }}
.seg.flagged {{ background: #d29922; }}
.seg.quarantined {{ background: #da3633; }}
.legend {{ display: flex; gap: 20px; margin-top: 20px; font-size: 12px; }}
.legend span {{ display: flex; align-items: center; gap: 6px; }}
.dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
</style></head><body>
<h2>Decision Distribution</h2>
<div class="domain">
  <div class="domain-label">Healthcare ({hc_n} records)</div>
  <div class="stacked">
    <div class="seg trusted" style="width:{hc_t/hc_n*100:.0f}%">{hc_t} trusted</div>
    <div class="seg flagged" style="width:{hc_f/hc_n*100:.0f}%">{hc_f} flagged</div>
    <div class="seg quarantined" style="width:{hc_q/hc_n*100:.0f}%">{hc_q} quarantined</div>
  </div>
</div>
<div class="domain">
  <div class="domain-label">Finance ({fn_n} records)</div>
  <div class="stacked">
    <div class="seg trusted" style="width:{fn_t/fn_n*100:.0f}%">{fn_t} trusted</div>
    <div class="seg flagged" style="width:{fn_f/fn_n*100:.0f}%">{fn_f} flagged</div>
    <div class="seg quarantined" style="width:{fn_q/fn_n*100:.0f}%">{fn_q} quarantined</div>
  </div>
</div>
<div class="legend">
  <span><span class="dot" style="background:#238636"></span> Trusted</span>
  <span><span class="dot" style="background:#d29922"></span> Flagged</span>
  <span><span class="dot" style="background:#da3633"></span> Quarantined</span>
</div>
</body></html>"""


def save_charts(hc_metrics, fn_metrics, hc_results, fn_results):
    """Generate and save all chart HTML files."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Confidence separation
    html = generate_confidence_chart_html(hc_metrics, fn_metrics)
    path = RESULTS_DIR / "confidence_separation.html"
    with open(path, "w") as f:
        f.write(html)
    print(f"  Saved: {path}")

    # Metrics table
    html = generate_metrics_table_html(hc_metrics, fn_metrics)
    path = RESULTS_DIR / "metrics_table.html"
    with open(path, "w") as f:
        f.write(html)
    print(f"  Saved: {path}")

    # Decision distribution
    html = generate_decision_distribution_html(hc_results, fn_results)
    path = RESULTS_DIR / "decision_distribution.html"
    with open(path, "w") as f:
        f.write(html)
    print(f"  Saved: {path}")
