---
chat_model: llama3.2:3b
coding_model: qwen2.5-coder:7b
embed_model: nomic-embed-text
models:
  - llama3.2:3b
  - qwen2.5-coder:7b
  - nomic-embed-text
---

# Models

## Role assignments

| Role | Model | Purpose |
|---|---|---|
| `chat_model` | `llama3.2:3b` | Live streaming responses — speed over depth |
| `coding_model` | `qwen2.5-coder:7b` | `/organize`, `/update` patches, concept suggestions |
| `embed_model` | `nomic-embed-text` | Vault ingestion and similarity search |

## Installed models

Any model listed under `models:` in the frontmatter will be pulled automatically on next launch if it is not already available locally. Add a model here before assigning it to a role.

| Model | Size | Notes |
|---|---|---|
| `llama3.2:3b` | 2.0 GB | Fast chat model |
| `qwen2.5-coder:7b` | 4.7 GB | Coding and instruction-following |
| `nomic-embed-text` | 274 MB | Embedding — do not change without re-ingesting |

## Notes

- Role assignment and model list changes take effect on next launch.
- Run `/ingest` after changing `embed_model` — the new model must re-embed the entire vault.
- Alternatives for `coding_model`: `deepseek-coder-v2`, `llama3.1:8b`.
