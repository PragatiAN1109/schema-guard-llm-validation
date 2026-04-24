# SchemaGuard — 10-Minute Video Demo Script
**Course:** INFO 7375 · Prompt Engineering for Generative AI · Northeastern University  
**Presenter:** Pragati Narotam  
**Total runtime:** ~10 minutes  
**Format:** Screen-recorded terminal + browser demo with voiceover  

---

## Pre-Demo Checklist

Before recording, have open and ready:
- [ ] VS Code with `validator/pipeline.py` visible (for architecture segment)
- [ ] Terminal at project root, virtualenv active
- [ ] Browser: `http://localhost:8000/docs` (FastAPI Swagger) loaded
- [ ] Browser tab: project website `website/index.html`
- [ ] Three JSON snippets copied and ready to paste (in script below)
- [ ] `audit_logs/healthcare_intake_audit.jsonl` accessible
- [ ] Font size bumped to 18pt in terminal and browser

---


---

## SEGMENT 1 — The Hook (0:00–1:15)

**SCREEN:** Black screen with white text fading in:  
`"Valid JSON. Wrong data."` — hold 3 seconds, then cut to terminal.

---

**NARRATION:**

You're running an LLM pipeline that generates structured patient records or loan applications. Every single output passes JSON Schema validation — correct types, required fields, valid formats. Your pipeline is clean. Your alerts are silent.

But here's what's actually in your data.

**SCREEN:** Paste this JSON into terminal — make text large, syntax-highlighted:

```json
{
  "patient_id": "P-4412",
  "first_name": "Sarah",
  "last_name": "Mitchell",
  "admission_date": "2024-08-15",
  "discharge_date": "2024-08-08",
  "diagnosis_code": "N39.0",
  "patient_age": 34
}
```

**NARRATION:**

Look at the dates. Discharge is August 8th. Admission is August 15th.

*— brief pause —*

This patient was discharged seven days before she was admitted. Every field has the right type. Every field has a valid format. JSON Schema passes it. And without additional validation, it flows straight into your database.

**SCREEN:** Slide in a second record below the first — or open a split terminal:

```json
{
  "applicant_name": "Jessica Williams",
  "annual_income": 48000,
  "loan_amount": 2500000,
  "loan_purpose": "home_purchase"
}
```

**NARRATION:**

Or this loan application. $2.5 million on a $48,000 salary. A 52-times loan-to-income ratio. No regulated lender would touch it. But it passes every type check — because 2500000 *is* a valid number.

*— pause one beat —*

These are semantic failures. The structure is correct. The logic is broken. And standard tooling has no answer for them.

**SCREEN:** Text overlay fades in:  
`SchemaGuard` — hold 1 second — then cut to project website homepage.

---


---

## SEGMENT 2 — What SchemaGuard Does (1:15–2:30)

**SCREEN:** Project website — scroll slowly through the hero section showing the stats bar:  
`100% Accuracy · F1 = 1.0 · 0.09ms median latency · 140 records validated`

---

**NARRATION:**

SchemaGuard is a semantic validation and drift detection layer for LLM-generated structured outputs. It sits between your LLM and any downstream system — database, billing pipeline, ML training set, compliance report — and catches what schema validation misses.

**SCREEN:** Scroll to the Architecture section of the website. Highlight the pipeline diagram:  
`JSON Record → Structural → Semantic Rules → Confidence Score → Decision Router`

**NARRATION:**

Every record goes through four stages.

First, structural validation — standard JSON Schema Draft 7. Types, required fields, formats. The baseline every team already runs.

Second, semantic validation — ten cross-field rules I've written for two domains. These check whether the values in a record are *logically consistent with each other*. Not just valid in isolation, but valid *together*.

Third, confidence scoring. Instead of a binary pass-fail, each record gets a score between 0 and 1. Critical violations subtract 0.30. Warnings subtract 0.12. The score is continuous — it preserves information that pass-fail throws away.

And fourth, decision routing. Three tiers:

