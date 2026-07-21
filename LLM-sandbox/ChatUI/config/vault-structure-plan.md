---
status: revising
date: 2026-06-27
implemented: 2026-06-28
revision-date: 2026-07-17
---

# Vault Structure Plan

## Status

Top-level classes (000-900) and second-level divisions (all 10 classes) are finalized;
third-level sections are being designed as real research happens.

## Classification Strategy

Monohierarchical folder structure using a custom 10-class scheme, numbered 000-900 in Dewey's decimal
notation style but not its category boundaries. Tags remain semantic and provide polyhierarchy across
folder boundaries.

**Folder = where a file lives (one location)**
**Tags = what a file is about (multiple)**

## Top-Level Classes

| Class | Name | Scope |
|---|---|---|
| 000 | Information Theory | Knowledge organization, taxonomy, classification, ontology, indexes, cross-disciplinary reference |
| 100 | Philosophy and Psychology | |
| 200 | Religion | |
| 300 | Formal and Applied Sciences | Mathematics, logic, computer science, AI/ML, engineering, applied technology |
| 400 | Social and Natural Sciences | Sociology, economics, politics, law, physics, biology, chemistry, earth sciences |
| 500 | Language and Literature | Linguistics, literature, and reference works (encyclopedias, dictionaries, biographies) |
| 600 | Fine Arts | Visual arts, music, design |
| 700 | History | |
| 800 | Geography | |
| 900 | Recreation and Everyday Life | Sports, games, entertainment, home/family life, food, practical skills, leisure travel |

### Design notes vs. the systems compared

- **Formal and applied sciences merged into one class (300)**, unlike Dewey/UDC's pure/applied split
  (500/600 in both) — computer science sits with mathematics rather than off in a general-works
  class, matching Library of Congress's `QA` (Mathematics and Computer Science share one subclass).

- **Social and natural sciences merged into one class (400)**, unlike all three systems compared,
  which each keep them separate. Psychology is excluded from 400 since it lives in 100 instead.

- **Language and Literature merged into one class (500)**, matching LCC's `P` rather than
  Dewey/UDC's split into two top-level classes for the same per-language breakdown. Organized by
  genre/function (poetry, prose, drama, criticism) rather than by individual European language, unlike
  Dewey/UDC/LCC, all of which devote most of their language/literature divisions to per-language splits.

- **History (700) and Geography (800) kept as two separate classes**, unlike UDC's single class 9 —
  space and time treated as equally fundamental, independent organizing axes rather than merged. Both
  are organized by era/theme globally rather than by continent, avoiding the Eurocentric bias in
  Dewey's 930-990 (which gives Europe alone as much room as the rest of the world combined).

- **Religion (200) rebalanced toward global equity** — Dewey devotes 7 of its 9 non-general divisions
  to Christianity alone; this scheme gives Judaism, Christianity, Islam, Dharmic religions, East Asian
  traditions, indigenous/new religious movements, and esotericism each their own division.

- **Recreation and Everyday Life (900) has no direct equivalent top-level slot in any of the three
  systems compared** — Dewey and UDC both fold it into Arts (Dewey 790s, UDC class 7), LCC splits it
  across Geography (`GV`, recreation/sports/games) and Technology (`TX`, home economics). Giving it
  its own class is the clearest structural gap the comparison surfaced.

- **Reference works** (encyclopedias, dictionaries, biographies) placed under Literature (500);
  **indexes and cross-disciplinary reference tools** placed under Information Theory (000) instead —
  unlike Dewey (010-090) and LCC (`Z`), which give general reference its own dedicated class.

- **Information Theory (000) is deliberately broad**: not narrowly Shannon/coding-theory, but "how
  knowledge itself is organized" — taxonomy, classification, ontology, controlled vocabularies.

### Known cross-class overlaps (by design)

Splitting theory from practice across separate classes creates a few deliberate overlaps — every
system compared runs into the same tension, and tags are the intended way to bridge them rather than
picking one "true" home and losing the other angle:

