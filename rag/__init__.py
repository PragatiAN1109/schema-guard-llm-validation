# rag/__init__.py
"""
SchemaGuard RAG Module
=======================
Retrieval-Augmented Generation for validation failure explanations.

Modules:
    knowledge_base  — synthetic clinical/financial reference documents
    chunker         — splits documents into ~400-token overlapping chunks
    vector_store    — FAISS index builder and retriever
    explainer       — RAG explanation pipeline (retrieval + LLM call)
    api_routes      — FastAPI router for /rag/* endpoints
    evaluate        — qualitative comparison: baseline vs RAG

Quick start:
    # 1. Build the FAISS index (one-time, ~10 seconds)
    python rag/vector_store.py --build

    # 2. Test retrieval
    python rag/vector_store.py --query "discharge date before admission"

    # 3. Generate a RAG explanation
    python rag/evaluate.py --demo

    # 4. Wire into FastAPI (already done in api/main.py)
    # GET /rag/status
    # POST /rag/explain
    # POST /rag/search
"""
