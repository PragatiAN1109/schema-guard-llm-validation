"""
SchemaGuard RAG — Document Chunker
====================================
Splits knowledge-base documents into overlapping chunks of 300–500 tokens,
preserving metadata for retrieval attribution.

Each chunk:
    {
        "chunk_id":   str,
        "doc_id":     str,
        "domain":     str,
        "rule_id":    str | None,
        "title":      str,
        "source":     str,
        "text":       str,         # the actual chunk content
        "char_start": int,
        "char_end":   int,
    }
"""

from __future__ import annotations
import re
import uuid
from typing import Iterator


# ── tunables ──────────────────────────────────────────────────────────────────
TARGET_TOKENS  = 400      # target chunk size in tokens (rough: 1 token ≈ 4 chars)
OVERLAP_TOKENS = 60       # overlap between consecutive chunks
CHARS_PER_TOK  = 4        # approximation


def _rough_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOK


def _split_sentences(text: str) -> list[str]:
    """Split on sentence boundaries, keeping the delimiter."""
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


def chunk_document(doc: dict) -> list[dict]:
    """
    Chunk a single knowledge-base document into overlapping segments.

    Strategy:
      1. Clean and normalise whitespace
      2. Split into sentences
      3. Greedily pack sentences into chunks up to TARGET_TOKENS
      4. Add OVERLAP_TOKENS of the previous chunk to each new chunk
    """
    text = re.sub(r'\n{3,}', '\n\n', doc["content"].strip())
    sentences = _split_sentences(text)

    chunks: list[dict] = []
    buffer: list[str] = []
    buffer_tokens = 0
    overlap_buffer: list[str] = []

    def _flush(buf: list[str], start_char: int, end_char: int) -> dict:
        chunk_text = " ".join(buf)
        return {
            "chunk_id":   f"{doc['doc_id']}-c{len(chunks):03d}",
            "doc_id":     doc["doc_id"],
            "domain":     doc["domain"],
            "rule_id":    doc.get("rule_id"),
            "title":      doc["title"],
            "source":     doc["source"],
            "text":       chunk_text,
            "char_start": start_char,
            "char_end":   end_char,
        }

    char_cursor = 0

    for sent in sentences:
        sent_tokens = _rough_tokens(sent)

        # If adding this sentence would overflow the chunk, flush first
        if buffer_tokens + sent_tokens > TARGET_TOKENS and buffer:
            chunks.append(_flush(buffer, char_cursor - buffer_tokens * CHARS_PER_TOK, char_cursor))
            # keep tail of buffer as overlap for next chunk
            overlap_tokens = 0
            overlap_buf = []
            for s in reversed(buffer):
                t = _rough_tokens(s)
                if overlap_tokens + t <= OVERLAP_TOKENS:
                    overlap_buf.insert(0, s)
                    overlap_tokens += t
                else:
                    break
            buffer = overlap_buf
            buffer_tokens = overlap_tokens

        buffer.append(sent)
        buffer_tokens += sent_tokens
        char_cursor += len(sent) + 1

    # flush remaining
    if buffer:
        chunks.append(_flush(buffer, char_cursor - buffer_tokens * CHARS_PER_TOK, char_cursor))

    return chunks


def build_chunk_corpus(knowledge_base: list[dict]) -> list[dict]:
    """Chunk all documents in the knowledge base and return flat list."""
    all_chunks = []
    for doc in knowledge_base:
        all_chunks.extend(chunk_document(doc))
    return all_chunks


# ── CLI helper ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from rag.knowledge_base import KNOWLEDGE_BASE
    chunks = build_chunk_corpus(KNOWLEDGE_BASE)

    print(f"Chunked {len(KNOWLEDGE_BASE)} documents → {len(chunks)} chunks\n")
    # Print chunk size distribution
    sizes = [_rough_tokens(c["text"]) for c in chunks]
    print(f"Chunk sizes: min={min(sizes)}  max={max(sizes)}  avg={sum(sizes)//len(sizes)} tokens")
    print()
    for c in chunks[:3]:
        print(f"[{c['chunk_id']}] {c['title'][:60]}")
        print(f"  rule_id={c['rule_id']}  tokens≈{_rough_tokens(c['text'])}")
        print(f"  {c['text'][:120]}…")
        print()