- **Travel**: 870 (Geography) studies travel/tourism patterns; 960 (Recreation) covers the practical/
  experiential side.
- **Film and performance**: 660/670 (Fine Arts) treat these as art forms; 970 (Recreation) covers them
  as entertainment/pop culture consumption.
- **Craft**: 690 (Fine Arts) is artistic craft practice; 930 (Recreation) is casual/hobbyist craft.
- **East Asian traditions** (270, Religion) straddle religion and philosophy (100) — Taoism and
  Confucianism in particular are argued both ways in secondary literature.
- **Logic**: 130 (Philosophy and Psychology) covers argumentation/informal reasoning; formal/symbolic
  logic (proof theory, computability) could arguably sit in 300 alongside mathematics instead —
  not yet decided which convention to use.

## Folder Hierarchy (target, top level only)

```
Knowledge/
├── 000-information-theory/
├── 100-philosophy-psychology/
├── 200-religion/
├── 300-formal-applied-sciences/
│   └── _ref/                     # Dense reference articles for RAG context
├── 400-social-natural-sciences/
├── 500-language-literature/
├── 600-fine-arts/
├── 700-history/
├── 800-geography/
├── 900-recreation-everyday-life/
├── misc/                         # Uncategorised or cross-cutting entries
└── conversations/                # Session logs — excluded from ingest
```

Second-level (division) and third-level (section) subfolders are not pre-created — per the vault's
existing practice, folders get made only once a real file needs them.

## Tag Conventions

Tags are semantic — they describe topic, not location.
A file in 000-information-theory/ can carry `[philosophy]`;
a file in 300-formal-applied-sciences/ can carry `[taxonomy]`.
The folder answers "where does this live?"; the tag answers "what is this about?".

### Folder Mapping

This table is used by `/classify` to place files.
When a file has multiple tags, the first matching tag determines the folder.
Tags listed as `(skip)` carry type/quality meaning only and are ignored for placement.
Currently maps to top-level classes only; whether `/classify` should place files at division-level
granularity (e.g. `300-formal-applied-sciences/330-ai-machine-learning/`) instead is an open question,
deferred until the physical folder structure is created.

| Tag | Folder |
|---|---|
| taxonomy | 000-information-theory |
| information-science | 000-information-theory |
| index | 000-information-theory |
| philosophy | 100-philosophy-psychology |
| ethics | 100-philosophy-psychology |
| psychology | 100-philosophy-psychology |
| religion | 200-religion |
| mathematics | 300-formal-applied-sciences |
| ai | 300-formal-applied-sciences |
| machinelearning | 300-formal-applied-sciences |
| engineering | 300-formal-applied-sciences |
| social-sciences | 400-social-natural-sciences |
| physics | 400-social-natural-sciences |
| biology | 400-social-natural-sciences |
| chemistry | 400-social-natural-sciences |
| medicine | 400-social-natural-sciences |
| language | 500-language-literature |
| linguistics | 500-language-literature |
| literature | 500-language-literature |
| arts | 600-fine-arts |
| history | 700-history |
| geography | 800-geography |
| recreation | 900-recreation-everyday-life |
| general | (skip — no placement, falls back to LLM) |
| meta | (skip — type tag, not a topic) |

## Special Cases

- Files prefixed `_ref-` are placed in `<folder>/_ref/` within their classified folder.
- Files with only skip-tags or no tags fall back to LLM classification using this document as context.
- Files with no clear classification land in `misc/` and are re-evaluated on the next `/classify` run once tagged.

## Next Steps

- Design third-level sections for the remaining 9 classes as real research/writing happens in each —
  same approach used for 000 (verify against real source material, don't reconstruct from memory).
- Decide the open logic-placement question (100 vs. 300) and the tag-mapping granularity question
  (top-level vs. division-level) once enough real content exists to judge by.
- Once the design is mature, reconcile against the actual current vault contents (which have drifted
  from earlier versions of this plan) and physically move files into the new structure, then re-run
  `/ingest`.
