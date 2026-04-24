# Product Overview — SchemaGuard

## What It Is

SchemaGuard is a validation-as-a-service platform for LLM-generated structured data. It catches semantic errors that schema validation misses, monitors output quality over time, and routes every record through a confidence-scored decision pipeline.

## Target Users

**ML/AI Engineering Teams** building data pipelines that consume LLM-generated JSON. They need assurance that outputs are not just structurally correct but logically coherent.

**Platform Engineering Teams** running multi-tenant LLM services where data quality directly impacts downstream consumers — databases, analytics, compliance reporting.

**Healthcare & Financial Services Teams** operating in regulated industries where data integrity is auditable and logical contradictions carry compliance risk.

## Use Cases

**LLM Output Validation** — Validate JSON records from GPT-4, Claude, Llama, or any LLM before they enter production databases. Catches temporal contradictions, ratio violations, and implausible field combinations.

**API Data Quality Gateway** — Sit between an LLM API and downstream consumers. Every response is scored, routed, and logged before reaching the consumer.

**Batch Processing QA** — Validate large batches of generated data with drift detection. Detect when model behavior shifts before it becomes a data quality incident.

**Compliance Audit Trail** — Every validation produces a deterministic, traceable result. Full audit logs with user, timestamp, rules evaluated, and confidence breakdown.

## How Companies Would Use This

### Integration Pattern
```
LLM API → SchemaGuard API → Downstream DB / Service
              │
              ├── trusted → auto-insert
              ├── flagged → human review queue
              └── quarantined → reject + alert
```

### Multi-Tenant Setup
- Each team gets API keys with per-user quotas
- Jobs are isolated by user — users only see their own results
- Usage tracking enables cost allocation per team
- Audit logs provide compliance visibility

## Monetization (SaaS Model)

| Tier | Validations/Month | Features | Price |
|------|-------------------|----------|-------|
| **Free** | 1,000 | Sync validation, 2 domains | $0 |
| **Pro** | 50,000 | Async pipeline, drift detection, batch | $49/mo |
| **Team** | 500,000 | Multi-user, quotas, audit logs, priority | $199/mo |
| **Enterprise** | Unlimited | Custom domains, SLA, SSO, dedicated support | Custom |

Revenue drivers: validation volume, number of custom domains, enterprise features (SSO, custom rules, SLA).

## Technical Differentiators

- **Deterministic rules** — same input always produces same output, unlike LLM-based classifiers
- **Continuous confidence** — not binary pass/fail; enables risk-tiered automation
- **Drift detection** — catches population-level shifts that per-record validation misses
- **Multi-signal monitoring** — z-score, PSI, null-rate, violation-rate
- **Domain-agnostic architecture** — add new domains with a schema + rules file; pipeline unchanged
- **Full audit trail** — per-request logging with user, payload, result, timing

## Architecture Highlights

| Layer | Technology | Production Replacement |
|-------|-----------|----------------------|
| API | FastAPI + token auth | API Gateway + JWT/OAuth |
| Queue | In-memory FIFO + retry | Kafka / SQS |
| Storage | Thread-safe dict | Redis + PostgreSQL |
| Analytics | In-memory tracker | ClickHouse / BigQuery |
| Rate Limiting | Sliding window | Redis / API Gateway |
| Audit | JSONL files | Elasticsearch / CloudTrail |