**SCREEN:** Zoom to the three decision chips on the architecture diagram:

- 🟢 Trusted — score 0.85 or above. Safe for downstream use.
- 🟡 Flagged — 0.50 to 0.84. Route to human review.
- 🔴 Quarantined — below 0.50. Block from all downstream systems.

**NARRATION:**

Two domains are currently supported: healthcare intake records, and financial loan applications. Five semantic rules each. Ten rules total. All deterministic — same input always produces the same result, with a full audit trail.

---


---

## SEGMENT 3 — Live Demo (2:30–7:00)

*This is the core of the video. Move deliberately. Let the output appear on screen before narrating it.*

---

### 3A — Valid Record (2:30–3:30)

**SCREEN:** Browser — `http://localhost:8000/docs`. Click `POST /validate`. Click "Try it out".

**NARRATION:**

Let me start with the API directly — this is the same endpoint a production system would call. I'll use the FastAPI Swagger UI so you can see the full request and response.

**SCREEN:** Paste into the request body field:

```json
{
  "domain": "healthcare_intake",
  "record": {
    "patient_id": "P-3021",
    "first_name": "James",
    "last_name": "Carter",
    "date_of_birth": "1978-11-02",
    "gender": "male",
    "admission_date": "2024-09-14",
    "discharge_date": "2024-09-19",
    "diagnosis_code": "J18.9",
    "diagnosis_description": "Pneumonia, unspecified organism",
    "treating_physician": "Dr. Susan Park",
    "medication": "Azithromycin",
    "procedure_code": null,
    "insurance_provider": "Aetna",
    "patient_age": 45,
    "emergency_admission": false,
    "notes": null
  }
}
```

**NARRATION:**

James Carter. 45 years old, admitted for pneumonia, treated with Azithromycin. Every field is coherent — the diagnosis, the medication, the dates, the age all line up.

**SCREEN:** Click "Execute". Scroll to response. The response should show:

```
"decision": "trusted",
"confidence_score": 1.0,
"semantic_valid": true,
"violated_rules": []
```

**NARRATION:**

Structural: pass. All five semantic rules: pass. Confidence 1.0. Decision: trusted. This record is clean — it can flow to any downstream system without review.

---

### 3B — Critical Violation — HC-003 (3:30–5:00)

**SCREEN:** Clear the request body. Paste the invalid healthcare record:

```json
{
  "domain": "healthcare_intake",
  "record": {
    "patient_id": "P-4412",
    "first_name": "Sarah",
    "last_name": "Mitchell",
    "date_of_birth": "1990-01-20",
    "gender": "female",
    "admission_date": "2024-08-15",
    "discharge_date": "2024-08-08",
    "diagnosis_code": "N39.0",
    "diagnosis_description": "Urinary tract infection",
    "treating_physician": "Dr. Mark Evans",
    "medication": "Ciprofloxacin",
    "procedure_code": null,
    "insurance_provider": "UnitedHealth",
    "patient_age": 34,
    "emergency_admission": false,
    "notes": null
  }
}
```

**NARRATION:**

Now Sarah Mitchell. Looks completely reasonable — valid UTI diagnosis, appropriate antibiotic. But look at the dates. Discharge August 8th. Admission August 15th.

**SCREEN:** Click "Execute". The response loads. Highlight the key fields:

```json
"decision": "flagged",
"confidence_score": 0.70,
"semantic_valid": false,
"violated_rules": [
  {
    "rule_id": "HC-003",
    "rule_name": "discharge_after_admission",
    "severity": "critical",
    "fields": ["admission_date", "discharge_date"],
    "message": "Discharge date (2024-08-08) precedes admission date (2024-08-15)"
  }
],
"explanation": "Record failed validation. Critical issues: discharge_after_admission..."
```

**NARRATION:**

Structural: pass. The JSON is perfectly formed. But semantic validation caught it — rule HC-003 fired. Discharge before admission. Critical severity. Confidence drops from 1.0 to 0.70 — that's the 0.30 critical penalty. Decision: flagged.

