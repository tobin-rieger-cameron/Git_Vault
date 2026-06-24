---
vault_path: /home/tizz/dev/LLM-sandbox/
similarity_threshold: 0.5
top_k: 3
chunk_size: 500
chunk_overlap: 50
history_window: 4
web_search_results: 3
---

# Settings

| Key | Default | Description |
|---|---|---|
| `vault_path` | _(script dir)_ | Absolute path to the vault root |
| `similarity_threshold` | `0.5` | Minimum score to use vault notes; below this falls back to model knowledge |
| `top_k` | `3` | Number of vault chunks retrieved per query |
| `chunk_size` | `500` | Characters per chunk during ingestion |
| `chunk_overlap` | `50` | Overlap between adjacent chunks |
| `history_window` | `4` | Conversation exchanges kept in context |
| `web_search_results` | `3` | DuckDuckGo results fetched per web search |

## Notes

- All changes take effect on next launch.
- After changing `chunk_size` or `chunk_overlap`, run `/ingest` to rebuild the database.
