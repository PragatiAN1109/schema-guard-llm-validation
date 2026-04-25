# SchemaGuard — Demo Run Instructions

Project: /Users/pragatinarote/Desktop/schema-guard-llm-validation

---

## Step 1 — One-time setup (already done if you ran this)

```bash
/opt/homebrew/bin/python3.12 -m pip install --break-system-packages python-multipart streamlit
chmod +x run_backend.sh run_ui.sh
```

Both are already installed and scripts are already executable after the fix above.

---

## Step 2 — Start the backend (Terminal 1)

```bash
cd /Users/pragatinarote/Desktop/schema-guard-llm-validation
./run_backend.sh
```

You will see:
```
Starting SchemaGuard API on http://localhost:8000
Swagger docs: http://localhost:8000/docs
INFO: Uvicorn running on http://0.0.0.0:8000
```

Leave this terminal open.

---

## Step 3 — Start the UI (Terminal 2, pick one)

### Option A — Next.js console (recommended, already built)
```bash
cd /Users/pragatinarote/Desktop/schema-guard-llm-validation/frontend
node_modules/.bin/next dev --port 3000
```
Opens at: http://localhost:3000

### Option B — Streamlit (simpler single page)
```bash
cd /Users/pragatinarote/Desktop/schema-guard-llm-validation
./run_ui.sh
```
Opens at: http://localhost:8501

---

## Step 4 — Demo flow (5-minute walkthrough)

### 1. Validate a clean record
- Go to http://localhost:3000/validate
- Domain: Healthcare Intake
- Load dropdown → pick any ✅ valid entry
- Click "Validate Record"
- Result: TRUSTED, confidence 1.00

### 2. Show a violation being caught
- Load dropdown → ❌ invalid — HC-seed-004
- Click "Validate Record"
- Result: FLAGGED, confidence 0.70, HC-003 fires
- Click the HC-003 card → expands to show "Why This Matters" + downstream impact

### 3. Show auto-correction
- Click "🔧 Suggest Corrections"
- See discharge_date: current → suggested diff
- Click "⚡ Apply Auto-Fixes"
- Re-validate → TRUSTED 1.00

### 4. Finance violation
- Switch domain to Financial Loan Application
- Load any ❌ invalid FN record (or paste below)
- Validate → FN-002 fires (52.1× income limit)
- Auto-fix: loan_amount capped at $480,000

Paste this for a live finance demo:
```json
{
  "application_id": "LA-demo",
  "applicant_name": "Jessica Williams",
  "date_of_birth": "1991-06-18",
  "annual_income": 48000,
  "employment_status": "employed",
  "employer_name": "Target",
  "employment_length_years": 3,
  "loan_amount": 2500000,
  "loan_purpose": "home_purchase",
  "loan_term_months": 360,
  "interest_rate": 6.5,
  "credit_score": 680,
  "existing_debt": 15000,
  "application_date": "2024-05-12",
  "approval_date": null,
  "approved_amount": null,
  "property_value": 2600000,
  "co_applicant": false,
  "notes": null
}
```

### 5. Rules Library
- Go to http://localhost:3000/rules
- Click HC-003 → regulatory reference: NUBC UB-04 FL6/FL16
- Click FN-002 → regulatory reference: CFPB ATR Rule 12 CFR §1026.43

### 6. Batch validation
- Go to http://localhost:3000/batch
- Paste a JSON array of records (mix valid + invalid)
- Click "Run Batch" → shows per-record confidence bars + violation chips

### 7. Audit trail
- Go to http://localhost:3000/audit
- Click any row to expand full explanation

---

## Raw API (for technical audience)

Swagger UI: http://localhost:8000/docs

Test a violation via curl:
```bash
curl -s -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{"domain":"healthcare_intake","record":{"patient_id":"P-demo","first_name":"Sarah","last_name":"M","date_of_birth":"1990-01-20","gender":"female","admission_date":"2024-08-15","discharge_date":"2024-08-08","diagnosis_code":"N39.0","diagnosis_description":"UTI","treating_physician":"Dr. Evans","medication":"Ciprofloxacin","procedure_code":null,"insurance_provider":"UnitedHealth","patient_age":34,"emergency_admission":false,"notes":null}}' \
  | python3 -m json.tool
```

Get auto-fix suggestions:
```bash
curl -s http://localhost:8000/suggest/suggest-fix/rules | python3 -m json.tool
```

Health check:
```bash
curl http://localhost:8000/health
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Port 8000 in use | lsof -ti:8000 \| xargs kill -9 |
| Port 3000 in use | lsof -ti:3000 \| xargs kill -9 |
| `permission denied: ./run_backend.sh` | chmod +x run_backend.sh run_ui.sh |
| pip externally-managed error | Use --break-system-packages flag |
| Frontend blank/error | Start backend first, then frontend |
| Validate returns confidence 0.0 | Record has extra keys (e.g. _label) — remove internal fields |
