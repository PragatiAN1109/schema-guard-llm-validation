# Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| **Backend** | Python + FastAPI | Async support, auto OpenAPI docs, native Pydantic integration |
| **Schema validation** | Pydantic + jsonschema | Pydantic for Python internals, jsonschema for portable schema definitions |
| **Semantic rules** | Custom Python engine | Cross-field checks are deterministic functions — no DSL or external engine needed |
| **LLM integration** | Provider-agnostic abstraction | Thin wrapper supporting OpenAI, Anthropic, or local models without lock-in |
| **Demo UI** | Streamlit | Fastest path to a working demo with forms, JSON display, and charts |
| **Storage** | JSON files + SQLite | Zero-config, no external database server, clone-and-run setup |
| **Evaluation** | matplotlib + plotly | Static charts for reports, interactive charts for the UI |
| **Testing** | pytest | Standard, parameterized tests for rule engine coverage |
| **Vector store** | Chroma or FAISS (optional, future) | Only needed if RAG enhancement is implemented later |

## Not in the stack

No Docker, no Kubernetes, no Terraform, no external databases, no React frontend, no Celery, no Kafka. This is a solo project — the stack stays minimal and runs locally.
