---
title: Web Index Architecture
tags: [taxonomy, old-structure-move-me]
---

# How Google's Search Index Works
Google's search index is a massive database that stores a copy of the web's content, using complex algorithms to organize and structure this data in a way that facilitates fast and accurate searching.

At its core, the search index is built through a process that involves crawling, indexing, and ranking. This allows users to navigate and find relevant information from the vast expanse of the internet.

## Crawling
The first step in building the search index is crawling, where Google's software agents, called crawlers or spiders, systematically explore the web, discovering new pages and updating existing ones. As they crawl, they extract relevant information from each page, such as links, metadata, and content, which is then fed into the indexing system.

## Indexing
The extracted data is then organized into a massive database using complex algorithms to structure the data in a way that facilitates fast searching. Google uses various techniques to index its massive dataset, including:

* **Inverted indexing**: This technique stores a list of words and their corresponding documents, allowing for efficient querying and retrieval of specific information.
* **Ranking**: Google's algorithm ranks the indexed pages based on relevance, authority, and other factors, ensuring that the most relevant results are displayed first.

## Ranking
Ranking is an essential component of the search index, as it determines which results are displayed to users. Google's ranking algorithm considers various factors, including:

* **Relevance**: How well does a page match the user's search query?
* **Authority**: Is the page from a trusted or authoritative source?
* **Other factors**: Such as link equity, content quality, and user experience.

## Index Data Structures: B-Trees and Inverted Indexes

Two structures do most of the work in making a massive dataset queryable in milliseconds:

**B-trees** — multi-level trees where each node holds a range of key values and pointers to child nodes. Effective for range queries and ordered lookups; the default index structure in most relational databases.

**Inverted indexes** — store a mapping from each word or term to the list of documents (and positions) it appears in, the reverse of a normal document → words mapping. This is what makes full-text search fast: instead of scanning every document for a keyword, the engine looks the keyword up once and gets back every document that contains it. Google's web index is built on this structure.

Both avoid the alternative — scanning the entire dataset per query — which is what makes them essential once a collection grows past what fits comfortably in memory.

## Applications Beyond Web Search

The same inverted-index principle underlies library and information-retrieval systems generally, and e-commerce platforms layer faceted filtering (see [[Faceted Browsing Techniques]]) on top of an index to let shoppers narrow a catalog by multiple attributes at once.

## See also
* [[Faceted Classification]]
* [[Faceted Browsing Techniques]]
* [[Database Search Index]]
* [[Sparse vs Dense Retrieval]]