The explanation names the exact fields, the exact dates, and the exact discrepancy. Not a vague error message — a precise, traceable finding.

If this record went to a billing system, it would trigger a Medicare claim rejection. If it went to an ML training set, it would teach the model that patients can leave before arriving. SchemaGuard catches it before either of those happen.

---

### 3C — RAG-Augmented Explanation (5:00–6:00)

**SCREEN:** Swap to `POST /rag/explain` in the Swagger UI. Click "Try it out". Paste the same Sarah Mitchell record. Execute.

**NARRATION:**

Now let me show the RAG explanation endpoint. Same record — but this time, the system retrieves relevant regulatory context from a FAISS vector store and calls Claude to generate a grounded explanation.

**SCREEN:** Scroll to the `rag_explanation` field in the response. Highlight key phrases as you read them:

> *"Under HL7 FHIR R4 (Encounter.period), the period.end must be on or after period.start; a negative length-of-stay is mathematically impossible and will trigger automatic claim rejection by Medicare's Inpatient Prospective Payment System (IPPS) grouper..."*
> 
> *"Per CMS Medicare Claims Processing Manual Chapter 1 §30.2, both dates should be cross-referenced against nursing admission notes and medication administration records..."*
> 
> *"Remediation: Correct discharge_date to a date ≥ 2024-08-15. Do not resubmit for billing until the corrected record has been validated."*

**SCREEN:** Scroll slightly to show the `retrieved_chunks` array — show chunk titles and cosine scores:
- `HC-003-b-c000` — "Same-Day Discharge: Valid vs Invalid Patterns" — score 0.6453
- `HC-003-a-c000` — "Discharge Date Sequencing and Length-of-Stay Calculations" — score 0.6109

**NARRATION:**

Compare that to the baseline explanation we just saw — 41 words, naming the violation. This RAG explanation is 168 words. It cites HL7 FHIR R4 by resource name. It cites the CMS Manual by chapter and section number. It names the downstream consequence — claim rejection. And it gives a specific remediation step that a compliance reviewer can act on immediately.

That's the difference between telling someone *what* is wrong and telling them *why it matters and what to do*.

---

### 3D — Drift Detection (6:00–7:00)

**SCREEN:** Switch to terminal. Run:

```bash
cat audit_logs/healthcare_intake_audit.jsonl | python3 -c "
import sys, json
records = [json.loads(l) for l in sys.stdin if l.strip()]
violations = [r for r in records if r.get('rules_violated')]
print(f'Total records  : {len(records)}')
print(f'With violations: {len(violations)}')
print(f'Trusted        : {sum(1 for r in records if r[\"decision\"]==\"trusted\")}')
print(f'Flagged        : {sum(1 for r in records if r[\"decision\"]==\"flagged\")}')
from collections import Counter
all_rules = [rule for r in records for rule in r.get(\"rules_violated\",[])]
print(\"Rule counts    :\", dict(Counter(all_rules)))
"
```

**SCREEN:** Output appears:

```
Total records  : 123
With violations: 40
Trusted        : 83
Flagged        : 40
Rule counts    : {'HC-003': 37, 'HC-001': 3, 'HC-004': 3}
```

**NARRATION:**

This is the live audit log from 123 real validation runs. 83 records trusted, 40 flagged, zero quarantined. 37 HC-003 violations — discharge before admission was the dominant error in this batch.

Now here's what drift detection adds. A single HC-003 violation tells me that *this one record* has a bad date. But when HC-003 appears in 30 percent of my batch, that's a different signal entirely — it means my LLM's date-generation behavior has shifted. Drift detection catches that population-level change.

**SCREEN:** Show the drift baseline file:

```bash
cat drift/baselines/healthcare_intake_baseline.json | python3 -m json.tool | head -30
```

**NARRATION:**

The baseline profiles the expected distributions — mean patient age, gender split, diagnosis code frequencies. When a new batch arrives, SchemaGuard computes z-scores and PSI against those baselines and raises an alert if any signal crosses its threshold. Not just "this record is wrong" — but "your LLM's output distribution has drifted."

