---
summary: >
  Defines which Ollama models are assigned to each role (chat, coding, embed)
  and maintains the registry of models that should exist locally. chatui.py
  reads this at startup — any model in the models: list that is not installed
  will be pulled automatically before the app launches. Edit role keys to swap
  models; add to models: before assigning a new model to a role.
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
| `coding_model` | `qwen2.5-coder:7b` | `/organize`, `/update` code generation, concept suggestions |
| `embed_model` | `nomic-embed-text` | Vault ingestion and similarity search |

## Installed models

Models listed under `models:` in the frontmatter are pulled automatically on launch if not already available. Add a model to this list before assigning it to a role.

| Model | Size | Notes |
|---|---|---|
| `llama3.2:3b` | 2.0 GB | Fast chat model |
| `qwen2.5-coder:7b` | 4.7 GB | Coding-specific model (kept as fallback) |
| `deepseek-r1:8b` | 5.0 GB | Reasoning model — strong at following multi-step instructions; good `coding_model` alternative |
| `nomic-embed-text` | 274 MB | Embedding — do not change without re-ingesting |

## Notes

- Role and model list changes take effect on next launch.
- After changing `embed_model`, run `/ingest` — the vault must be fully re-embedded.
- Alternatives for `coding_model`: `deepseek-coder-v2`, `llama3.1:8b`.
