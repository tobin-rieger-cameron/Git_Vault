---
title: "Machine Learning"
tags: [ai, machinelearning]
---

# Machine Learning

Machine learning is the field of algorithms that learn patterns from data rather than being explicitly programmed. A model is trained by optimising a loss function over a dataset using gradient-based methods.

## Learning Paradigms

| Paradigm | Signal | Examples |
|---|---|---|
| **Supervised** | Labelled (input, output) pairs | Image classification, translation |
| **Self-supervised** | Labels derived from data itself | Next-token prediction in LLMs, masked image modelling |
| **Unsupervised** | No labels | Clustering, dimensionality reduction |
| **Reinforcement** | Scalar reward from environment | Game playing, RLHF alignment |

Modern LLMs are trained with **self-supervised learning** (next-token prediction) — the "label" for each token is just the next token in the existing text.

## Training Loop

1. **Forward pass** — feed a batch of inputs through the model, compute predictions
2. **Loss** — measure how wrong the predictions are (cross-entropy for classification/LLMs, MSE for regression)
3. **Backward pass (backpropagation)** — compute the gradient of loss w.r.t. every parameter via the chain rule
4. **Optimiser step** — update parameters in the direction that reduces loss

### Optimisers

- **SGD** — subtract `lr × gradient` from each parameter. Simple but sensitive to learning rate.
- **Adam** — adapts per-parameter learning rates using exponential moving averages of gradients (m) and squared gradients (v). The dominant optimiser for deep learning.
- **AdamW** — Adam with decoupled weight decay. Standard for LLM training.

## Key Concepts

**Learning rate** — step size for each parameter update. Too large → divergence. Too small → slow convergence. **Learning rate schedules** (cosine decay, warmup) are critical in practice.

**Batch size** — number of examples per gradient update. Larger batches give lower-variance gradients but require more VRAM. Gradient accumulation simulates larger batches.

**Overfitting** — model memorises training data and fails to generalise. Mitigations: dropout, weight decay, data augmentation, early stopping.

**Regularisation** — techniques that constrain models to generalise better. Weight decay penalises large weights; dropout randomly zeros activations during training.

## Neural Networks

A neural network is a stack of linear transformations interleaved with non-linear **activation functions** (ReLU, GELU, SiLU). Depth allows learning hierarchical representations.

- **Parameters** — the learnable weights and biases. A 7B model has 7 billion of these.
- **Activations** — intermediate values during the forward pass. Stored during training for backprop; the primary VRAM cost during training.
- **Gradient checkpointing** — recompute activations during backward pass instead of storing them. Trades compute for memory.

## Training vs Inference

During **training**, both forward and backward passes run, activations are stored, and parameters are updated. During **inference**, only the forward pass runs. Inference needs roughly half the VRAM of training (no gradient storage).

## See Also

- [[language-models]]
- [[fine-tuning-methods]]
- [[lo-ra-adaptations]]
- [[rlhf-alignment]]
- [[knowledge-distillation-methods]]
