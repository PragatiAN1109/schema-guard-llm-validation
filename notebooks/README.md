# SchemaGuard — Notebooks

Four Jupyter notebooks documenting the project end-to-end, presentation-ready with pre-populated outputs.

## Notebooks

| # | Notebook | Description |
|---|----------|-------------|
| 01 | `01_prompt_engineering.ipynb` | Prompt template design, v1→v3 iteration log, seed data inspection, rule coverage analysis |
| 02 | `02_validation_pipeline.ipynb` | 4-stage pipeline walkthrough, live record runs, all 16 seed records scored with emoji badges |
| 03 | `03_evaluation_metrics.ipynb` | Full metrics table, confusion matrix, confidence gap analysis, all evaluation charts |
| 04 | `04_drift_detection.ipynb` | Baseline profiles, stable vs shifted batch comparison, finance drift signals, throughput benchmark |

## Setup

```bash
# From project root
pip install jupyter ipykernel matplotlib seaborn numpy pandas
jupyter notebook notebooks/
```

Or with the project's existing Python (python3.12):
```bash
/opt/homebrew/bin/python3.12 -m jupyter notebook notebooks/
```

## Plots

All plots are pre-generated and saved in `../outputs/plots/`. Notebooks reference them via relative path.

To regenerate plots:
```bash
/opt/homebrew/bin/python3.12 outputs/generate_plots.py
```

| Plot | Description |
|------|-------------|
| `confidence_distribution.png` | Bar chart: confidence scores per record, valid vs invalid |
| `confidence_separation_box.png` | Boxplot: confidence gap between valid and invalid records |
| `metrics_comparison.png` | Grouped bar: Precision/Recall/F1/Accuracy for HC vs FN |
| `decision_distribution.png` | Pie charts: trusted/flagged/quarantined per domain |
| `rule_violation_frequency.png` | Horizontal bar: how often each rule was triggered |
| `drift_detection.png` | Drift signal ratios vs threshold for both domains |
| `pipeline_throughput.png` | Line chart: records/second vs batch size |
