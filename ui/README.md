# ui/

Streamlit demo interface for SchemaGuard.

## Running

```bash
cd schema-guard-llm-validation
streamlit run ui/app.py
```

Opens at `http://localhost:8501`.

## Features

### Tab 1: Single Record Validation
- Dropdown: domain selection (healthcare / finance)
- Text area: paste JSON record (pre-filled with sample)
- Color-coded decision badge (green / yellow / red)
- Confidence score progress bar
- Explanation text
- Violated rules with severity icons
- Full JSON result in expander

### Tab 2: Batch Validation
- Upload JSON file or paste array
- Falls back to seed data as demo
- Summary cards: total / trusted / flagged / quarantined
- Per-record result list with decisions
- Drift detection results with alerts

### Tab 3: Sample Browser
- Browse all seed records by category
- One-click validate any seed record
- Generate baseline from valid seeds
