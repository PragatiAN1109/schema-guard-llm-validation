"""
SchemaGuard RAG — Explanation Engine
=======================================
Generates augmented, context-grounded explanations for validation failures
by retrieving relevant knowledge-base chunks and calling Claude.

Two modes:
    baseline   — deterministic rule-based explanation (existing system)
    rag        — LLM-generated explanation grounded in retrieved context

Public API:
    explain_with_rag(record, domain, violations, decision) -> RAGExplanation
    explain_baseline(record, domain, violations, decision) -> str
"""

from __future__ import annotations
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ── data types ────────────────────────────────────────────────────────────────

@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id:   str
    domain:   str
    rule_id:  str | None
    title:    str
    source:   str
    text:     str
    score:    float


@dataclass
class RAGExplanation:
    record_id:        str
    domain:           str
    violated_rules:   list[str]
    decision:         str
    baseline:         str
    rag_explanation:  str
    retrieved_chunks: list[RetrievedChunk]
    retrieval_query:  str
    latency_ms:       float
    model:            str


# ── prompt template ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are SchemaGuard's clinical and financial data quality analyst.
You explain validation failures in structured records using precise, actionable language.
Your explanations are written for data engineers and compliance reviewers — not patients or borrowers.
Always cite the specific field values from the record that caused the failure.
Always reference the relevant regulation, standard, or clinical guideline from the provided context.
Be concise: 3–5 sentences per violation. Do not repeat the same point multiple times.
"""

RAG_PROMPT_TEMPLATE = """\
A {domain_label} record failed validation. Explain the failure clearly and suggest remediation.

RECORD (JSON):
{record_json}

VALIDATION RESULT:
- Decision       : {decision}
- Violated rules : {rules_list}
- Rule messages  : {rule_messages}

RETRIEVED REFERENCE CONTEXT:
{context}

TASK:
Write a clear, professional explanation of why this record failed validation.
For each violated rule:
  1. State exactly what is wrong — cite the specific field values from the record above
  2. Explain why it matters clinically or legally — cite the reference context
  3. Suggest a specific remediation step

Conclude with the overall data quality decision ({decision}) and what should happen next.

Write in plain English. Be specific. 3–5 sentences per violation maximum.
"""


# ── baseline explanation ──────────────────────────────────────────────────────

def explain_baseline(
    record: dict,
    domain: str,
    violations: list[dict],
    decision: str,
    record_id: str = "unknown",
) -> str:
    """Re-use the existing deterministic explanation builder."""
    from validator.explanation import build_explanation

    structural = {"valid": True, "errors": []}
    semantic   = {
        "valid":           len(violations) == 0,
        "violations":      violations,
        "rules_evaluated": len(violations),
    }
    return build_explanation(structural, semantic, decision, record_id)


# ── retrieval query builder ───────────────────────────────────────────────────

def _build_retrieval_query(domain: str, violations: list[dict]) -> str:
    parts = []
    for v in violations:
        parts.append(f"{v.get('rule_id','')} {v.get('rule_name','')} {v.get('message','')}")

    domain_hint = (
        "healthcare clinical patient record admission discharge age diagnosis medication"
        if "healthcare" in domain
        else "financial loan application income approval date employment debt income ratio"
    )
    parts.append(domain_hint)
    return " ".join(parts)[:500]


# ── RAG pipeline ──────────────────────────────────────────────────────────────

def explain_with_rag(
    record:     dict,
    domain:     str,
    violations: list[dict],
    decision:   str,
    record_id:  str = "unknown",
    top_k:      int = 3,
    dry_run:    bool = False,
) -> RAGExplanation:
    """
    Full RAG explanation pipeline:
      1. Build retrieval query from violations + record
      2. Retrieve top-k relevant knowledge chunks (cached singleton)
      3. Format augmented prompt
      4. Call Claude for grounded explanation
      5. Return structured RAGExplanation
    """
    from rag.vector_store import get_retriever

    t0 = time.perf_counter()

    # ── 1. retrieve ──────────────────────────────────────────────────────────
    query = _build_retrieval_query(domain, violations)

    retriever   = get_retriever()  # cached singleton — no reload
    rule_ids    = [v.get("rule_id") for v in violations if v.get("rule_id")]
    rule_filter = rule_ids[0] if len(set(rule_ids)) == 1 else None

    raw_chunks  = retriever.retrieve(query, top_k=top_k,
                                     domain_filter=domain, rule_filter=rule_filter)
    context_str = retriever.format_context(raw_chunks)

    retrieved = [
        RetrievedChunk(
            chunk_id=c["chunk_id"], doc_id=c["doc_id"],
            domain=c["domain"],    rule_id=c.get("rule_id"),
            title=c["title"],      source=c["source"],
            text=c["text"],        score=c["score"],
        )
        for c in raw_chunks
    ]

    # ── 2. baseline ───────────────────────────────────────────────────────────
    baseline = explain_baseline(record, domain, violations, decision, record_id)

    if dry_run:
        return RAGExplanation(
            record_id=record_id, domain=domain,
            violated_rules=[v.get("rule_id","?") for v in violations],
            decision=decision, baseline=baseline,
            rag_explanation="[dry run — no LLM call]",
            retrieved_chunks=retrieved, retrieval_query=query,
            latency_ms=round((time.perf_counter()-t0)*1000, 2),
            model="dry-run",
        )

    # ── 3. build prompt ───────────────────────────────────────────────────────
    domain_label = (
        "healthcare intake" if "healthcare" in domain else "financial loan application"
    )
    user_prompt = RAG_PROMPT_TEMPLATE.format(
        domain_label  = domain_label,
        record_json   = json.dumps(record, indent=2, default=str)[:2000],
        decision      = decision,
        rules_list    = ", ".join(v.get("rule_id","?") for v in violations) or "none",
        rule_messages = "\n".join(
            f"  {v.get('rule_id','?')}: {v.get('message','')}" for v in violations
        ) or "  (no violations)",
        context       = context_str,
    )

    # ── 4. call Claude ────────────────────────────────────────────────────────
    import anthropic
    client = anthropic.Anthropic()
    model  = "claude-opus-4-5"

    response = client.messages.create(
        model=model, max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    rag_text = response.content[0].text.strip()

    return RAGExplanation(
        record_id=record_id, domain=domain,
        violated_rules=[v.get("rule_id","?") for v in violations],
        decision=decision, baseline=baseline,
        rag_explanation=rag_text, retrieved_chunks=retrieved,
        retrieval_query=query,
        latency_ms=round((time.perf_counter()-t0)*1000, 2),
        model=model,
    )
