"""
SchemaGuard RAG — FAISS Vector Store
======================================
Embeds the chunk corpus using a lightweight sentence-transformer model,
stores vectors in a FAISS flat index, and persists both index and metadata
to disk so the store can be loaded without re-embedding on every startup.

Files written to rag/store/:
    index.faiss      — FAISS flat L2 index
    metadata.json    — parallel list of chunk dicts (without embeddings)
    manifest.json    — build metadata (model, chunk count, build timestamp)
"""

from __future__ import annotations
import json
import time
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

STORE_DIR  = Path(__file__).parent / "store"
INDEX_PATH = STORE_DIR / "index.faiss"
META_PATH  = STORE_DIR / "metadata.json"
MANIFEST   = STORE_DIR / "manifest.json"

EMBED_MODEL = "all-MiniLM-L6-v2"   # 22 MB, 384-dim, fast, good quality
EMBED_DIM   = 384

# Module-level singleton — avoids reloading the model on every call
_RETRIEVER_INSTANCE: "RAGRetriever | None" = None

def get_retriever() -> "RAGRetriever":
    """Return (or create) the module-level singleton RAGRetriever."""
    global _RETRIEVER_INSTANCE
    if _RETRIEVER_INSTANCE is None:
        _RETRIEVER_INSTANCE = RAGRetriever()
    return _RETRIEVER_INSTANCE


def _load_libs():
    """Lazy-import heavy libraries so the module is importable without them."""
    try:
        import faiss
        from sentence_transformers import SentenceTransformer
        import numpy as np
        return faiss, SentenceTransformer, np
    except ImportError as e:
        raise ImportError(
            f"RAG requires extra packages. Run:\n"
            f"  pip install faiss-cpu sentence-transformers\n"
            f"Original error: {e}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# BUILD
# ══════════════════════════════════════════════════════════════════════════════

def build_store(chunks: list[dict], verbose: bool = True) -> None:
    """
    Embed all chunks and write the FAISS index + metadata to disk.

    Args:
        chunks:  output of chunker.build_chunk_corpus()
        verbose: print progress
    """
    faiss, SentenceTransformer, np = _load_libs()
    STORE_DIR.mkdir(exist_ok=True)

    if verbose:
        print(f"  Building FAISS store: {len(chunks)} chunks")
        print(f"  Embedding model     : {EMBED_MODEL}")

    t0 = time.time()
    model = SentenceTransformer(EMBED_MODEL)
    texts = [c["text"] for c in chunks]

    if verbose:
        print(f"  Encoding…")

    embeddings = model.encode(
        texts, batch_size=32,
        show_progress_bar=verbose,
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype("float32")

    index = faiss.IndexFlatIP(EMBED_DIM)
    index.add(embeddings)
    faiss.write_index(index, str(INDEX_PATH))

    with open(META_PATH, "w") as f:
        json.dump([{k: v for k, v in c.items()} for c in chunks], f, indent=2)

    with open(MANIFEST, "w") as f:
        json.dump({
            "model":    EMBED_MODEL,
            "dim":      EMBED_DIM,
            "n_chunks": len(chunks),
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "elapsed_s": round(time.time() - t0, 2),
        }, f, indent=2)

    if verbose:
        print(f"  Saved: {INDEX_PATH}")
        print(f"  Saved: {META_PATH}")
        print(f"  Done in {time.time()-t0:.1f}s")


# ══════════════════════════════════════════════════════════════════════════════
# RETRIEVE
# ══════════════════════════════════════════════════════════════════════════════

class RAGRetriever:
    """
    Loads the persisted FAISS index and performs nearest-neighbour retrieval.

    Usage:
        retriever = get_retriever()   # cached singleton
        chunks = retriever.retrieve("discharge before admission HC-003", top_k=3)
    """

    def __init__(self) -> None:
        if not INDEX_PATH.exists():
            raise FileNotFoundError(
                f"FAISS index not found at {INDEX_PATH}. "
                "Run: python rag/vector_store.py --build"
            )

        faiss, SentenceTransformer, np = _load_libs()
        self._faiss  = faiss
        self._np     = np
        self._index  = faiss.read_index(str(INDEX_PATH))

        with open(META_PATH) as f:
            self._chunks = json.load(f)

        self._model = SentenceTransformer(EMBED_MODEL)

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        domain_filter: str | None = None,
        rule_filter: str | None = None,
    ) -> list[dict]:
        """
        Retrieve the top-k most relevant chunks for a query.

        Args:
            query:         natural-language retrieval query
            top_k:         number of chunks to return
            domain_filter: restrict to this domain (also passes "general" chunks)
            rule_filter:   prefer chunks for this rule ID

        Returns:
            list of chunk dicts, each augmented with a "score" field
        """
        np = self._np

        q_vec = self._model.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).astype("float32")

        k_search = top_k * 4 if (domain_filter or rule_filter) else top_k
        scores, indices = self._index.search(q_vec, min(k_search, len(self._chunks)))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            chunk = dict(self._chunks[idx])
            chunk["score"] = float(score)

            if domain_filter:
                if chunk["domain"] not in (domain_filter, "general"):
                    continue
            if rule_filter:
                if chunk["rule_id"] is not None and chunk["rule_id"] != rule_filter:
                    continue

            results.append(chunk)
            if len(results) >= top_k:
                break

        return results

    def format_context(self, chunks: list[dict]) -> str:
        """Format retrieved chunks into a context block for prompt injection."""
        parts = []
        for i, chunk in enumerate(chunks, 1):
            rule_tag = f"[{chunk['rule_id']}] " if chunk["rule_id"] else ""
            parts.append(
                f"--- Reference {i}: {rule_tag}{chunk['title']} ---\n"
                f"Source: {chunk['source']}\n\n"
                f"{chunk['text']}"
            )
        return "\n\n".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--build",  action="store_true")
    parser.add_argument("--query",  type=str)
    parser.add_argument("--top-k",  type=int, default=3)
    args = parser.parse_args()

    if args.build:
        from rag.knowledge_base import KNOWLEDGE_BASE
        from rag.chunker import build_chunk_corpus
        chunks = build_chunk_corpus(KNOWLEDGE_BASE)
        print(f"Chunked → {len(chunks)} chunks")
        build_store(chunks)

    if args.query:
        r = get_retriever()
        for res in r.retrieve(args.query, top_k=args.top_k):
            print(f"  [{res['score']:.4f}] {res['chunk_id']} — {res['title'][:55]}")
            print(f"           rule={res['rule_id']}  {res['text'][:100]}…\n")
