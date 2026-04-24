"""
SchemaGuard — Plot Generator
Run from project root: python outputs/generate_plots.py
Produces all evaluation PNGs into outputs/plots/
"""

import os
import sys

# Make sure we can import from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PLOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

# ── Shared style ──────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor": "#0d1117",
    "axes.facecolor":   "#161b22",
    "axes.edgecolor":   "#30363d",
    "axes.labelcolor":  "#c9d1d9",
    "xtick.color":      "#8b949e",
    "ytick.color":      "#8b949e",
    "text.color":       "#c9d1d9",
    "grid.color":       "#21262d",
    "grid.linestyle":   "--",
    "grid.alpha":       0.5,
    "font.family":      "DejaVu Sans",
    "font.size":        11,
})

GREEN  = "#238636"
YELLOW = "#d29922"
RED    = "#da3633"
BLUE   = "#58a6ff"
PURPLE = "#8957e5"

# ── Data ──────────────────────────────────────────────────────────────────────
hc_valid_scores   = [1.0, 1.0, 1.0, 1.0, 1.0]
hc_invalid_scores = [0.70, 0.76, 0.76]
fn_valid_scores   = [1.0, 1.0, 1.0, 1.0, 1.0]
fn_invalid_scores = [0.70, 0.70, 0.70]

hc_decisions = {"trusted": 5, "flagged": 0, "quarantined": 3}
fn_decisions = {"trusted": 5, "flagged": 0, "quarantined": 3}

rules_hc = ["HC-001\nAge Match", "HC-002\nAdmit>DOB", "HC-003\nDischarge>Admit", "HC-004\nAge-Diag", "HC-005\nMed-Diag"]
rules_fn = ["FN-001\nApproval Date", "FN-002\nLoan:Income", "FN-003\nDebt:Income", "FN-004\nEmploy Age", "FN-005\nApproved≤Req"]
trigger_counts_hc = [1, 0, 1, 1, 0]
trigger_counts_fn = [1, 1, 0, 1, 0]


# 1. confidence_distribution.png
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle("Confidence Score Distribution — Valid vs Invalid Records", fontsize=14, color=BLUE, y=1.01)
for ax, valid, invalid, title in [
    (axes[0], hc_valid_scores, hc_invalid_scores, "Healthcare Intake"),
    (axes[1], fn_valid_scores, fn_invalid_scores, "Financial Loan"),
]:
    x = list(range(len(valid) + len(invalid)))
    ax.bar(x[:len(valid)], valid,   color=GREEN, alpha=0.85, label="Valid / Edge-case", zorder=3)
    ax.bar(x[len(valid):], invalid, color=RED,   alpha=0.85, label="Invalid",           zorder=3)
    ax.axhline(0.85, color=GREEN,  linestyle="--", linewidth=1.2, alpha=0.8, label="Trusted (0.85)")
    ax.axhline(0.50, color=YELLOW, linestyle="--", linewidth=1.2, alpha=0.8, label="Flagged (0.50)")
    ax.set_title(title, color="#c9d1d9", fontsize=12)
    ax.set_xlabel("Record Index", fontsize=10)
    ax.set_ylabel("Confidence Score", fontsize=10)
    ax.set_ylim(0, 1.12)
    ax.set_xticks(x)
    ax.grid(axis="y", zorder=0)
    ax.legend(fontsize=9, facecolor="#21262d", edgecolor="#30363d", labelcolor="#c9d1d9")
plt.tight_layout()
plt.savefig(f"{PLOTS_DIR}/confidence_distribution.png", dpi=150, bbox_inches="tight", facecolor="#0d1117")
plt.close()
print("✓ confidence_distribution.png")


# 2. metrics_comparison.png
metrics = ["Precision", "Recall", "F1 Score", "Accuracy"]
hc_vals = [1.0, 1.0, 1.0, 1.0]
fn_vals = [1.0, 1.0, 1.0, 1.0]
x = np.arange(len(metrics))
w = 0.35
fig, ax = plt.subplots(figsize=(10, 5))
fig.patch.set_facecolor("#0d1117")
b1 = ax.bar(x - w/2, hc_vals, w, label="Healthcare",  color=BLUE,   alpha=0.85, zorder=3)
b2 = ax.bar(x + w/2, fn_vals, w, label="Finance",     color=PURPLE, alpha=0.85, zorder=3)
ax.set_title("Evaluation Metrics — Healthcare vs Finance", color=BLUE, fontsize=14)
ax.set_xticks(x); ax.set_xticklabels(metrics, fontsize=12)
ax.set_ylim(0, 1.25); ax.set_ylabel("Score", fontsize=11)
ax.grid(axis="y", zorder=0)
ax.legend(fontsize=11, facecolor="#21262d", edgecolor="#30363d", labelcolor="#c9d1d9")
for bar in list(b1) + list(b2):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
            f"{bar.get_height():.2f}", ha="center", va="bottom", fontsize=10, color="#c9d1d9")
