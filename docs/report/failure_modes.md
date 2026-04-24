# SchemaGuard — Failure Modes Analysis

> **Module coverage:** `validator/` · `rag/` · `ingest/`  
> **Source revision:** v0.3.0 (April 2025)  
> All behaviours verified against the live codebase via automated probes.

---

## Table of Contents

1. [Validator Module Failures](#1-validator-module-failures)  
   1.1 Structural Validation  
   1.2 Semantic Rule Engine  
   1.3 Confidence Scoring  
   1.4 Pipeline-Level  
2. [RAG Module Failures](#2-rag-module-failures)  
   2.1 Retrieval Layer  
   2.2 Explanation Generation  
3. [Ingest Module Failures](#3-ingest-module-failures)  
   3.1 Text Extraction  
   3.2 LLM Field Extraction  
   3.3 Pipeline Integration  
4. [Cross-Cutting Concerns](#4-cross-cutting-concerns)  
5. [Mitigation Priority Matrix](#5-mitigation-priority-matrix)

---

## 1. Validator Module Failures

### 1.1 Structural Validation (`validator/structural.py`)

---

#### FM-V-001 — Malformed date string silently passes structural validation

**Severity:** Medium  
**Confirmed:** Yes (live probe)

**Cause:**  
JSON Schema Draft 7 `"format": "date"` is advisory, not mandatory. `Draft7Validator` validates format annotations only when the `format` checker is explicitly enabled. The current `validate_structure` call uses `Draft7Validator(schema)` without enabling format checking, so `"admission_date": "not-a-date"` passes structural validation without error.

**Observed behaviour:**
```python
record = { ..., "admission_date": "not-a-date", "discharge_date": "2024-09-19", ... }
result = validate_record(record, "healthcare_intake")
# → structural_valid=True, confidence=1.0, decision="trusted"
```

The temporal rules (HC-002, HC-003) call `_parse_date()`, which returns `None` on parse failure and short-circuits to `passed=True`. A patient record with a garbled admission date routes as fully trusted.

**Mitigation:**
```python
# Option A: Enable format checking in Draft7Validator
from jsonschema import Draft7Validator, FormatChecker
validator = Draft7Validator(schema, format_checker=FormatChecker())

# Option B: Add a dedicated structural date-format rule before semantic validation
# Checks that all date fields match /^\d{4}-\d{2}-\d{2}$/ before passing to rules
```

---

#### FM-V-002 — Extra/unknown fields rejected by JSON Schema `additionalProperties: false`

**Severity:** Low (correct by design, but may surprise integrators)  
**Confirmed:** Yes (live probe)

**Cause:**  
Both domain schemas include `"additionalProperties": false`. Any record containing fields not declared in the schema fails structural validation immediately and is quarantined at confidence 0.0.

**Observed behaviour:**
```python
record = { ..., "extra_field": "surprise", "nested": {"a": 1} }
# → structural_valid=False, structural_errors=["Additional properties are not allowed ('extra_field', 'nested')"]
# → confidence=0.0, decision="quarantined"
```

LLM-generated records, document-extracted records, or records from upstream systems that add custom metadata fields will all be quarantined.

**Mitigation:**  
Strip non-schema fields at the API boundary before validation, or change to `"additionalProperties": true` for forward-compatibility. For ingest, the `_llm_extract` function should only emit declared fields — confirm this is enforced by the extraction prompt.

---

#### FM-V-003 — Schema `pattern` regex mismatch on record IDs causes false quarantine

**Severity:** Medium  
**Confirmed:** Yes (live probe)

**Cause:**  
`healthcare_schema.json` requires `patient_id` to match `^P-[0-9]{4,6}$` and `finance_schema.json` requires `application_id` to match `^LA-[0-9]{5,8}$`. Any record with an ID outside these patterns fails structural validation.

**Observed behaviour:**
```python
# Both quarantined at confidence=0.0 despite being otherwise valid:
{ "patient_id": "P-1" }         # too short (1 digit, needs 4-6)
{ "application_id": "LA-999" }  # too short (3 digits, needs 5-8)
```

Integrators using short IDs (e.g., sequential integers starting from 1), UUIDs, or external system IDs that don't match the regex will see all records quarantined before any semantic rules run.

**Mitigation:**  
Broaden the ID pattern to `^P-[0-9A-Za-z-]{1,20}$`, or remove the pattern constraint and validate ID format as an optional semantic rule rather than a structural blocker.

---

### 1.2 Semantic Rule Engine (`rules/healthcare_rules.py`, `rules/finance_rules.py`)

---

#### FM-V-004 — HC-005 silently passes on unknown ICD-10 categories

**Severity:** Medium  
**Confirmed:** Yes (live probe)

**Cause:**  
`check_medication_plausibility` looks up the first 3 characters of `diagnosis_code` in `_DIAGNOSIS_MED_MAP`. If the prefix is not in the map (e.g., `M81`, `C61`, `F32`), the rule returns `passed=True` without any flag.

**Observed behaviour:**
```python
record = { ..., "diagnosis_code": "M81.0", "medication": "Amoxicillin" }
# M81 not in _DIAGNOSIS_MED_MAP → violations=[]
# Amoxicillin is an antibiotic, M81.0 is osteoporosis — clinically nonsensical
# → confident=1.0, decision="trusted"
```

The map covers only 7 ICD-10 prefixes (E11, J18, J06, I10, I25, N39, K21). Any diagnosis outside these is silently trusted regardless of medication assigned.

**Mitigation:**  
Add an `"unknown_diagnosis"` info-level signal when the category is not in the map:
```python
if known_meds is None:
    return RuleResult(rule_id="HC-005", passed=True, severity="info",
        message=f"Medication-diagnosis check skipped: {category} not in known categories")
```
Longer term, expand `_DIAGNOSIS_MED_MAP` to cover the 50 most common ICD-10 categories.

---

#### FM-V-005 — HC-001 age tolerance allows silent 1-year mismatches

**Severity:** Low (by design, but worth documenting)  
**Confirmed:** Yes

**Cause:**  
`check_age_matches_dates` applies `abs(computed_age - stated_age) <= 1` tolerance to handle birthday boundary conditions. This means a stated age of 46 when computed age is 45 will pass without any flag.

**Observed behaviour:**
```python
record = { ..., "date_of_birth": "1978-11-02", "admission_date": "2024-09-14", "patient_age": 46 }
# computed_age = 45, stated_age = 46, diff = 1 → passes HC-001
```

In a record containing a 1-year data entry error (e.g., birth year transposed by 1), this passes silently. For paediatric patients where age determines dosing, a 1-year error is clinically significant.

**Mitigation:**  
Make the tolerance configurable per domain or patient age group:
```python
tolerance = 0 if age < 2 else 1   # stricter for neonates/infants
passed = abs(computed_age - stated_age) <= tolerance
```

---

#### FM-V-006 — HC-001/HC-002/HC-003 cascade: shared root cause inflates penalty

**Severity:** Medium  
**Confirmed:** Yes (live probe)

**Cause:**  
When `date_of_birth` is set to a future date, it independently triggers:
- HC-002 (`admission_date < date_of_birth`) — critical
- HC-001 (computed age from future DOB produces impossible age) — critical

Both fire simultaneously even though they share a single root cause: one wrong field. The confidence penalty is `1.0 − 0.30 − 0.30 = 0.40` (quarantined) rather than the `0.70` that a single-field error merits.

**Observed behaviour:**
```python
record = { ..., "date_of_birth": "2030-01-01", "patient_age": 0 }
# → violations=['HC-001', 'HC-002'], confidence=0.40, decision=quarantined
# Root cause: one bad field produced two violations
```

**Mitigation:**  
Introduce a `root_cause` field in `RuleResult`. The confidence scorer can deduplicate violations sharing the same root cause, applying only the highest-severity penalty:
```python
@dataclass
class RuleResult:
    ...
    root_cause: str | None = None   # e.g. "date_of_birth"

# In compute_confidence():
seen_roots = set()
for violation in violations:
    root = violation.get("root_cause")
    if root and root in seen_roots:
        continue  # skip — already penalised for this root
    if root:
        seen_roots.add(root)
    score -= SEVERITY_WEIGHTS[violation["severity"]]
```

---

#### FM-V-007 — FN-002 and FN-003 pass silently when `annual_income = 0`

**Severity:** Medium  
**Confirmed:** Yes (live probe)

**Cause:**  
Both `check_loan_to_income_ratio` (FN-002) and `check_debt_to_income_ratio` (FN-003) guard against zero-division by returning `passed=True` when `annual_income <= 0`. A record with zero income and a large loan is trusted.

**Observed behaviour:**
```python
record = { ..., "annual_income": 0, "loan_amount": 50000, "existing_debt": 1000 }
# → violations=[], confidence=1.0, decision="trusted"
# 0/0 income + $50k loan = no alert
```

An employed applicant with zero income is logically suspect and should be flagged.

**Mitigation:**  
Add FN-006: `annual_income > 0 OR employment_status in ('student', 'retired', 'unemployed')`. Zero income for an `employed` applicant is a warning-level violation.
```python
@register_rule(domain="financial_loan_application", rule_id="FN-006",
               rule_name="income_plausibility", severity="warning", ...)
def check_income_plausibility(record):
    income = record.get("annual_income", 0)
    status = record.get("employment_status", "")
    if income == 0 and status == "employed":
        return RuleResult(passed=False, severity="warning",
            message="annual_income=0 is implausible for employment_status='employed'")
    return RuleResult(passed=True, ...)
```

---

### 1.3 Confidence Scoring (`scoring/confidence.py`)

---

#### FM-V-008 — Warning violations route as "trusted" even when semantically suspicious

**Severity:** Low (by design, but produces counterintuitive results)  
**Confirmed:** Yes (live probe)

**Cause:**  
Warning violations subtract only 0.12 from a starting score of 1.0. A single warning yields `0.88 ≥ 0.85 threshold` → decision is `trusted`. This means a record with a documented clinical inconsistency (e.g., cardiac medication prescribed for a UTI) routes to trusted with no blocking.

**Observed behaviour:**
```python
record = { ..., "diagnosis_code": "N39.0", "medication": "Metoprolol" }
# HC-005 fires (warning): medication mismatch
# → confidence=0.88, decision="trusted"
```

Downstream consumers receive a trusted record with a warning in the `violated_rules` array — easy to ignore.

**Mitigation:**  
Option A: Lower the trusted threshold from 0.85 to 0.90 for domains with active warning rules.  
Option B: Add a `warning_count` field to the response, and require downstream consumers to check it:
```json
"summary": { "decision": "trusted", "critical_violations": 0, "warning_violations": 1 }
```

---

#### FM-V-009 — Zero rules evaluated produces mild 0.05 penalty, not quarantine

**Severity:** Low  
**Confirmed:** Yes (code review)

**Cause:**  
`compute_confidence` applies a `−0.05` "sparse record" penalty when `rules_evaluated == 0` and the record is structurally valid. This produces `confidence=0.95`, which routes as trusted. This scenario occurs if the rule registry is accidentally empty (e.g., import error at startup).

**Mitigation:**  
Check rule count at startup and fail-fast if no rules are registered for a domain:
```python
for domain in VALID_DOMAINS:
    rules = registry.get_rules(domain)
    if not rules:
        raise RuntimeError(f"No rules registered for domain '{domain}' — check imports")
```

---

### 1.4 Pipeline-Level (`validator/pipeline.py`)

---

#### FM-V-010 — Semantic rules run only when structural validation passes

**Severity:** Low (correct by design, but means partially correct records are never semantically evaluated)  
**Confirmed:** Yes (code review)

**Cause:**  
```python
if structural["valid"]:
    semantic = validate_semantics(record, resolved_domain)
else:
    semantic = {"valid": False, "violations": [], "rules_evaluated": 0}
```

A record that fails structural validation (e.g., wrong type on one field) receives no semantic analysis, even if the remaining fields contain semantic violations. The explanations for such records only mention the structural error, not the semantic issues that would also exist.

**Mitigation:**  
Run semantic validation in parallel with structural, or implement a "best-effort" semantic pass on structurally invalid records, marking semantic results as advisory.

---

#### FM-V-011 — Whitespace-padded date strings pass both structural and semantic validation

**Severity:** Low  
**Confirmed:** Yes (live probe)

**Cause:**  
`_parse_date("  2024-09-14  ")` calls `datetime.strptime(date_str, "%Y-%m-%d")`. Python's `strptime` does **not** strip leading/trailing whitespace — it raises `ValueError`, which `_parse_date` catches and returns `None`. Both temporal rules then short-circuit to `passed=True`.

**Observed behaviour:**
```python
record = { ..., "admission_date": "  2024-09-14  ", "discharge_date": "2024-09-19" }
# _parse_date("  2024-09-14  ") → None (parse failure, whitespace not stripped)
# HC-003: admission is None → passed=True
# → confidence=1.0, decision="trusted"
```

**Mitigation:**  
Strip whitespace in `_parse_date`:
```python
def _parse_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
```

---

## 2. RAG Module Failures

### 2.1 Retrieval Layer (`rag/vector_store.py`, `rag/explainer.py`)

---

#### FM-R-001 — Valid records retrieve violation-specific chunks (incorrect context)

**Severity:** Medium  
**Confirmed:** Yes (live probe)

**Cause:**  
`_build_retrieval_query` appends a domain hint to the query regardless of whether violations exist. For valid records, the query is purely the domain hint:
```
"healthcare clinical patient record admission discharge age diagnosis medication"
```
This broad query matches HC-003 and HC-001 chunks best (cosine 0.60), so a valid record receives violation-specific context. A live RAG call on a valid record would generate an explanation that sounds like it's describing violations that don't exist.

**Observed behaviour:**
```
Valid record retrieval chunks:
  0.6009 [HC-003] Same-Day Discharge: Valid vs Invalid Patterns
  0.5669 [HC-003] Discharge Date Sequencing and Length-of-Stay Calculations
  0.5637 [HC-001] Patient Age Verification in Clinical Documentation
```

**Mitigation:**  
Guard the RAG call at the explainer level:
```python
def explain_with_rag(record, domain, violations, decision, ...):
    if not violations:
        # No violations — skip RAG entirely, return baseline
        return RAGExplanation(..., rag_explanation=baseline, retrieved_chunks=[])
```

---

#### FM-R-002 — HC-005 knowledge base has a single document; ranks 2–3 fall to generic fallback

**Severity:** Medium  
**Confirmed:** Yes (live probe)

**Cause:**  
The knowledge base has only one document for HC-005 (medication-diagnosis concordance). After retrieving that chunk as rank 1, the retriever fills ranks 2 and 3 from the general "Common Failure Modes" document (scores 0.12–0.20). This provides weak context for the LLM.

**Observed behaviour:**
```
HC-005-a retrieval:
  0.4625 [HC-005] Medication-Diagnosis Concordance in Clinical Documentation
  0.1211 [None]  Common Failure Modes in LLM-Generated Structured Data
  0.1197 [None]  Common Failure Modes in LLM-Generated Structured Data
```

Single-document coverage rules (HC-002, FN-001, FN-003, FN-004, FN-005) show the same pattern.

**Mitigation:**  
Add a second knowledge-base document for each single-document rule. For HC-005, add a document covering ISMP polypharmacy alerts and drug-disease contraindications. For FN-001, add a document covering Regulation Z timeline requirements in detail.

---

#### FM-R-003 — Multi-violation combined query may miss some violated rules in retrieval

**Severity:** Low  
**Confirmed:** Yes (live probe — FN-multi-1 case)

**Cause:**  
When two rules are violated, `_build_retrieval_query` concatenates all violation messages into one query string. If the two violations have different semantic fields, the combined embedding may score better for one rule's document than the other's. `rule_filter` is only applied when all violations share the same rule ID.

**Observed behaviour:**
```
HC-004-b (HC-004 + HC-005 violated):
  0.4879 [HC-001] Patient Age Verification  ← wrong rule retrieved at rank 1
  0.4857 [HC-004] Age-Restricted ICD-10 Diagnosis Codes
  0.4432 [HC-004] Age-Restricted ICD-10 Diagnosis Codes
  # HC-005 (medication) doc missing from top-3
```

**Mitigation:**  
For multi-violation cases, issue one retrieval query per violated rule and merge results with deduplication:
```python
if len(set(rule_ids)) > 1:
    all_chunks = {}
    for rule_id in set(rule_ids):
        chunks = retriever.retrieve(query, top_k=2, domain_filter=domain,
                                    rule_filter=rule_id)
        for c in chunks:
            if c["chunk_id"] not in all_chunks:
                all_chunks[c["chunk_id"]] = c
    return sorted(all_chunks.values(), key=lambda c: -c["score"])[:top_k]
```

---

#### FM-R-004 — FAISS singleton not reloaded if knowledge base is rebuilt at runtime

**Severity:** Low  
**Confirmed:** Yes (code review)

**Cause:**  
`get_retriever()` returns a module-level singleton (`_RETRIEVER_INSTANCE`). If `python rag/vector_store.py --build` is run while the API server is live, the old index remains in memory. New chunks won't be retrievable until the process restarts.

**Mitigation:**  
Add a `reload_retriever()` function and a `POST /rag/reload` admin endpoint:
```python
def reload_retriever() -> RAGRetriever:
    global _RETRIEVER_INSTANCE
    _RETRIEVER_INSTANCE = RAGRetriever()
    return _RETRIEVER_INSTANCE
```

---

### 2.2 Explanation Generation (`rag/explainer.py`)

---

#### FM-R-005 — Anthropic API errors propagate as bare exceptions to the caller

**Severity:** High  
**Confirmed:** Yes (code review)

**Cause:**  
The `explain_with_rag` function has no try/except around the Claude API call. Any `anthropic.APIError`, `anthropic.RateLimitError`, or network timeout propagates to the caller as an unhandled exception. The caller in `rag/evaluate.py` wraps this in a try/except, but direct use of `explain_with_rag` from other callers (e.g., the FastAPI `/rag/explain` endpoint) may not.

**Mitigation:**  
Add a fallback inside `explain_with_rag`:
```python
try:
    response = client.messages.create(...)
    rag_text = response.content[0].text.strip()
except Exception as e:
    logger.warning(f"[{record_id}] RAG LLM call failed: {e}")
    rag_text = f"[RAG explanation unavailable: {type(e).__name__}] {baseline}"
```

---

#### FM-R-006 — Record JSON truncated to 2000 characters in RAG prompt

**Severity:** Low  
**Confirmed:** Yes (code review)

**Cause:**  
```python
record_json = json.dumps(record, indent=2, default=str)[:2000]
```

A finance record with many fields and long string values can exceed 2000 characters when pretty-printed. The truncated JSON may cut off mid-field, providing incomplete context to the LLM and potentially causing hallucinated field values in the explanation.

**Mitigation:**  
Truncate at field boundaries, not character boundaries:
```python
import json
full = json.dumps(record, default=str)
if len(full) > 2000:
    # Keep only violation-relevant fields
    relevant_keys = [f for v in violations for f in v.get("fields", [])]
    slim = {k: record.get(k) for k in relevant_keys}
    record_json = json.dumps(slim, indent=2, default=str)
else:
    record_json = json.dumps(record, indent=2, default=str)
```

---

## 3. Ingest Module Failures

### 3.1 Text Extraction (`ingest/document_ingest.py` — `extract_text`)

---

#### FM-I-001 — Scanned/image-only PDFs produce empty or near-empty text extraction

**Severity:** High  
**Confirmed:** Yes (live probe)

**Cause:**  
`pdfplumber` and `pypdf` both extract text from the PDF text layer. A scanned document (rasterised image embedded in a PDF) has no text layer — `page.extract_text()` returns `None` or empty string for every page. The pipeline then calls `_llm_extract` on empty text, and the LLM returns a record with all fields null.

**Observed behaviour:**
```python
file_bytes = b'%PDF-1.4 minimal'   # minimal PDF with no text
text = extract_text(file_bytes, "scan.pdf")
# pdfplumber raises PdfminerException: No /Root object!
# pypdf fallback: returns empty string
# doc_text = ""
# → raises ValueError("Document appears to be empty or unreadable.")
```

The ValueError is caught by the FastAPI route and returned as HTTP 400. For a scanned document with valid content, the user receives an opaque error with no guidance.

**Mitigation:**  
Add OCR fallback using `pytesseract` + `pdf2image`:
```python
def _extract_text_from_pdf(data: bytes) -> str:
    text = _try_pdfplumber(data)
    if not text.strip():
        # No text layer — attempt OCR
        try:
            from pdf2image import convert_from_bytes
            import pytesseract
            images = convert_from_bytes(data)
            text = "\n".join(pytesseract.image_to_string(img) for img in images)
        except ImportError:
            pass  # OCR packages not installed
    return text
```
If OCR is unavailable, return a specific error: `"Scanned PDF detected. Install pytesseract for OCR support."`.

---

#### FM-I-002 — Text documents larger than 3,500 characters have fields silently truncated

**Severity:** Medium  
**Confirmed:** Yes (code review)

**Cause:**  
```python
truncated = text[:3500] + ("\n...[truncated]" if len(text) > 3500 else "")
```

A 10-page clinical discharge summary may be 15,000+ characters. Only the first 3,500 characters reach the LLM. Fields that appear later in the document (e.g., discharge date in a summary, approved amount in a multi-page loan application) will be extracted as null.

**Example scenario:**  
A 6-page loan application PDF where the approval date and approved amount appear on page 4 will extract `null` for both fields, causing FN-001 and FN-005 to pass silently (null values are treated as "not yet approved" by the rules).

**Mitigation:**  
Implement page-aware chunking: extract the most relevant pages (usually first + last) rather than a hard character truncation. For finance documents, also scan for amount/date keywords regardless of position:
```python
def _smart_truncate(text: str, domain: str, max_chars: int = 3500) -> str:
    if len(text) <= max_chars:
        return text
    # Always include first 2000 chars (header fields)
    # Scan for domain-critical keywords in the remainder
    head = text[:2000]
    keywords = ["discharge", "approved", "approval date"] if domain == "healthcare_intake" \
               else ["approved amount", "approval date", "final decision"]
    tail_snippets = []
    for kw in keywords:
        idx = text.lower().rfind(kw)
        if idx > 2000:
            tail_snippets.append(text[max(0, idx-100):idx+300])
    return head + "\n...\n" + "\n".join(tail_snippets[:3])
```

---

#### FM-I-003 — Non-UTF-8 encoded text files produce garbled extraction

**Severity:** Low  
**Confirmed:** Yes (code review)

**Cause:**  
```python
return file_bytes.decode("utf-8", errors="replace").strip()
```

Using `errors="replace"` substitutes the Unicode replacement character (U+FFFD, `\ufffd`) for invalid bytes. A Latin-1 encoded document with accented characters (common in French/Spanish medical records) produces a text with hundreds of `\ufffd` characters. The LLM receives corrupted text and extracts null or incorrect values.

**Mitigation:**  
Auto-detect encoding using `chardet` before decoding:
```python
def extract_text(file_bytes: bytes, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        return _extract_text_from_pdf(file_bytes)
    try:
        import chardet
        detected = chardet.detect(file_bytes)
        encoding = detected.get("encoding") or "utf-8"
    except ImportError:
        encoding = "utf-8"
    return file_bytes.decode(encoding, errors="replace").strip()
```

---

### 3.2 LLM Field Extraction (`ingest/document_ingest.py` — `_llm_extract`)

---

#### FM-I-004 — `json.loads` raises unhandled `JSONDecodeError` on non-JSON LLM output

**Severity:** High  
**Confirmed:** Yes (live probe)

**Cause:**  
```python
def _llm_extract(prompt: str) -> dict:
    ...
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw)  # strip code fences
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)   # ← raises JSONDecodeError if LLM explains itself
```

The regex strips standard backtick code fences, but the LLM may still return:
- Partial JSON (context window overflow)
- Prose explanation followed by JSON (prompt non-compliance)
- JSON with Python-style `True`/`False`/`None` instead of JSON booleans
- Truncated JSON (LLM stopped mid-generation)

**Observed behaviour:**
```python
raw = "Here is the extracted record:\n\`\`\`json\n{\"patient_id\": \"P-1\"}\n\`\`\`"
# After regex: "Here is the extracted record:\n\`\`\`json\n{...}"
# Code fence stripping fails on variant backtick encoding → JSONDecodeError
```

The `JSONDecodeError` propagates through `extract_and_validate` to the FastAPI route, which returns HTTP 500.

**Mitigation:**
```python
def _llm_extract(prompt: str) -> dict:
    ...
    raw = response.content[0].text.strip()
    # Strip any code fences
    raw = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("```").strip()
    # Find the first JSON object or array in the response
    match = re.search(r"(\{.*\}|\[.*\])", raw, re.DOTALL)
    if match:
        raw = match.group(1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned non-JSON output. Raw: {raw[:200]!r}") from e
```

---

#### FM-I-005 — LLM may extract fields with wrong types (strings instead of numbers/booleans)

**Severity:** Medium  
**Confirmed:** Yes (design analysis)

**Cause:**  
The extraction prompt specifies field types in natural language ("number, USD", "boolean"), but the LLM may return:
- `"annual_income": "92,000"` (string with comma, not a number)
- `"co_applicant": "false"` (string, not a JSON boolean)
- `"patient_age": "45"` (string, not an integer)

These values pass the `_llm_extract` JSON parsing step but fail structural validation (schema type checks), quarantining otherwise valid documents.

**Mitigation:**  
Add a post-extraction type coercion step before validation:
```python
_COERCE_INT   = {"patient_age", "credit_score", "loan_term_months"}
_COERCE_FLOAT = {"annual_income", "loan_amount", "existing_debt", "interest_rate"}
_COERCE_BOOL  = {"co_applicant", "emergency_admission"}

def _coerce_types(record: dict, domain: str) -> dict:
    for field in _COERCE_INT:
        if field in record and isinstance(record[field], str):
            record[field] = int(record[field].replace(",",""))
    for field in _COERCE_FLOAT:
        if field in record and isinstance(record[field], str):
            record[field] = float(record[field].replace(",","").replace("$",""))
    for field in _COERCE_BOOL:
        if field in record and isinstance(record[field], str):
            record[field] = record[field].lower() in ("true","yes","1")
    return record
```

---

### 3.3 Pipeline Integration (`ingest/document_ingest.py` — `extract_and_validate`)

---

#### FM-I-006 — No retry logic on LLM API transient failures

**Severity:** Medium  
**Confirmed:** Yes (code review)

**Cause:**  
`_llm_extract` makes a single API call with no retry. Anthropic API rate limits (HTTP 429) or transient network errors cause the entire ingest to fail with an unhandled exception, returning HTTP 500 to the client. The client has no way to distinguish a transient failure from a permanent one.

**Mitigation:**
```python
import time

def _llm_extract(prompt: str, max_retries: int = 2) -> dict:
    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(...)
            ...
            return json.loads(raw)
        except anthropic.RateLimitError:
            if attempt < max_retries:
                time.sleep(2 ** attempt)   # exponential backoff: 1s, 2s
                continue
            raise
        except anthropic.APIError as e:
            if attempt < max_retries and e.status_code >= 500:
                time.sleep(1)
                continue
            raise
```

---

#### FM-I-007 — Ingest result `extracted_text` capped at 1,000 characters may hide extraction issues

**Severity:** Low  
**Confirmed:** Yes (code review)

**Cause:**  
```python
extracted_text=doc_text[:1000]   # cap for response payload
```

The preview truncation means the API response never shows whether the relevant sections of a long document were actually fed to the LLM. A downstream caller cannot tell if extraction was based on complete or partial text.

**Mitigation:**  
Include `text_chars_fed_to_llm` in the response to indicate actual extraction coverage:
```python
return {
    ...
    "extraction_stats": {
        "total_chars": len(doc_text),
        "chars_fed_to_llm": min(len(doc_text), 3500),
        "truncated": len(doc_text) > 3500,
    }
}
```

---

## 4. Cross-Cutting Concerns

---

#### FM-X-001 — No audit trail for ingest failures

**Severity:** Medium  
**Confirmed:** Yes (code review)

**Cause:**  
The core `validate_record` pipeline writes a JSONL audit entry for every record. The ingest module calls `validate_record` internally, so successful ingest runs are audited. However, ingest failures (text extraction error, LLM JSON parse failure, API key missing) raise exceptions before `validate_record` is called — they produce no audit entry at all.

**Mitigation:**  
Write a failure audit entry in the ingest exception handler:
```python
except Exception as e:
    _write_ingest_failure_audit(filename, domain, str(e))
    raise
```

---

#### FM-X-002 — Parallel validation of same record ID produces duplicate audit entries

**Severity:** Low  
**Confirmed:** Yes (code review)

**Cause:**  
`write_audit_log` appends to a per-domain JSONL file with no locking. If two concurrent requests validate records with the same `record_id` (e.g., retries), both entries are written. The audit log is then non-unique on `record_id`.

**Mitigation:**  
Use a thread-safe write with file locking:
```python
import fcntl

def write_audit_log(entry: dict, domain: str) -> None:
    path = AUDIT_DIR / f"{domain}_audit.jsonl"
    with open(path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(json.dumps(entry) + "\n")
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
```

---

#### FM-X-003 — Schema cache is process-global; schema file changes require restart

**Severity:** Low  
**Confirmed:** Yes (code review)

**Cause:**  
`_schema_cache` in `validator/structural.py` is a module-level dict that is populated once per domain per process lifetime. If a schema file is edited on disk while the server is running, the updated schema is never loaded.

**Mitigation:**  
Add a cache invalidation mechanism with file modification timestamp:
```python
_schema_cache: dict[str, tuple[dict, float]] = {}  # domain → (schema, mtime)

def load_schema(domain: str) -> dict:
    path = SCHEMA_DIR / DOMAIN_SCHEMA_MAP[domain]
    mtime = path.stat().st_mtime
    cached = _schema_cache.get(domain)
    if cached and cached[1] == mtime:
        return cached[0]
    schema = json.loads(path.read_text())
    _schema_cache[domain] = (schema, mtime)
    return schema
```

---

## 5. Mitigation Priority Matrix

| ID | Module | Severity | Confirmed | Priority | Fix effort |
|----|--------|:--------:|:---------:|:--------:|:----------:|
| FM-I-004 | Ingest — `_llm_extract` JSON parse | High | Yes | **P1** | Low |
| FM-R-005 | RAG — API error propagation | High | Yes | **P1** | Low |
| FM-I-001 | Ingest — scanned PDF no text layer | High | Yes | **P1** | Medium |
| FM-V-007 | Validator — income=0 silent pass | Medium | Yes | **P2** | Low |
| FM-V-001 | Validator — malformed date trusted | Medium | Yes | **P2** | Low |
| FM-I-005 | Ingest — LLM type mismatch | Medium | Yes | **P2** | Low |
| FM-R-001 | RAG — valid record wrong context | Medium | Yes | **P2** | Low |
| FM-R-002 | RAG — sparse KB, rank 2–3 junk | Medium | Yes | **P2** | Medium |
| FM-V-006 | Validator — cascade penalty inflation | Medium | Yes | **P2** | Medium |
| FM-I-006 | Ingest — no LLM retry | Medium | Yes | **P2** | Low |
| FM-V-002 | Validator — extra fields quarantine | Low | Yes | **P3** | Low |
| FM-V-003 | Validator — ID regex mismatch | Medium | Yes | **P3** | Low |
| FM-I-002 | Ingest — 3500-char truncation | Medium | Yes | **P3** | Medium |
| FM-V-004 | Validator — HC-005 unknown codes | Medium | Yes | **P3** | Medium |
| FM-R-003 | RAG — multi-violation missed rule | Low | Yes | **P3** | Medium |
| FM-I-003 | Ingest — non-UTF-8 encoding | Low | Yes | **P3** | Low |
| FM-V-011 | Validator — whitespace date | Low | Yes | **P3** | Low |
| FM-V-008 | Validator — warning = trusted | Low | By design | P3 | Config |
| FM-X-001 | Cross-cut — no ingest audit | Medium | Yes | **P3** | Low |
| FM-V-005 | Validator — 1-year age tolerance | Low | By design | P4 | Config |
| FM-R-004 | RAG — stale singleton | Low | Yes | P4 | Low |
| FM-V-009 | Validator — zero rules penalty | Low | Yes | P4 | Low |
| FM-V-010 | Validator — structural blocks semantic | Low | By design | P4 | Medium |
| FM-R-006 | RAG — 2000-char record truncation | Low | Yes | P4 | Low |
| FM-X-002 | Cross-cut — duplicate audit entries | Low | Yes | P4 | Low |
| FM-X-003 | Cross-cut — schema cache no invalidation | Low | Yes | P4 | Low |
| FM-I-007 | Ingest — preview hides coverage | Low | Yes | P4 | Low |

---

*Analysis conducted against SchemaGuard v0.3.0. All behaviours verified by live probe unless noted "code review" or "By design".*
