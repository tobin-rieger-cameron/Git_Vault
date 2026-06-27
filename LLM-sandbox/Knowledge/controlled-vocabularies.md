---
tags: [taxonomy]
---

# Controlled Vocabularies and Thesauri

Controlled vocabularies and thesauri are tools for maintaining **consistency and precision** in knowledge organisation systems. They define an authorised set of terms and the relationships between them, ensuring that the same concept is always described the same way.

## Controlled Vocabulary

A controlled vocabulary is a curated, fixed list of approved terms for describing or indexing content in a specific domain. Only terms from the list may be used; synonyms and variant spellings are mapped to a single **preferred term**.

**Examples:**
- **LCSH** (Library of Congress Subject Headings) — used by libraries worldwide to classify holdings
- **MeSH** (Medical Subject Headings) — used by PubMed and the US National Library of Medicine
- **ISO country codes** — standardised country names for data systems

### Key Features
- **Preferred terms** vs. **non-preferred terms** (synonyms redirected via USE references)
- **Scope notes** — definitions clarifying what a term includes or excludes
- **Hierarchical relationships** — broader term (BT) / narrower term (NT)
- **Associative relationships** — related terms (RT) that are not hierarchically linked

## Thesaurus (Information Science)

In information science, a **thesaurus** is a structured controlled vocabulary that explicitly documents the relationships between terms. It is more than a synonym list — it encodes the semantic network of a domain.

A thesaurus entry typically contains:
- **USE / UF (Used For)** — maps non-preferred synonyms to the preferred term
- **BT (Broader Term)** — the parent concept
- **NT (Narrower Term)** — child concepts
- **RT (Related Term)** — associated concepts at the same level

*Note: this is distinct from a general-language thesaurus (e.g. Roget's), which provides word choices. An IS thesaurus is a structural knowledge tool.*

**Examples:**
- **AAT** (Art & Architecture Thesaurus) — Getty's structured vocabulary for art and material culture
- **AGROVOC** — FAO's multilingual thesaurus for agriculture

## How They Differ from Free Tagging (Folksonomy)

| Dimension | Controlled Vocabulary / Thesaurus | Folksonomy / Free Tagging |
|---|---|---|
| Who assigns terms | Domain experts / central authority | Any user |
| Consistency | High — one preferred term per concept | Low — synonyms, typos, plural/singular variants all coexist |
| Recall in search | High — all items using preferred term are found | Variable — missed if user searches a synonym |
| Flexibility | Lower — adding terms requires governance | High — any tag can be created instantly |
| Maintenance cost | High | Low |

## When to Use Each

- **Controlled vocabulary** — institutional repositories, medical databases, library catalogues, anywhere precision and recall matter
- **Folksonomy** — social bookmarking, personal notes, informal content where user vocabulary diversity is a feature rather than a bug
- **Hybrid** — many modern systems (e.g. Zotero, some CMS platforms) offer suggested controlled terms alongside free tagging