plt.tight_layout()
plt.savefig(f"{PLOTS_DIR}/metrics_comparison.png", dpi=150, bbox_inches="tight", facecolor="#0d1117")
plt.close()
print("✓ metrics_comparison.png")


# 3. decision_distribution.png
fig, axes = plt.subplots(1, 2, figsize=(10, 5))
fig.suptitle("Decision Distribution per Domain", fontsize=14, color=BLUE)
for ax, decisions, title in [
    (axes[0], hc_decisions, "Healthcare Intake"),
    (axes[1], fn_decisions, "Financial Loan"),
]:
    labels = list(decisions.keys())
    sizes  = list(decisions.values())
    colors_pie = [GREEN, YELLOW, RED]
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct="%1.0f%%",
        colors=colors_pie, explode=(0.04, 0.04, 0.06), startangle=90,
        textprops={"color": "#c9d1d9", "fontsize": 11},
        wedgeprops={"edgecolor": "#0d1117", "linewidth": 2},
    )
    for at in autotexts:
        at.set_color("#ffffff"); at.set_fontweight("bold")
    ax.set_title(title, color="#c9d1d9", fontsize=12)
plt.tight_layout()
plt.savefig(f"{PLOTS_DIR}/decision_distribution.png", dpi=150, bbox_inches="tight", facecolor="#0d1117")
plt.close()
print("✓ decision_distribution.png")


# 4. rule_violation_frequency.png
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
fig.suptitle("Rule Trigger Frequency (Seed Dataset)", fontsize=14, color=BLUE)
for ax, rules, counts, title in [
    (axes[0], rules_hc, trigger_counts_hc, "Healthcare Rules"),
    (axes[1], rules_fn, trigger_counts_fn, "Finance Rules"),
]:
    bar_colors = [RED if c > 0 else GREEN for c in counts]
    bars = ax.barh(rules, counts, color=bar_colors, alpha=0.85, zorder=3)
    ax.set_title(title, color="#c9d1d9", fontsize=12)
    ax.set_xlabel("# Violations Detected", fontsize=10)
    ax.set_xlim(0, 2); ax.set_xticks([0, 1, 2])
    ax.grid(axis="x", zorder=0)
    for bar, c in zip(bars, counts):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
                str(c), va="center", fontsize=11, color="#c9d1d9")
plt.tight_layout()
plt.savefig(f"{PLOTS_DIR}/rule_violation_frequency.png", dpi=150, bbox_inches="tight", facecolor="#0d1117")
plt.close()
print("✓ rule_violation_frequency.png")


# 5. drift_detection.png
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle("Drift Detection — Baseline vs Shifted Batch", fontsize=14, color=BLUE)
hc_fields  = ["gender", "emergency_admission", "patient_age", "null_rate"]
hc_scores  = [27.0, 27.6, 0.3, 15.2]
hc_thresh  = [0.20, 0.20, 1.5, 15.0]
fn_fields  = ["annual_income", "credit_score", "employment_status", "loan_purpose"]
fn_scores  = [4.13, 2.66, 0.04, 0.01]
fn_thresh  = [1.5, 1.5, 0.20, 0.20]
for ax, fields, scores, thresholds, title in [
    (axes[0], hc_fields, hc_scores, hc_thresh, "Healthcare Drift Signals"),
    (axes[1], fn_fields, fn_scores, fn_thresh, "Finance Drift Signals"),
]:
    norm_scores = [s / t for s, t in zip(scores, thresholds)]
    colors_d = [RED if ns > 1.0 else GREEN for ns in norm_scores]
    bars = ax.barh(fields, norm_scores, color=colors_d, alpha=0.85, zorder=3)
    ax.axvline(1.0, color=YELLOW, linestyle="--", linewidth=2, label="Alert threshold (1×)", zorder=4)
    ax.set_title(title, color="#c9d1d9", fontsize=12)
    ax.set_xlabel("Drift Score / Threshold (ratio)", fontsize=10)
    ax.grid(axis="x", zorder=0)
    ax.legend(fontsize=9, facecolor="#21262d", edgecolor="#30363d", labelcolor="#c9d1d9")
    for bar, ns in zip(bars, norm_scores):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
                f"{ns:.1f}×", va="center", fontsize=10, color="#c9d1d9",
                fontweight="bold" if ns > 1.0 else "normal")
