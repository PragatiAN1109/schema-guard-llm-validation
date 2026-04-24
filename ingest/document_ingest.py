"""
SchemaGuard — Document Ingestion
==================================
Upload a PDF or plain-text document, extract structured JSON using Claude,
then run it through the SchemaGuard validation pipeline.

Public API:
    extract_and_validate(file_bytes, filename, domain) -> IngestResult
"""

from __future__ import annotations
import json, os, re, time
from dataclasses import dataclass
from pathlib import Path

# ── text extraction ──────────────────────────────────────────────────────────

def _extract_text_from_pdf(data: bytes) -> str:
    """Extract all text from a PDF using pdfplumber (falls back to pypdf)."""
    try:
        import pdfplumber, io
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join(
                (page.extract_text() or "") for page in pdf.pages
            ).strip()
    except ImportError:
        pass
    try:
        import pypdf, io
        reader = pypdf.PdfReader(io.BytesIO(data))
        return "\n".join(
            (page.extract_text() or "") for page in reader.pages
        ).strip()
    except ImportError:
        raise RuntimeError(
            "No PDF library found. Run: pip install pdfplumber"
        )


def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Extract plain text from an uploaded file.
    Supports: .pdf, .txt, .md, and any UTF-8 text file.
    """
    name = filename.lower()
    if name.endswith(".pdf"):
        return _extract_text_from_pdf(file_bytes)
    # Assume UTF-8 text for everything else
    return file_bytes.decode("utf-8", errors="replace").strip()


# ── domain field maps ────────────────────────────────────────────────────────

_HC_FIELDS = """
  patient_id (string, e.g. "P-1234"),
  first_name (string), last_name (string),
  date_of_birth (YYYY-MM-DD), gender ("male"/"female"/"other"),
  admission_date (YYYY-MM-DD), discharge_date (YYYY-MM-DD),
  diagnosis_code (ICD-10, e.g. "J18.9"),
  diagnosis_description (string),
  treating_physician (string, e.g. "Dr. Jane Smith"),
  medication (string or null),
  procedure_code (string or null),
  insurance_provider (string or null),
  patient_age (integer),
  emergency_admission (boolean),
  notes (string or null)
"""

_FN_FIELDS = """
  application_id (string, e.g. "LA-1234"),
  applicant_name (string),
  date_of_birth (YYYY-MM-DD),
  annual_income (number, USD),
  employment_status ("employed"/"self_employed"/"unemployed"/"retired"),
  employer_name (string or null),
  employment_length_years (number or null),
  loan_amount (number, USD),
  loan_purpose ("home_purchase"/"auto"/"personal"/"education"/"business"/"refinance"/"debt_consolidation"),
  loan_term_months (integer),
  interest_rate (number, percentage),
  credit_score (integer),
  existing_debt (number, USD),
  application_date (YYYY-MM-DD),
  approval_date (YYYY-MM-DD or null),
  approved_amount (number or null),
  property_value (number or null),
  co_applicant (boolean),
  notes (string or null)
"""

_DOMAIN_FIELDS = {
    "healthcare_intake": _HC_FIELDS,
    "financial_loan_application": _FN_FIELDS,
}

_DOMAIN_EXAMPLE = {
    "healthcare_intake": "a patient intake form, discharge summary, or clinical note",
    "financial_loan_application": "a loan application form, credit document, or financial statement",
}


def _build_extraction_prompt(text: str, domain: str) -> str:
    fields = _DOMAIN_FIELDS[domain]
    example = _DOMAIN_EXAMPLE.get(domain, "a structured document")
    # Keep document text to a safe length
    truncated = text[:3500] + ("\n...[truncated]" if len(text) > 3500 else "")
    return f"""You are a data extraction assistant. Extract structured fields from the document below.

The document is {example}. Extract ALL of the following fields as a single JSON object.
- If a field is missing or cannot be inferred, use null.
- For dates, use YYYY-MM-DD format.
- Output ONLY a valid JSON object — no markdown, no commentary, no explanation.

FIELDS TO EXTRACT:
{fields}

DOCUMENT:
{truncated}

JSON:"""


# ── LLM extraction ───────────────────────────────────────────────────────────

def _llm_extract(prompt: str) -> dict:
    """Call Claude to extract JSON from the document text."""
    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    # Strip markdown code fences if the model added them
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


# ── result dataclass ─────────────────────────────────────────────────────────

@dataclass
class IngestResult:
    filename:         str
    domain:           str
    extracted_text:   str
    extracted_record: dict
    validation:       dict      # full SchemaGuard result
    latency_ms:       float


# ── main entry point ─────────────────────────────────────────────────────────

def extract_and_validate(
    file_bytes: bytes,
    filename:   str,
    domain:     str,
) -> IngestResult:
    """
    Full pipeline:
      1. Extract text from file (PDF or plain text)
      2. Call Claude to extract structured JSON fields
      3. Run SchemaGuard validation pipeline on the extracted record
      4. Return IngestResult with everything

    Args:
        file_bytes: raw bytes of the uploaded file
        filename:   original filename (used to detect PDF vs text)
        domain:     "healthcare_intake" or "financial_loan_application"
    """
    from config import resolve_domain
    from validator.pipeline import validate_record

    canonical = resolve_domain(domain)
    if not canonical:
        raise ValueError(f"Unknown domain: {domain!r}")

    t0 = time.perf_counter()

    # 1. Extract text
    doc_text = extract_text(file_bytes, filename)
    if not doc_text:
        raise ValueError("Document appears to be empty or unreadable.")

    # 2. LLM extraction
    prompt = _build_extraction_prompt(doc_text, canonical)
    record = _llm_extract(prompt)

    # 3. SchemaGuard validation
    validation = validate_record(record, canonical)

    return IngestResult(
        filename=filename,
        domain=canonical,
        extracted_text=doc_text[:1000],   # cap for response payload
        extracted_record=record,
        validation=validation,
        latency_ms=round((time.perf_counter() - t0) * 1000, 2),
    )
