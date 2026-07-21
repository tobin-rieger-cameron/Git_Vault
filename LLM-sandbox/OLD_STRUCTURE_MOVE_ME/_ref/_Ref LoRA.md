---
title: LoRA Reference
tags: [machinelearning, ai, meta, ref, old-structure-move-me]
---

# LoRA Reference

LoRA (Low-Rank Adaptation) is a parameter-efficient fine-tuning technique. It does **not** modify existing weights — it adds small trainable adapter matrices alongside frozen pretrained weights.

## Core Mechanism

For a pretrained weight matrix W ∈ ℝ^(d×k), standard fine-tuning learns a full update ΔW of the same shape, requiring d×k new parameters.

LoRA constrains ΔW to a low-rank decomposition:

```
ΔW = B · A    where B ∈ ℝ^(d×r), A ∈ ℝ^(r×k), rank r << min(d, k)
```

- **A** is initialised with random Gaussian values
- **B** is initialised to zero (so ΔW = 0 at the start of training)
- Only A and B are trained; W remains completely frozen
- A scaling factor α/r controls the magnitude of the update

At inference, the adapter can be **merged** into the base weights: W' = W + (α/r)·B·A. This adds zero latency — the model looks identical to a standard pretrained model after merging.

## Parameter Savings

For a weight matrix of shape 4096×4096 (d=k=4096):
- Full update: 4096 × 4096 = **16.8M parameters**
- LoRA at r=8: (4096×8) + (8×4096) = **65K parameters** — a 256× reduction

A 7B model has ~32 attention layers, each with Q/K/V/O projections (4 matrices each). LoRA typically targets at least Q and V:
- 32 layers × 2 matrices × 65K = ~4M trainable parameters
- vs 7 billion for full fine-tuning

## Where LoRA is Applied

Most implementations inject LoRA into the **query (Q) and value (V)** projection matrices of the attention mechanism. Some fine-tunes also add LoRA to:
- Key (K) projections
- Output (O) projections  
- FFN up/down projections (for more capacity)

## Choosing Rank

| Rank | Use case |
|---|---|
| r = 4 | Style/tone adaptation, minimal capacity needed |
| r = 8–16 | General instruction tuning (most common) |
| r = 32–64 | Domain knowledge injection, complex reasoning |
| r = 128+ | Rarely needed; diminishing returns |

## QLoRA

QLoRA combines LoRA with 4-bit quantisation (NF4 format) of the base model:
- Base weights stored in 4-bit NF4 → reduces 7B model from ~14 GB to ~4 GB VRAM
- LoRA adapters stored in bfloat16 → ~4M × 2 bytes ≈ 8 MB overhead
- Makes fine-tuning a 7B model feasible on a single consumer GPU (8 GB VRAM)

## What LoRA is NOT

- It does **not** reduce the rank of existing weights
- It does **not** modify W during training — W stays frozen
- It does **not** slow inference once adapters are merged

## See Also

- [[Fine-Tuning Methods]]
- [[_Ref Fine Tuning]]
- [[RLHF Alignment]]
- [[Machine Learning]]