---


---

## SEGMENT 4 — Architecture Deep Dive (7:00–8:15)

**SCREEN:** VS Code. Open `rules/healthcare_rules.py`. Scroll to the HC-003 function. Zoom so it's clearly readable.

---

**NARRATION:**

Let me show you how this is built. The rule engine uses a decorator pattern — each rule is a regular Python function registered with metadata.

**SCREEN:** Highlight the decorator block and function signature:

```python
@register_rule(
    domain="healthcare_intake",
    rule_id="HC-003",
    rule_name="discharge_after_admission",
    severity="critical",
    fields=["admission_date", "discharge_date"],
)
def check_discharge_after_admission(record: dict) -> RuleResult:
    admission = _parse_date(record.get("admission_date"))
    discharge  = _parse_date(record.get("discharge_date"))
    if admission is None or discharge is None:
        return RuleResult(rule_id="HC-003", passed=True, ...)
    passed = discharge >= admission
    return RuleResult(
        rule_id="HC-003", passed=passed, severity="critical",
        message="" if passed else
            f"Discharge ({record['discharge_date']}) precedes admission ({record['admission_date']})"
    )
```

**NARRATION:**

The decorator captures the metadata — domain, rule ID, severity, affected fields. The function contains only the logic. They're completely decoupled. Adding a new rule is adding a new decorated function. Adding a new domain is adding a new rules file. The pipeline itself never needs to change.

**SCREEN:** Open `scoring/confidence.py`. Highlight the penalty formula.

**NARRATION:**

Confidence scoring applies severity-weighted penalties — 0.30 for critical violations, 0.12 for warnings — clamped to zero at the bottom. A single critical violation gives 0.70. Two critical violations give 0.40, which routes to quarantine. One warning gives 0.88 — trusted, but with a flag in the result.

**SCREEN:** Split view — show `rag/vector_store.py` briefly, then `rag/explainer.py`. 

**NARRATION:**

The RAG module is separate from the core pipeline. It runs on top. Eleven reference documents — synthetic but realistic, with real regulatory citations — are chunked into 17 overlapping segments, embedded with a 384-dimensional sentence transformer, and indexed in FAISS. When the explain endpoint is called, it retrieves the three most relevant chunks by cosine similarity, builds an augmented prompt with the record and the violations, and calls Claude to generate the explanation. The core pipeline doesn't wait for any of this — validation is still sub-millisecond.

**SCREEN:** Open `api/main.py`. Show the four router lines:

```python
app.include_router(router)                               # sync validation
app.include_router(async_router, prefix="/async")       # async batch
app.include_router(user_router,  prefix="/user")        # analytics
app.include_router(rag_router,   prefix="/rag")         # RAG explanations
```

**NARRATION:**

The API has four routers. Synchronous single-record validation. Async batch with job queue and retry logic. User analytics and audit access. And the RAG explanation layer. Each router is independently testable and deployable.

---


---

## SEGMENT 5 — Metrics (8:15–9:15)

**SCREEN:** Open `outputs/plots/12_summary_dashboard.png` — full screen.  
*Let it sit for 3 full seconds before narrating. The chart should speak first.*

---

**NARRATION:**

Here are the evaluation results. 140 real records from the audit log. 16 labeled seed records for classification metrics.

**SCREEN:** Mouse-highlight the top-left panel (classification metrics bar chart).

**NARRATION:**

Precision, recall, and F1 at 1.0 on both domains. 100% accuracy. Zero false quarantines — not a single valid record was incorrectly blocked from downstream use, including all the edge-case boundary-condition records.

**SCREEN:** Mouse-highlight the confidence histogram or confidence gap chart.

**NARRATION:**

The confidence distribution is cleanly bimodal. Valid records cluster at 1.0. Invalid records land at 0.70 or 0.88 depending on violation severity. No overlap. The healthcare gap is 0.24. Finance gap is 0.30. The scoring thresholds don't need tuning on this dataset.

