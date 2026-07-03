---
title: "RAG Reference"
tags: [ai, machinelearning, meta]
---

# RAG Reference

RAG (Retrieval-Augmented Generation) grounds LLM responses in external documents rather than relying on parametric memory alone. It reduces hallucinations for factual queries and keeps responses current without retraining.

## Pipeline

```
Query → [Embedder] → query vector
                          ↓
            [Vector store] similarity search
                          ↓
                   top-k documents
                          ↓
[Prompt builder] — context + query → LLM → response
```

### 1. Ingestion (offline)
- Load source documents
- **Chunk** into segments (typically 200–800 tokens)
- **Embed** each chunk with an embedding model → dense vector
- **Store** vectors in a vector database (ChromaDB, Qdrant, Weaviate, Pinecone)

### 2. Retrieval (online, per query)
- Embed the query with the same embedding model
- Find the k nearest chunks by cosine similarity
- Optionally re-rank with a cross-encoder for precision
- Return top-k chunks as context

### 3. Generation
- Build a prompt: `[system] + [retrieved context] + [user query]`
- LLM generates a response grounded in the retrieved context

## Chunking Strategies

**Fixed-size** — split every N characters with M overlap. Simple but may split mid-sentence or mid-concept.

**Semantic / header-based** — split at natural boundaries (markdown headers, paragraph breaks). Better for structured documents.

**Recursive character splitting** — tries larger boundaries first (paragraphs), falls back to smaller (sentences, then characters) to respect size limits.

## Sparse vs Dense Retrieval

**Dense retrieval** (embeddings) — captures semantic similarity. "What is gradient descent?" can retrieve content about "optimisation algorithms" even without word overlap. Requires embedding model.

**Sparse retrieval** (BM25/TF-IDF) — keyword-based. Fast, no embedding needed, excels at exact-match and rare-term lookups. Fails on paraphrases.

**Hybrid** — combine both signals. Sparse for recall of exact terms, dense for semantic coverage. Re-ranker selects final top-k.

## Embedding Models

An embedding model converts text into a dense vector in a high-dimensional space (typically 768–4096 dims). Similar texts → nearby vectors.

Key properties:
- **nomic-embed-text** (local, free, strong) — used in this vault
- **text-embedding-3-small** (OpenAI) — strong, API-only
- **all-MiniLM-L6-v2** — small, fast, good for sentence similarity

The query and document embeddings **must come from the same model**. Changing the embedding model requires re-ingesting all documents.

## Limitations

- **Context window** — retrieved chunks must fit in the LLM's context. Top-k must be tuned.
- **Chunk boundary sensitivity** — a key fact split across two chunks may be retrieved partially.
- **Stale index** — if source documents update, the vector store must be re-ingested.
- **Retrieval failures** — if the right chunk isn't in the top-k, the LLM can't answer correctly regardless of how good it is.

## Similarity Score Interpretation

Cosine similarity in RAG is model-dependent. For nomic-embed-text, rough thresholds:
- ≥ 0.7 — strong topical match
- 0.5–0.7 — relevant, likely on-topic
- < 0.5 — marginal; consider falling back to model knowledge

## See Also

- [[Retrieval Augmentation Models]]
- [[Sparse vs Dense Retrieval]]
- [[Embedding Models]]
- [[Language Models]]
- [[Vector Databases for Search]]
