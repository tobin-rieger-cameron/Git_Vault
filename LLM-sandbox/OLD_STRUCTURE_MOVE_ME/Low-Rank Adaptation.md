---
title: 'LoRA: Low-Rank Adaptation'
tags: [ai, machinelearning, old-structure-move-me]
---

# LoRA: Low-Rank Adaptation

LoRA is a parameter-efficient fine-tuning technique that adds small trainable adapter matrices alongside **frozen** pretrained weights. It does not modify or compress existing weights — the base model is untouched during training.

## How It Works

Standard fine-tuning learns a full weight update ΔW ∈ ℝ^(d×k) for each matrix — the same size as the original. LoRA constrains this update to a low-rank decomposition:

```
ΔW = B · A    where B ∈ ℝ^(d×r),  A ∈ ℝ^(r×k),  r << min(d, k)
```

- **W** — original pre-trained weight, kept frozen throughout training
- **A** — initialized randomly; trained
- **B** — initialized to zero (so the adapter starts as a no-op); trained
- **r** — the rank, a hyper-parameter (typically 8–64)
- **α** — a scaling constant; the effective update is (α/r) · B·A

After training, the adapter merges into the base: `W' = W + (α/r)·B·A`. The merged model is identical in size and speed to the original — zero inference overhead.

## Why the Low-Rank Assumption Works

Empirically, the weight changes needed for fine-tuning have a low intrinsic rank — most of the "useful" adaptation lies in a low-dimensional subspace. Full fine-tuning wastes capacity updating many near-zero directions.

## Parameter Efficiency

For a typical attention weight matrix (d=k=4096):
- Full update: 4096 × 4096 = **16.8M parameters**
- LoRA at r=8: (4096×8) + (8×4096) = **65K parameters** — 256× fewer

Across a 7B model fine-tuned with LoRA on Q and V projections: ~4M trainable parameters vs 7 billion. VRAM for the adapter is negligible.

## QLoRA

QLoRA extends LoRA by also quantising the frozen base weights to 4-bit NF4 format. This reduces a 7B model from ~14 GB to ~4–5 GB VRAM during training, making fine-tuning feasible on consumer GPUs (8 GB).

## Choosing Rank

| Rank | Suitable for |
|---|---|
| r = 4–8 | Style, tone, format adaptation |
| r = 16 | General instruction tuning (good default) |
| r = 32–64 | Domain knowledge injection, complex reasoning tasks |

## Compared to Full Fine-Tuning

| | Full FT | LoRA (r=16) | QLoRA (r=16) |
|---|---|---|---|
| Trainable params | 100% | ~0.5% | ~0.5% |
| VRAM (7B) | ~60 GB | ~16 GB | ~5 GB |
| Quality ceiling | Highest | Near-full | Slight degradation |
| Catastrophic forgetting | Risk | Low | Low |

## See Also

- [[Fine-Tuning Methods]]
- [[RLHF Alignment]]
- [[Machine Learning]]
- [[Knowledge Distillation Methods]]
