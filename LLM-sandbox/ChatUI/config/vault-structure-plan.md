---
status: implemented
date: 2026-06-27
implemented: 2026-06-28
---

# Vault Structure Plan

## Classification Strategy

Monohierarchical folder structure based on Dewey Decimal top-level classes, with one deliberate deviation: computer science and AI moved from 000 to 600 (Applied Sciences). Tags remain semantic and provide polyhierarchy across folder boundaries.

**Folder = where a file lives (one location)**
**Tags = what a file is about (multiple)**

## Folder Hierarchy

```
Knowledge/
├── 000-information/        # Knowledge organisation, taxonomy, classification, ontology, information science
├── 100-philosophy/         # Philosophy, logic, ethics, cognitive science
├── 200-religion/           # (empty — reserved)
├── 300-social-sciences/    # Sociology, economics, politics, law
├── 400-language/           # Linguistics, language theory (empty — reserved)
├── 500-natural-sciences/   # Physics, biology, chemistry, mathematics
├── 600-applied-sciences/   # Computer science, AI/ML, engineering, medicine
│   └── _ref/               # Dense reference articles for RAG context
├── 700-arts/               # Arts, design, recreation (empty — reserved)
├── 800-literature/         # (empty — reserved)
├── 900-history/            # History, geography (empty — reserved)
├── misc/                   # Uncategorised or cross-cutting entries
└── conversations/          # Session logs — excluded from ingest
```

## Current File Placement

### 000-information/
- taxonomy.md
- taxonomy-hierarchy-differences.md
- taxonomy-mappings.md
- folksonomy-differences.md
- faceted-classification.md
- polyhierarchy.md
- controlled-vocabularies.md
- disciplines-hierarchies.md
- interdisciplinary-ontologies.md
- dewey-decimal-system.md
- Library of Congress Classification System.md
- Polythematic Structured Subject Heading System.md
- Evaluating Systems of Classification.md
- humanities-spectrum.md

### 100-philosophy/
- formal-sciences-philosophy.md

### 300-social-sciences/
- social-science-subfields.md

### 500-natural-sciences/
- Mathematics.md
- natural-sciences.md
- kinematics.md
- kinematic-frameworks.md
- photosynthesis.md

### 600-applied-sciences/
- language-models.md
- machine-learning.md
- fine-tuning-methods.md
- lo-ra-adaptations.md
- rlhf-alignment.md
- knowledge-distillation-methods.md
- agential-patterns.md
- consequential-informed-guidance.md
- prompt-engineering-strategies.md
- language-model-evaluation.md
- embedding-models.md
- sparse-vs-dense-retrieval.md
- retrieval-augmentation-models.md
- vector-databases-for-search.md
- vector-search-engines.md

### 600-applied-sciences/_ref/
- _ref-fine-tuning.md
- _ref-lora.md
- _ref-rag.md
- _ref-rlhf.md

### misc/
- cupcakes.md

## Deviation from Dewey

Computer science (Dewey: 004, 006.3 under 000) is placed in 600-applied-sciences.
Rationale: Dewey's placement reflects a 19th-century categorisation decision made before computing existed.
Applied computing belongs conceptually alongside engineering and applied technology.

## Tag Conventions

Tags are semantic — they describe topic, not location. A file in 000-information/ can carry `[philosophy]`;
a file in 600-applied-sciences/ can carry `[taxonomy]`. The folder answers "where does this live?"; the tag
answers "what is this about?".

## Tag → Folder Mapping

This table is the canonical source of truth used by `/organize` to classify files.
When a file has multiple tags, the first matching tag determines the folder.
Tags listed as `(skip)` carry type/quality meaning only and are ignored for placement.

| Tag | Folder |
|---|---|
| taxonomy | 000-information |
| information-science | 000-information |
| index | 000-information |
| philosophy | 100-philosophy |
| ethics | 100-philosophy |
| religion | 200-religion |
| social-sciences | 300-social-sciences |
| language | 400-language |
| linguistics | 400-language |
| mathematics | 500-natural-sciences |
| physics | 500-natural-sciences |
| biology | 500-natural-sciences |
| chemistry | 500-natural-sciences |
| ai | 600-applied-sciences |
| machinelearning | 600-applied-sciences |
| engineering | 600-applied-sciences |
| medicine | 600-applied-sciences |
| arts | 700-arts |
| literature | 800-literature |
| history | 900-history |
| geography | 900-history |
| general | (skip — no placement, falls back to LLM) |
| meta | (skip — type tag, not a topic) |

## Special Cases

- Files prefixed `_ref-` are placed in `<folder>/_ref/` within their classified folder.
- Files with only skip-tags or no tags fall back to LLM classification using this document as context.
- Files with no clear classification land in `misc/` and are re-evaluated on the next `/organize` run once tagged.
