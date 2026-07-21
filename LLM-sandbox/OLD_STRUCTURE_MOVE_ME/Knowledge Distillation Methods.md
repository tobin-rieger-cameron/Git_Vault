---
title: Knowledge Distillation
tags: [machinelearning, ai, old-structure-move-me]
---

# Knowledge Distillation

Knowledge distillation is a model compression technique where a smaller **student** model is trained to mimic the behaviour of a larger **teacher** model. The student learns from the teacher's output distributions rather than just hard labels, allowing it to capture more of the teacher's learned representations.

## Core Mechanism

During standard training, a model learns from one-hot ground-truth labels (the correct class gets probability 1, all others 0). Knowledge distillation instead trains the student on the teacher's **soft probability outputs** (e.g., a model might assign 0.7 to "cat", 0.2 to "dog", 0.1 to "tiger"). These soft targets carry richer information about class similarities.

The distillation loss combines:
- **Distillation loss** — KL divergence between student and teacher softmax outputs (at temperature T > 1 to soften the distribution)
- **Student loss** — standard cross-entropy against ground truth labels
- A weighting factor α balances the two terms

Hinton et al. (2015) showed that a student trained with distillation significantly outperforms a student trained on hard labels alone.

## Temperature Scaling

At temperature T, logits z are divided before softmax: `σ(z_i / T)`. Higher T produces softer distributions that reveal more structure in the teacher's beliefs. T=1 is standard softmax; T=3–5 is common for distillation.

## Types of Knowledge to Distill

**Response-based** — distil from the teacher's final output (logits). Simplest, most common.

**Feature-based** — match intermediate layer activations between teacher and student. Transfers internal representations, not just outputs.

**Relation-based** — match the relationships between different samples' activations. Captures geometric structure in representation space.

## Applications in LLMs

- **Model compression** — distil a 70B model into a 7B student for cheaper inference
- **Speculative decoding** — a small draft model (student) generates tokens quickly; a large model (teacher) verifies them in parallel
- **Dataset generation** — use a teacher (e.g., GPT-4) to generate training data (responses) for fine-tuning a student (e.g., Llama-3-8B). Mistral, Phi-2, and many open models were trained this way
- **Task-specific compression** — distil a general model into a smaller domain-specific one

## Limits

- The student is bounded by the teacher's capability ceiling
- Architectural mismatch between teacher and student can limit transfer
- Feature-based distillation requires the student to have compatible intermediate dimensions

## See Also

- [[Machine Learning]]
- [[Fine-Tuning Methods]]
- [[lo-ra-adaptations]]
- [[Language Models]]
