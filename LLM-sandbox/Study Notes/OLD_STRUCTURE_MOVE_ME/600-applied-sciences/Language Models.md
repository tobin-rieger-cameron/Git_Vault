---
title: "Language Models"
tags: [ai, machinelearning]
---

# Language Models

A language model assigns probabilities to sequences of tokens and can generate new text by sampling from those probabilities. Modern large language models (LLMs) are transformer-based neural networks trained on web-scale text via next-token prediction.

## Architecture: The Transformer

All major LLMs (Llama, GPT, Mistral, Gemma) are **decoder-only transformers**. Each forward pass through the network:

1. Tokenises input text into integers (subword tokens via BPE or SentencePiece)
2. Looks up a learned embedding vector for each token
3. Passes the sequence through N identical **transformer blocks**, each containing:
   - **Multi-head self-attention** — each token attends to all preceding tokens; Q, K, V projections; scaled dot-product attention; output projection
   - **Feed-forward network (FFN)** — two linear layers with a non-linearity (SiLU/GELU); intermediate dim is typically 4× the model dim
   - **Layer norm + residual connection** around each sub-layer
4. A final linear projection (the "unembedding" layer) maps the last hidden state to vocabulary logits
5. Softmax gives a probability distribution over the next token

Positional information is injected via **RoPE** (Rotary Position Embedding) in most modern models, replacing the original sinusoidal encoding.

## Context Window and KV Cache

The context window is the maximum number of tokens the model can attend to at once. During generation, past keys and values are cached (**KV cache**) to avoid recomputing attention for already-processed tokens. KV cache grows linearly with sequence length and is the primary VRAM constraint during inference.

## Quantisation

Running a 7B model in full float32 requires ~28 GB VRAM. Quantisation reduces this:

| Format | Bits/weight | 7B model VRAM |
|---|---|---|
| float32 | 32 | ~28 GB |
| bfloat16 | 16 | ~14 GB |
| GPTQ/AWQ (int4) | 4 | ~4–5 GB |
| GGUF Q4_K_M | ~4.5 | ~4–5 GB |

**GGUF** (llama.cpp format) and **GPTQ/AWQ** are the dominant local formats. Ollama uses GGUF internally.

## Why LLMs Hallucinate

LLMs predict statistically likely continuations — they don't retrieve facts, they interpolate learned patterns. Sources of hallucination:

- Training data contained errors, contradictions, or outdated facts
- The model has no epistemic uncertainty signal — it generates fluently whether it "knows" something or not
- Long-context prompts can cause attention to drift from key facts

Mitigations: RAG (retrieval-augmented generation), tool use, chain-of-thought prompting, lowering temperature.

## Generation Sampling

Given the probability distribution over next tokens:

- **Greedy** — always pick the highest-probability token. Deterministic but repetitive.
- **Temperature** — divide logits by T before softmax. T<1 sharpens the distribution (more focused), T>1 flattens it (more diverse).
- **Top-p (nucleus)** — sample from the smallest set of tokens whose cumulative probability exceeds p.
- **Top-k** — restrict sampling to the k most likely tokens.

## See Also

- [[Machine Learning]]
- [[Low-Rank Adaptation]]
- [[Fine-Tuning Methods]]
- [[RLHF Alignment]]
- [[Retrieval Augmentation Models]]
