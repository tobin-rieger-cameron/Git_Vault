---
title: "RLHF: Reinforcement Learning from Human Feedback"
tags: [ai, machinelearning]
---

# RLHF: Reinforcement Learning from Human Feedback

RLHF is a three-stage training pipeline that aligns a pretrained language model with human preferences. It is the primary technique behind ChatGPT, Claude, and Llama-2-Chat.

## Why It Exists

A base LLM trained on next-token prediction learns to imitate internet text — including unhelpful, harmful, or off-topic content. SFT alone teaches format but not nuance. RLHF captures the subtle human preferences (helpfulness, honesty, harmlessness) that can't easily be specified as rules.

## The Three Stages

### 1. Supervised Fine-Tuning (SFT)
Fine-tune the base model on a curated dataset of (prompt, ideal response) pairs written by human contractors. This teaches the model the expected response format and basic instruction-following before preference learning.

### 2. Reward Model Training
Collect **preference comparisons**: for each prompt, human raters compare two model responses and pick the better one. Train a **reward model (RM)** — the SFT model with its language-model head replaced by a scalar value head — to predict human preference scores. Training loss is a Bradley-Terry pairwise ranking objective.

The trained RM acts as a learned proxy for human judgement.

### 3. RL Optimisation with PPO
Use **PPO (Proximal Policy Optimization)** to fine-tune the SFT model to maximise expected reward from the RM. A **KL divergence penalty** keeps the policy from drifting too far from the SFT model:

```
reward = RM(prompt, response) − β · KL(policy ‖ SFT_model)
```

The KL penalty prevents **reward hacking** — generating text that gets high RM scores while becoming incoherent or exploiting RM weaknesses.

## Common Failure Modes

- **Reward hacking** — the policy exploits gaps in the reward model. The KL penalty and diverse RM training data mitigate this.
- **Over-refusal** — excessive safety training causes the model to refuse benign requests.
- **RM distribution shift** — the RM was trained on SFT outputs but is scored on PPO outputs that diverge over time.

## Alternatives to RLHF

| Method | Mechanism | Advantage |
|---|---|---|
| **DPO** | Reparameterises RLHF to train directly on preference pairs, no RL | Simpler, stable, widely adopted (Llama-3) |
| **RLAIF** | Uses AI model instead of humans to generate preference labels | Cheaper to scale |
| **Constitutional AI** (Anthropic) | AI self-critique guided by a "constitution" of principles | Reduces human labelling cost |
| **KTO** | Uses individual ratings rather than pairwise comparisons | More data-efficient |

## See Also

- [[fine-tuning-methods]]
- [[lo-ra-adaptations]]
- [[machine-learning]]
- [[knowledge-distillation-methods]]
