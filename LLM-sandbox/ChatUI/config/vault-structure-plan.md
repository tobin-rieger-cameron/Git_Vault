---
status: revising
date: 2026-06-27
implemented: 2026-06-28
revision-date: 2026-07-17
---

# Vault Structure Plan

## Status

Revising as of 2026-07-17: replacing the original Dewey-Decimal-with-one-deviation scheme with a
custom classification, built by comparing Dewey, Library of Congress Classification (LCC), and
Universal Decimal Classification (UDC) and picking whichever category boundaries actually fit a
personal knowledge vault, rather than inheriting one system's groupings and patching a single
deviation. Top-level classes (000-900) and second-level divisions (all 10 classes) are finalized;
third-level sections are being designed per-class as real research happens, starting with 000 (done).
This revision intentionally ignores the current on-disk vault structure — file placement is deferred
until the design is mature; see Next Steps.

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
| 100 | Philosophy & Psychology | |
| 200 | Religion | |
| 300 | Formal & Applied Sciences | Mathematics, logic, computer science, AI/ML, engineering, applied technology |
| 400 | Social & Natural Sciences | Sociology, economics, politics, law, physics, biology, chemistry, earth sciences |
| 500 | Language and Literature | Linguistics, literature, and reference works (encyclopedias, dictionaries, biographies) |
| 600 | Fine Arts | Visual arts, music, design |
| 700 | History | |
| 800 | Geography | |
| 900 | Recreation & Everyday Life | Sports, games, entertainment, home/family life, food, practical skills, leisure travel |

### Design notes vs. the systems compared

- **Formal and applied sciences merged into one class (300)**, unlike Dewey/UDC's pure/applied split
  (500/600 in both) — computer science sits with mathematics rather than off in a general-works
  class, matching Library of Congress's `QA` (Mathematics & Computer Science share one subclass).
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
- **Recreation & Everyday Life (900) has no direct equivalent top-level slot in any of the three
  systems compared** — Dewey and UDC both fold it into Arts (Dewey 790s, UDC class 7), LCC splits it
  across Geography (`GV`, recreation/sports/games) and Technology (`TX`, home economics). Giving it
  its own class is the clearest structural gap the comparison surfaced.
- **Reference works** (encyclopedias, dictionaries, biographies) placed under Literature (500);
  **indexes and cross-disciplinary reference tools** placed under Information Theory (000) instead —
  unlike Dewey (010-090) and LCC (`Z`), which give general reference its own dedicated class.
- **Information Theory (000) is deliberately broad**: not narrowly Shannon/coding-theory, but "how
  knowledge itself is organized" — taxonomy, classification, ontology, controlled vocabularies.

### Known cross-class overlaps (by design, not oversight)

Splitting theory from practice across separate classes creates a few deliberate overlaps — every
system compared runs into the same tension, and tags are the intended way to bridge them rather than
picking one "true" home and losing the other angle:

- **Travel**: 870 (Geography) studies travel/tourism patterns; 960 (Recreation) covers the practical/
  experiential side.
- **Film & performance**: 660/670 (Fine Arts) treat these as art forms; 970 (Recreation) covers them
  as entertainment/pop culture consumption.
- **Craft**: 690 (Fine Arts) is artistic craft practice; 930 (Recreation) is casual/hobbyist craft.
- **East Asian traditions** (270, Religion) straddle religion and philosophy (100) — Taoism and
  Confucianism in particular are argued both ways in secondary literature.
- **Logic**: 130 (Philosophy & Psychology) covers argumentation/informal reasoning; formal/symbolic
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
existing practice, folders get made only once a real file needs them. The tables below are the design
reference for where those subfolders will go, not a literal directory listing to create up front.

## Second-Level Divisions

### 000 Information Theory

```
000  general — overview, foundational theory
010  Classification systems & schemes (by named system: Dewey, LCC, UDC, Bliss, Colon)
020  Taxonomies & hierarchical structures
030  Controlled vocabularies & subject headings
040  Folksonomies & social/collaborative tagging
050  Faceted classification & analytico-synthetic methods
060  Ontologies & semantic structures
070  Metadata & bibliographic description
080  Information retrieval theory & indexing
090  Evaluating & comparing classification systems
```

#### 000 Third-Level Sections (drafted so far)

**010 Classification systems & schemes**
```
010  general/comparative overview
011  Dewey Decimal Classification (DDC)
012  Library of Congress Classification (LCC)
013  Universal Decimal Classification (UDC)
014  Bliss Bibliographic Classification (BC2)
015  Colon Classification (Ranganathan)
016-018  [reserved — other systems encountered later]
019  cross-system comparative notes
```

**020 Taxonomies & hierarchical structures**
```
020  general
021  monohierarchy
022  polyhierarchy
023  discipline & subject hierarchies
024  hierarchy differences & comparison
025-029  [reserved]
```

**030 Controlled vocabularies & subject headings**
```
030  general
031  thesaurus construction & structure
032  subject heading systems (LCSH-style)
033  Polythematic Structured Subject Heading System (PSH)
034-039  [reserved]
```

**040 Folksonomies & social/collaborative tagging**
```
040  general
041-049  [reserved — tag clouds, crowd-sourced tagging, hashtag systems]
```

**050 Faceted classification & analytico-synthetic methods**
```
050  general
051-059  [reserved — PMEST facets, facet analysis theory, post-coordinate indexing]
```

**060 Ontologies & semantic structures**
```
060  general
061  interdisciplinary/cross-domain ontologies
062-069  [reserved — formal ontology (philosophy), semantic web/RDF/OWL, domain ontologies]
```

**070 Metadata & bibliographic description**
```
070  general
071  cataloging standards & metadata schemas (Dublin Core, MARC, schema.org)
072  frontmatter/structured file metadata conventions
073-079  [reserved]
```

