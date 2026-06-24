---
chat_model: llama3.2:3b
coding_model: qwen2.5-coder:7b
embed_model: nomic-embed-text
---

# Models

| Role | Key | Purpose |
|---|---|---|
| `chat_model` | live streaming responses | Fast — latency matters more than depth |
| `coding_model` | /organize, /update patch proposals, concept suggestions | Slow OK — quality and instruction-following matter |
| `embed_model` | vault ingestion and similarity search | Must match the model used when the DB was built |

## Notes

- Swap `coding_model` to `deepseek-coder-v2` or `llama3.1:8b` if qwen2.5-coder is unavailable.
- Changing any model here takes effect on next launch. Run `/ingest` after changing `embed_model`.