plt.tight_layout()
plt.savefig(f"{PLOTS_DIR}/drift_detection.png", dpi=150, bbox_inches="tight", facecolor="#0d1117")
plt.close()
print("✓ drift_detection.png")


# 6. pipeline_throughput.png
batch_sizes    = [1, 10, 50, 100, 250, 500, 1000]
throughput_rps = [320, 430, 480, 495, 500, 502, 498]
fig, ax = plt.subplots(figsize=(10, 5))
fig.patch.set_facecolor("#0d1117")
ax.plot(batch_sizes, throughput_rps, color=BLUE, linewidth=2.5, marker="o",
        markersize=8, markerfacecolor="#0d1117", markeredgecolor=BLUE, markeredgewidth=2, zorder=3)
ax.fill_between(batch_sizes, throughput_rps, alpha=0.15, color=BLUE)
ax.axhline(500, color=GREEN, linestyle="--", linewidth=1.5, alpha=0.8, label="Target (500 rec/s)")
ax.set_title("Pipeline Throughput vs Batch Size", color=BLUE, fontsize=14)
ax.set_xlabel("Batch Size (records)", fontsize=11)
ax.set_ylabel("Records per Second", fontsize=11)
ax.set_xscale("log"); ax.set_ylim(0, 600)
ax.grid(zorder=0)
ax.legend(fontsize=10, facecolor="#21262d", edgecolor="#30363d", labelcolor="#c9d1d9")
for x_val, y_val in zip(batch_sizes, throughput_rps):
    ax.annotate(f"{y_val}", (x_val, y_val), textcoords="offset points",
                xytext=(0, 10), ha="center", fontsize=9, color="#8b949e")
plt.tight_layout()
plt.savefig(f"{PLOTS_DIR}/pipeline_throughput.png", dpi=150, bbox_inches="tight", facecolor="#0d1117")
plt.close()
print("✓ pipeline_throughput.png")


# 7. confidence_separation_box.png
fig, ax = plt.subplots(figsize=(9, 5))
fig.patch.set_facecolor("#0d1117")
all_data   = [hc_valid_scores, hc_invalid_scores, fn_valid_scores, fn_invalid_scores]
tick_names = ["HC\nValid", "HC\nInvalid", "FN\nValid", "FN\nInvalid"]
box_colors = [GREEN, RED, GREEN, RED]
bp = ax.boxplot(all_data, patch_artist=True, widths=0.5,
                medianprops={"color": "#ffffff", "linewidth": 2},
                whiskerprops={"color": "#8b949e"},
                capprops={"color": "#8b949e"},
                flierprops={"marker": "o", "color": YELLOW, "markersize": 6})
for patch, color in zip(bp["boxes"], box_colors):
    patch.set_facecolor(color); patch.set_alpha(0.75)
ax.axhline(0.85, color=GREEN,  linestyle="--", linewidth=1.5, alpha=0.8, label="Trusted ≥ 0.85")
ax.axhline(0.50, color=YELLOW, linestyle="--", linewidth=1.5, alpha=0.8, label="Flagged ≥ 0.50")
ax.set_xticks(range(1, 5)); ax.set_xticklabels(tick_names, fontsize=11)
ax.set_ylabel("Confidence Score", fontsize=11)
ax.set_ylim(0.4, 1.15)
ax.set_title("Confidence Score Separation — Valid vs Invalid", color=BLUE, fontsize=14)
ax.grid(axis="y", zorder=0)
ax.legend(fontsize=10, facecolor="#21262d", edgecolor="#30363d", labelcolor="#c9d1d9")
plt.tight_layout()
plt.savefig(f"{PLOTS_DIR}/confidence_separation_box.png", dpi=150, bbox_inches="tight", facecolor="#0d1117")
plt.close()
print("✓ confidence_separation_box.png")


print(f"\n✅ All 7 plots saved to: {PLOTS_DIR}")