**080 Information retrieval theory & indexing**
```
080  general
081  relevance & ranking theory
082  indexing methods & theory
083-089  [reserved]
```

**090 Evaluating & comparing classification systems**
```
090  general
091  cross-system mapping
092  evaluation criteria & comparative analysis
093-099  [reserved]
```

Compared against Dewey/UDC/LCC's real equivalents (verified against the official OCLC DDC summaries
and LCC/UDC sources, not reconstructed from memory): none of the three systems treat knowledge-
organization theory as worthy of a full top-level class — Dewey's real 000 is dominated by
publication-format-by-language splits (bibliographies/encyclopedias/serials/newspapers/collections,
each divided into the same 10 language slots); UDC nests this whole territory inside one sub-branch
(`001 Science and knowledge in general`); LCC's closest analog is one slice of one letter-class
(`Z665-718.8`). This scheme's 000 gives the subject more dedicated structural room than any source
system does. Two optional, not-yet-added gaps: general history/theory of information science as a
discipline, and bibliographic control/cataloging practice (MARC, RDA, AACR2) — likely unnecessary for
a personal vault, noted for completeness only.

### 100 Philosophy & Psychology

```
100  general — overview of philosophy & psychology as fields, their historical relationship
110  Metaphysics & ontology — nature of being, existence, free will, mind-body problem
120  Epistemology & philosophy of knowledge — theory of knowledge, philosophy of science
130  Logic — formal & informal logic, argumentation, fallacies
140  Ethics & moral philosophy — normative ethics, applied ethics, metaethics
150  Aesthetics & philosophy of art
160  History of philosophy by tradition — ancient, medieval, eastern, modern schools
170  Cognitive & general psychology — perception, memory, intelligence, cognitive science
180  Developmental, social & personality psychology
190  Clinical, abnormal & applied psychology — mental health, therapy, disorders
```

### 200 Religion

```
200  general — comparative religion, religious studies as a field
210  Philosophy & theory of religion — arguments for/against deities, problem of evil
220  Comparative mythology & religious history — origins and history of religion broadly
230  Judaism
240  Christianity
250  Islam
260  Dharmic religions — Hinduism, Buddhism, Jainism, Sikhism
270  East Asian traditions — Taoism, Confucianism, Shinto
280  Indigenous, folk & new religious movements
290  Esotericism, mysticism & comparative theology
```

### 300 Formal & Applied Sciences

```
300  general — overview, the pure/applied relationship
310  Mathematics
320  Computer science & computation theory — algorithms, complexity, formal languages
330  Artificial intelligence & machine learning
340  Information systems & data engineering — databases, retrieval, vector search
350  Engineering — mechanical, electrical, civil, aerospace
360  Medicine & health sciences
370  Applied technology & industrial processes — manufacturing, materials science
380  Agriculture & environmental applied science
390  Systems, cybernetics & control theory
```

### 400 Social & Natural Sciences

```
400  general — overview, behavioral-science bridge between social & natural sciences
410  Sociology & anthropology
420  Economics
430  Political science, government & law
440  Education & pedagogy
450  Physics & astronomy
460  Chemistry
470  Earth sciences & geology
480  Biology & life sciences
490  Ecology, botany & zoology
```

### 500 Language and Literature

```
500  general
510  Linguistics
520  Language acquisition, learning & pedagogy
530  Rhetoric, composition & writing theory
540  Literary theory & criticism
550  Poetry
560  Prose fiction
570  Drama (as written text)
580  Nonfiction & creative nonfiction — essays, memoir, biography-as-literature
590  World literature by region/tradition — catch-all when geography beats genre
```

### 600 Fine Arts

```
600  general — aesthetics in practice, ties back to 150's theory
610  Visual arts — drawing, painting, printmaking
620  Sculpture & three-dimensional art
630  Architecture & environmental design
640  Music
650  Photography & digital/computer art
660  Film (as an art form)
670  Performing arts — dance & theater (performance practice, distinct from 570's text)
680  Design — graphic, industrial, fashion
690  Craft & decorative arts
```

### 700 History

```
700  general — historiography, philosophy of history, methods
710  Prehistory & archaeology
720  Ancient history (global, to ~500 CE)
730  Medieval history (global, ~500-1500)
740  Early modern history (~1500-1800)
750  Modern history (~1800-1945)
760  Contemporary history (1945-present)
770  Military & political history
780  Social & cultural history
790  Regional & national history surveys — catch-all when place beats era
```

### 800 Geography

```
800  general — geography as a field, cartography theory
810  Physical geography
820  Human geography
830  Cartography & GIS
840  Environmental geography & ecology
850  Economic geography
860  Political geography & geopolitics
870  Travel & exploration (study of travel/tourism patterns)
880  Historical geography — how places have changed over time
890  Regional & national geography surveys — catch-all
```

### 900 Recreation & Everyday Life

```
900  general
910  Sports & athletics
920  Games — board, card, video, puzzles
930  Hobbies & crafts (casual leisure, distinct from 690's artistic craft)
940  Food & cooking
950  Home & family life
960  Travel & leisure (practical/experiential, distinct from 870's study of it)
970  Entertainment & pop culture — distinct from 660's film-as-art-form
980  Personal health, fitness & wellness — distinct from 360's clinical medicine
990  Social recreation & celebrations — parties, holidays, traditions
```

## Tag Conventions

Tags are semantic — they describe topic, not location. A file in 000-information-theory/ can carry
`[philosophy]`; a file in 300-formal-applied-sciences/ can carry `[taxonomy]`. The folder answers
"where does this live?"; the tag answers "what is this about?".

## Tag → Folder Mapping

This table is the canonical source of truth used by `/classify` to classify files.
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
