# LinkedIn Post — SchemaGuard

---

## Post

LLMs can generate perfect-looking JSON that is completely wrong.

A healthcare record where the patient was discharged a week before being admitted. A loan approval for 52x someone's annual income. Every field has the right type. Every format checks out. Schema validation says it's fine.

But it's not fine. These silent failures flow straight into production databases.

I built **SchemaGuard** to fix this.

It's a semantic validation and drift detection layer that sits between LLM output and any consuming system. Every record goes through:

→ Structural check (JSON schema enforcement)
→ Semantic check (10 cross-field rules across healthcare and finance)
→ Confidence scoring (severity-weighted, 0 to 1)
→ Decision routing (trusted / flagged / quarantined)

The system also monitors output distributions over time. If an LLM starts generating younger patients, higher incomes, or fewer edge cases — the drift detector catches it before it becomes a data quality problem.

A few things I'm proud of in the design:

• Every decision is deterministic and auditable — same input, same output, full rule trace. No black-box LLM classification.
• Confidence scoring isn't binary pass/fail — it's a continuous score that lets downstream systems handle different risk tiers differently.
• The architecture is domain-agnostic. Adding a new domain means adding a schema file and a rules file. Everything else works unchanged.

Built with Python, FastAPI, Streamlit, and jsonschema. 100% classification accuracy on seed evaluation data. All simulated drift shifts detected.

If you're deploying LLMs for structured data generation and relying solely on schema validation — you're missing the layer that catches the errors that actually matter.

GitHub: github.com/PragatiAN1109/schema-guard-llm-validation

#SoftwareEngineering #LLM #DataQuality #Python #FastAPI #AIEngineering #BackendDevelopment

---

## Shorter Version (if needed)

I built SchemaGuard — a semantic validation layer for LLM-generated JSON outputs.

The problem: LLMs generate structurally valid records with logical contradictions. A discharge before admission. A $2.5M loan on $48K income. Schema validation passes all of them.

SchemaGuard catches them with cross-field semantic rules, confidence scoring, drift detection, and three-tier routing (trusted / flagged / quarantined).

10 rules, 2 domains, 100% accuracy on evaluation data. Python + FastAPI + Streamlit.

github.com/PragatiAN1109/schema-guard-llm-validation
