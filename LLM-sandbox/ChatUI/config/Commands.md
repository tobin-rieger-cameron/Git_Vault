
This document defines every command that can be used in the ChatUI program:

| Input               | Behavior                                         |
| ------------------- | ------------------------------------------------ |
| prompt              | Get answers from the vault                       |
| `/draft`            | Start or resume drafting a paper                 |
| `/classify`         | Suggest location, tags, and wikilinks for a file |
| `/review [subject]` | Guided study session on a given topic            |
| `/ingest`           | Rebuild the vector database from the vault       |
| `/web`              | Toggle the web-search supplement                 |
| `/model [name]`     | Show or switch the active chat model             |

## Notes
---
- Applied command/behavior changes are logged in `config/changelog.md`, same as any other code change. 
