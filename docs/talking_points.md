# Interview Talking Points — SchemaGuard

## Design Decisions

**Why a rule engine instead of ML classification?**
Deterministic rules give reproducible results with full audit trails. In healthcare and finance, you need the same input to always produce the same output. An LLM classifier might achieve similar accuracy, but it can't be formally verified or provide rule-level traceability.

**Why two validation layers (structural + semantic)?**
They catch different failure modes. Structural validation catches type errors, missing fields, and format mismatches — fast and cheap. Semantic validation catches logical contradictions between fields — requires domain knowledge. Running semantic checks only after structural passes avoids wasting computation on malformed records.

**Why continuous confidence scoring instead of binary pass/fail?**
A record with one warning-level violation (confidence 0.88) is fundamentally different from a record with three critical violations (confidence 0.10). The continuous score preserves that gradient and enables three-tier routing. Downstream systems can handle each tier differently based on their risk tolerance.

**Why three decision tiers?**
Trusted records flow through automatically. Quarantined records are blocked. Flagged records go to a review queue. This matches real-world operational patterns — you rarely want pure binary accept/reject in production.

**Why drift detection as a separate module?**
Single-record validation catches per-record errors. But if an LLM gradually shifts its output distribution — younger patients, higher incomes, fewer edge cases — no individual record looks wrong. Drift detection catches population-level degradation that per-record checks miss.

## Tradeoffs

**Rule coverage vs. simplicity:** 10 rules across 2 domains is enough to demonstrate the system without overcomplicating it. In production, you'd add dozens more rules per domain, but the architecture scales — each rule is an independent function.

**Seed data vs. LLM-generated data:** 16 hand-labeled records give perfect control over what's being tested. The metrics are meaningful on this set. A larger LLM-generated dataset would provide statistical power but introduces labeling noise. The architecture supports both — the prompt templates are ready.

**Fixed thresholds vs. learned thresholds:** Scoring uses fixed severity weights (critical: -0.30, warning: -0.12). In a production system, you'd calibrate these from labeled data. For this scope, fixed weights are transparent and defensible.

**jsonschema fallback:** The structural validator tries to use the `jsonschema` library, but falls back to a built-in validator if it's not installed. This makes the system runnable with zero external dependencies at the cost of less thorough structural validation.

## Why This Architecture

**Modular packages:** schemas, rules, validator, drift, scoring, API, and UI are all separate. Adding a third domain means adding two files — a schema and a rules file. Everything else works unchanged. This is the kind of separation of concerns that scales.

**Decorator-based rule registration:** Rules are just Python functions with `@register_rule`. No configuration files, no separate registration step, no ORM. The registry groups by domain automatically.

**Provider-agnostic LLM integration:** The generation pipeline doesn't hard-code OpenAI or Anthropic. The abstraction layer accepts any provider. Prompt templates are stored as markdown files, not embedded in code.

**Config centralization:** All thresholds live in `config.py` and are overridable via environment variables. No magic numbers scattered across modules.

## Limitations

- Seed dataset is small (16 records) — metrics need validation on larger datasets
- Medication plausibility (HC-005) only covers 7 ICD-10 categories
- DTI rule (FN-003) uses a fixed threshold regardless of loan type
- Drift baseline with 3 records has high variance — noisy for categorical fields
- No real-time streaming — batch mode only
- LLM provider not connected — generation uses seed data

## Future Improvements

- Connect LLM API for full 300+ record dataset generation
- Add lightweight RAG for grounded explanation generation
- Calibrate scoring weights from labeled data
- Add loan-type-aware thresholds for finance rules
- Expand medication mapping for healthcare rules
- Containerize with Docker for production deployment
- Add CI/CD with automated test runs on push
- Build monitoring dashboard for drift alerts over time
