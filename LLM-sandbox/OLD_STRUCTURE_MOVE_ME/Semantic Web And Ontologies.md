---
title: Semantic Web and Ontologies
tags: [taxonomy, old-structure-move-me]
---

# Semantic Web and Ontologies

RDF and OWL are the two standards that let ontologies actually run on the web — RDF for representing data as a graph, OWL for defining the classes, properties, and inference rules on top of it.

## RDF: describing data as a graph

The Resource Description Framework represents data as triples (subject–predicate–object), forming a graph of interconnected resources rather than a document tree. This makes it possible to link data across sites the same way HTML links documents.

## OWL: adding classes and inference

Built on top of RDF, the Web Ontology Language adds vocabulary for defining classes, properties, and constraints between entities. It's what turns a bare RDF graph into a formal [[Taxonomy Hierarchy Differences|ontology]] — one where a reasoner can infer new facts (e.g. "A Smartphone is-a Electronics" implies smartphone-specific rules apply) rather than just storing them.

## The Semantic Web vision

Tim Berners-Lee's Semantic Web proposal aims to make web data machine-understandable, not just human-readable. Ontologies (via RDF/OWL) are the mechanism: a shared vocabulary lets independent systems reason about the same data and interoperate without custom integration code.

## See also

* [[Taxonomy Hierarchy Differences]]
* [[Interdisciplinary Ontologies]]
* [[Controlled Vocabularies]]
