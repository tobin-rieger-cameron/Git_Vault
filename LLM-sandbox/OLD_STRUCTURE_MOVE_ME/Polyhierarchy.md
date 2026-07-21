---
title: Polyhierarchy
tags: [taxonomy, old-structure-move-me]
---

# Polyhierarchy

Polyhierarchy is the property of a classification system where a single concept or node can have **multiple parent categories** simultaneously, rather than being constrained to one position in a tree.

## Why It Exists

Real-world knowledge does not always fit neatly into a single hierarchy. Concepts naturally belong to multiple domains based on different properties or perspectives. A strictly monohierarchical system forces an arbitrary choice of parent, losing the other valid relationships.

## Examples

**Tomato**
- In botanical taxonomy: *Solanum lycopersicum* → genus *Solanum* → family *Solanaceae* → flowering plants
- In culinary classification: fruit in botany, but treated as a vegetable in cooking contexts
- In legal/trade contexts: classified as a vegetable (US Supreme Court, *Nix v. Hedden*, 1893)

**Surgery**
- Under medical sciences (procedure category)
- Under psychology (as an area of study for patient decision-making)
- Under social studies (healthcare and society)

**Pizza**
- Under culinary classification (Italian cuisine, baked goods)
- Under cultural anthropology (food as cultural artefact, regional identity)

## Where Polyhierarchy Is Actively Used

- **Medical Subject Headings (MeSH)** — the US National Library of Medicine's controlled vocabulary explicitly supports polyhierarchy, allowing the same disease concept to appear under multiple anatomical, aetiological, and treatment branches
- **Getty Art & Architecture Thesaurus (AAT)** — art concepts appear under multiple style, material, and function hierarchies
- **Wikipedia category system** — articles routinely belong to multiple categories

## Contrast with Strict Hierarchy

| | Monohierarchy | Polyhierarchy |
|---|---|---|
| Each concept has | Exactly one parent | One or more parents |
| Structure | Tree | Directed acyclic graph (DAG) |
| Precision | Lower (forced placement) | Higher (reflects actual relationships) |
| Complexity | Simpler to implement | Requires DAG traversal logic |

## Relationship to Faceted Classification

Both polyhierarchy and faceted classification address the limitations of strict trees, but differently. Polyhierarchy keeps the concept in a single ontology with multiple parents; faceted classification assigns values across independent dimensions. They can coexist — a faceted system may also allow polyhierarchical relationships within each facet.