**SCREEN:** Open `outputs/plots/07_latency_distribution.png`.

**NARRATION:**

Latency. Median 0.09 milliseconds. p99 is 3 milliseconds — that's the Python warm-up cost on the first records in a session. Mean latency of 0.26 milliseconds translates to roughly 3,800 records per second from a single process. No I/O. No network calls. Pure CPU.

**SCREEN:** Return to the summary dashboard. Mouse-highlight the scorecard panel (bottom right).

**NARRATION:**

And for the RAG module: explanation quality improved from an average of 2.7 out of 6 for the deterministic baseline to a perfect 6 out of 6 across all six test cases. The three criteria the baseline missed completely — citing a regulation, explaining the downstream consequence, providing a remediation step — every RAG explanation nailed all three. Average explanation length went from 42 words to 175 words. Every extra word is actual regulatory information, not padding.

---


---

## SEGMENT 6 — Future Work + Close (9:15–10:00)

**SCREEN:** Project website — scroll to the Roadmap section. The six future-work cards visible.

---

**NARRATION:**

The infrastructure for everything you've seen is in place. There are six clear directions to extend this.

**SCREEN:** Highlight cards as you mention each one — briefly, don't linger.

**NARRATION:**

The 600-record synthetic dataset is scaffolded and ready to generate — it needs an API key and about 15 minutes of runtime. That would give statistically reliable precision and recall estimates across all ten rules, not just the seed-set results.

The domain-agnostic architecture means adding insurance claims or electronic prescriptions is two files — a schema and a rules file. The pipeline doesn't change.

Active learning for borderline records would close the loop — reviewer corrections on flagged records feeding back into threshold calibration over time.

And the most interesting direction: using the violation patterns in the audit log to propose new rules the system doesn't know about yet. LLMs generating structured data will find failure modes no one anticipated. An LLM-assisted rule discovery process would help the system keep up.

**SCREEN:** Pause on website. Cut to black.

**NARRATION:**

Schema validation tells you whether JSON is well-formed. SchemaGuard tells you whether it's logically coherent. For any team using LLMs to generate structured data in production — healthcare, finance, compliance, or any regulated domain — that's the validation layer that's currently missing.

**SCREEN:** Final frame — white text on dark background, hold 4 seconds:

```
SchemaGuard

github.com/pragatinarote/schema-guard-llm-validation

INFO 7375 · Prompt Engineering for GenAI
Northeastern University · 2025
```

*Fade to black.*

---


---

## TIMING SUMMARY

| Segment | Title | Start | End | Duration |
|---------|-------|-------|-----|----------|
| 1 | The Hook (problem) | 0:00 | 1:15 | 1 min 15 sec |
| 2 | What SchemaGuard does | 1:15 | 2:30 | 1 min 15 sec |
| 3A | Demo — valid record | 2:30 | 3:30 | 1 min 00 sec |
| 3B | Demo — HC-003 critical violation | 3:30 | 5:00 | 1 min 30 sec |
| 3C | Demo — RAG explanation | 5:00 | 6:00 | 1 min 00 sec |
| 3D | Demo — drift detection | 6:00 | 7:00 | 1 min 00 sec |
| 4 | Architecture walkthrough | 7:00 | 8:15 | 1 min 15 sec |
| 5 | Metrics highlights | 8:15 | 9:15 | 1 min 00 sec |
| 6 | Future work + close | 9:15 | 10:00 | 0 min 45 sec |
| | **Total** | | | **~10 min** |

---

## SCREEN SEQUENCE REFERENCE

A quick-reference list of every screen transition in order:

