"""
SchemaGuard — Synthetic Dataset Generator

Generates labeled records for healthcare and finance domains using LLM prompt templates.
Outputs labeled JSONL files for evaluation.

Usage:
    python generate_dataset.py --domain healthcare_intake --category valid --count 10
    python generate_dataset.py --domain financial_loan_application --category invalid --count 5 --rule FN-002
    python generate_dataset.py --domain healthcare_intake --category edge_case --count 5
"""

import json
import os
import uuid
import argparse
from pathlib import Path
from datetime import datetime


# --- Configuration ---

DOMAINS = ["healthcare_intake", "financial_loan_application"]
CATEGORIES = ["valid", "invalid", "edge_case"]
DIFFICULTIES = ["easy", "medium", "hard"]

PROMPT_DIR = Path(__file__).parent / "prompts"
DATASET_DIR = Path(__file__).parent / "datasets"
RAW_DIR = DATASET_DIR / "raw"
LABELED_DIR = DATASET_DIR / "labeled"

HEALTHCARE_RULES = ["HC-001", "HC-002", "HC-003", "HC-004", "HC-005"]
FINANCE_RULES = ["FN-001", "FN-002", "FN-003", "FN-004", "FN-005"]


# --- Prompt Loading ---

def load_prompt_template(domain: str, category: str) -> str:
    """Load the prompt template file for a given domain and category."""
    domain_prefix = "healthcare" if "healthcare" in domain else "finance"
    filename = f"{domain_prefix}_{category}.md"
    filepath = PROMPT_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Prompt template not found: {filepath}")
    return filepath.read_text()


def build_prompt(domain: str, category: str, rule_id: str = None, difficulty: str = "medium") -> str:
    """
    Build a complete prompt for the LLM from template + parameters.

    Returns the system prompt and user prompt as a tuple.
    """
    template = load_prompt_template(domain, category)

    # TODO: Parse template and fill in parameters
    # - For valid: select random age_range, gender, condition_hint / profile_type, loan_type
    # - For invalid: inject violation_instructions for the target rule_id + difficulty
    # - For edge_case: select edge_case_type and instructions

    return template


# --- LLM Integration (placeholder) ---

def call_llm(system_prompt: str, user_prompt: str) -> dict:
    """
    Call the LLM provider and return a parsed JSON record.

    TODO: Implement provider-agnostic LLM call.
    - Read LLM_PROVIDER and API key from environment
    - Send system + user prompt
    - Parse JSON response
    - Retry on parse failure (up to 3 attempts)
    """
    raise NotImplementedError("LLM integration not yet implemented. Use seed data for testing.")


# --- Record Labeling ---

def create_labeled_record(
    domain: str,
    category: str,
    record: dict,
    rule_id: str = None,
    difficulty: str = "n/a",
    notes: str = "",
) -> dict:
    """Wrap a generated record with metadata labels."""
    domain_prefix = "HC" if "healthcare" in domain else "FN"
    record_id = f"{domain_prefix}-gen-{uuid.uuid4().hex[:6]}"

    return {
        "record_id": record_id,
        "domain": domain,
        "category": category,
        "prompt_type": f"{domain_prefix.lower()}_{category}_{rule_id or 'base'}_{difficulty}",
        "llm_output_json": record,
        "structural_valid": True,  # All generated records should pass schema
        "semantic_valid": category != "invalid",
        "violated_rules": [rule_id] if (category == "invalid" and rule_id) else [],
        "difficulty": difficulty if category == "invalid" else "n/a",
        "notes": notes,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


# --- Output ---

def save_records(records: list[dict], domain: str, output_dir: Path = None):
    """Save labeled records to JSONL file."""
    if output_dir is None:
        output_dir = LABELED_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    domain_prefix = "healthcare" if "healthcare" in domain else "finance"
    filepath = output_dir / f"{domain_prefix}_labeled.jsonl"

    mode = "a" if filepath.exists() else "w"
    with open(filepath, mode) as f:
        for record in records:
            f.write(json.dumps(record) + "\n")

    print(f"Saved {len(records)} records to {filepath}")


# --- Main ---

def generate_batch(domain: str, category: str, count: int, rule_id: str = None, difficulty: str = "medium"):
    """
    Generate a batch of labeled records.

    Currently uses placeholder logic. Replace call_llm() with actual provider integration.
    """
    records = []

    for i in range(count):
        # Build prompt
        prompt = build_prompt(domain, category, rule_id=rule_id, difficulty=difficulty)

        # Call LLM (placeholder — will raise NotImplementedError)
        try:
            raw_record = call_llm(system_prompt="", user_prompt=prompt)
        except NotImplementedError:
            print(f"  [skip] LLM not configured. Record {i+1}/{count} skipped.")
            continue

        # Label and store
        labeled = create_labeled_record(
            domain=domain,
            category=category,
            record=raw_record,
            rule_id=rule_id,
            difficulty=difficulty,
        )
        records.append(labeled)

    if records:
        save_records(records, domain)

    return records


def main():
    parser = argparse.ArgumentParser(description="SchemaGuard synthetic data generator")
    parser.add_argument("--domain", required=True, choices=DOMAINS)
    parser.add_argument("--category", required=True, choices=CATEGORIES)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--rule", type=str, default=None, help="Target rule ID for invalid records")
    parser.add_argument("--difficulty", type=str, default="medium", choices=DIFFICULTIES)

    args = parser.parse_args()

    if args.category == "invalid" and not args.rule:
        print("Error: --rule is required when category is 'invalid'")
        return

    print(f"Generating {args.count} {args.category} records for {args.domain}...")
    generate_batch(
        domain=args.domain,
        category=args.category,
        count=args.count,
        rule_id=args.rule,
        difficulty=args.difficulty,
    )


if __name__ == "__main__":
    main()
