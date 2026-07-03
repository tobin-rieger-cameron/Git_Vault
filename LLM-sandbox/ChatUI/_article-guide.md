---
title: "Article Writing Guide"
tags: [meta]
---

# Article Writing Guide

Guidelines for writing knowledge-base articles. Follow this template for every article generated from conversation content.

## Structure

```
---
title: "Exact topic name"
tags: [tag1, tag2]   ← from taxonomy hierarchy
---

# Topic Name

One or two sentences saying what this is and why it matters.

## How It Works  (or: Core Mechanism, Key Concepts, etc.)

Explain the mechanism with concrete detail. Include:
- The actual process step by step
- Numbers and dimensions where relevant (e.g. "rank r=8 means 65K params vs 16M")
- What it does NOT do (common misconceptions)

## [Subtopic A]

...

## Comparison / When to Use

A table comparing alternatives is often the most useful thing in an article.

## Limitations

What breaks, what the tradeoffs are, when NOT to use this.

## See Also

- [[related-note-1]]
- [[related-note-2]]
```

## Rules

1. **Accuracy over completeness.** If you're not sure of a detail, omit it rather than guessing.
2. **Use reference material from the vault.** If REFERENCE MATERIAL FROM VAULT is provided, treat it as ground truth and build the article from it. Do not contradict it.
3. **Only link to vault notes that exist.** [[wikilinks]] in See Also must match real vault files listed under EXISTING VAULT NOTES. Never invent link targets.
4. **No redundant See Also links.** Only include notes that are genuinely related to the topic. Do not link to photosynthesis in a machine learning article.
5. **No frontmatter.** The system adds frontmatter automatically — do not write `---` blocks.
6. **Tables beat paragraphs** for comparisons. Use them.
7. **Concrete beats vague.** "r=8 gives 256× fewer trainable params" beats "significantly reduces parameters".

## Anti-patterns to Avoid

- Listing the vault stems verbatim in See Also
- Starting every section with "In the context of..."
- Saying things are "complex" without explaining them
- Ending with "I hope this was helpful"
- Including a Table of Contents for articles under 600 words
- Writing in Q&A format ("Q: what is X? A: X is...")
- Saying "I couldn't find", "Unfortunately", or "I don't have information" — omit the topic instead
- Reproducing the source text verbatim; always rewrite into reference prose
- Inventing facts not present in SOURCE or REFERENCE MATERIAL
