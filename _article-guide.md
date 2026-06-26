---
title: Article Writing Guide
tags: [meta]
---

# Article Writing Guide

**Markdown Article Structure Guide**

### Frontmatter (Top of the File)

* Use YAML format to store metadata
* Include:
	+ `title`: Article title
	+ `tags`: Keywords for categorization

Example frontmatter:
```yml
---
title: Introduction to Structured Markdown
tags: markdown, knowledge-base
---
```

### H1 Title (Top of the Section)

* Use `#` symbol followed by space and article title

### Opening Summary Paragraph (Introduction)

* Briefly introduce the topic and provide context

Example:
```markdown
## Introduction to Structured Markdown
Structured Markdown is a format for writing formatted text using plain text syntax. It's widely used in knowledge bases, documentation, and online content.
```

### H2 Sections (Key Concepts)

* Use `##` symbol followed by space and section title
* Break down complex topics into smaller sections

Example:
```markdown
## Key Concepts

Structured Markdown uses a combination of plain text syntax and special characters to format text. The most commonly used elements include headers, links, lists, and images.
```

### [[Wikilinks]] (Related Notes)

* Use double square brackets `[[ ]]` with the link text and target URL
* Provide links to related notes or documentation

Example:
```markdown
## Related Notes
See also: [Markdown Syntax](https://example.com/markdown-syntax) for more information on structured Markdown syntax.
```

### See Also Section (Conclusion)

* Summarize key points and provide additional resources
* Encourage further learning or exploration