1. `Black screen` — text: "Valid JSON. Wrong data."
2. `Terminal` — paste Sarah Mitchell record (discharge before admission)
3. `Terminal` — paste Jessica Williams record (52× LTI)
4. `Project website` — hero section with metrics bar
5. `Project website` — Architecture section, pipeline diagram
6. `Project website` — Architecture section, decision chips
7. `Browser: localhost:8000/docs` — POST /validate, James Carter (valid)
8. `Browser: localhost:8000/docs` — Response: trusted, score 1.0
9. `Browser: localhost:8000/docs` — POST /validate, Sarah Mitchell (HC-003)
10. `Browser: localhost:8000/docs` — Response: flagged, score 0.70, HC-003 violation
11. `Browser: localhost:8000/docs` — POST /rag/explain, Sarah Mitchell
12. `Browser: localhost:8000/docs` — RAG response: HL7 FHIR, CMS §30.2, remediation
13. `Browser: localhost:8000/docs` — retrieved_chunks array with cosine scores
14. `Terminal` — audit log analysis (Python one-liner): 123 records, rule counts
15. `Terminal` — drift baseline JSON (healthcare_intake_baseline.json)
16. `VS Code` — `rules/healthcare_rules.py` — HC-003 decorator + function
17. `VS Code` — `scoring/confidence.py` — penalty formula
18. `VS Code` — `rag/explainer.py` — explainer pipeline overview
19. `VS Code` — `api/main.py` — four include_router lines
20. `Plot: 12_summary_dashboard.png` — full screen, 3-second pause
21. `Plot: 07_latency_distribution.png` — latency histogram with p50/p95/p99
22. `Plot: 12_summary_dashboard.png` — scorecard panel highlighted
23. `Project website` — Roadmap / Future Work section
24. `Black screen` — final title card: SchemaGuard / GitHub / Course

---

## DEMO BACKUP PLAN

*If the FastAPI server isn't running or a live call fails:*

**Option A — Terminal fallback.** Run the quick demo script instead:
```bash
python3 demo/quick_demo.py
```
This validates three records (valid, HC-003 violation, FN-002 violation) and prints full results to terminal. Looks clean, all real output.

**Option B — Pre-recorded fallback.** Record a short 90-second screencast of just the API calls before the real recording session. If a live call hangs, cut to the pre-recorded footage seamlessly.

**Option C — Raw pipeline call.** Drop into Python REPL directly:
```python
from validator.pipeline import validate_record
import json

record = {
    "patient_id": "P-4412", "first_name": "Sarah", "last_name": "Mitchell",
    "date_of_birth": "1990-01-20", "gender": "female",
    "admission_date": "2024-08-15", "discharge_date": "2024-08-08",
    "diagnosis_code": "N39.0", "medication": "Ciprofloxacin",
    "patient_age": 34, "emergency_admission": False,
    "procedure_code": None, "insurance_provider": "UnitedHealth", "notes": None,
    "diagnosis_description": "Urinary tract infection",
    "treating_physician": "Dr. Mark Evans"
}
result = validate_record(record, "healthcare_intake")
print(json.dumps({
    "decision": result["decision"],
    "confidence_score": result["confidence_score"],
    "semantic_valid": result["semantic_valid"],
    "violated_rules": [v["rule_id"] for v in result.get("violated_rules", [])]
}, indent=2))
```

Expected output:
```json
{
  "decision": "flagged",
  "confidence_score": 0.7,
  "semantic_valid": false,
  "violated_rules": ["HC-003"]
}
```

---

## DELIVERY NOTES

**Pace:** Speak at ~140 words per minute. The script is written to that pace. If you're running fast, add 2–3 seconds of silence after each response appears on screen before narrating it.

**Demo segment (3A–3D):** Don't narrate while typing. Type the JSON, pause, then speak. The viewer needs to read the input before hearing the output.

**On the RAG output:** Read the regulation citation out loud. "HL7 FHIR R4, Encounter.period" and "CMS Medicare Claims Processing Manual Chapter 1 Section 30.2" — these are the details that make the comparison compelling. Don't rush past them.

**On the metrics chart:** Give the dashboard 3 full seconds of silence before speaking. Let the viewer scan it. Then guide them.

**Tone:** Confident, specific, no hedging. You built this — own it. Avoid "kind of", "basically", "sort of". Every claim in this script is backed by a real number or a live demo call.

---
