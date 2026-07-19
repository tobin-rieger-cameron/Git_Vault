---
title: "RLHF Reference"
tags: [machinelearning, ai, meta]
---

# RLHF Reference

RLHF (Reinforcement Learning from Human Feedback) is a three-stage training pipeline that aligns a pretrained language model with human preferences. Used by OpenAI (ChatGPT), Anthropic (Claude), and Meta (Llama-2-Chat).

## The Three Stages

### Stage 1: Supervised Fine-Tuning (SFT)
Start with a pretrained base model and fine-tune it on a dataset of human-written (prompt, response) demonstrations. This teaches the model the format and basic instruction-following behaviour before preference learning begins.

The SFT model is the starting point for the next two stages.

### Stage 2: Reward Model Training
Collect human **preference comparisons**: for each prompt, show labellers two responses (A and B) and ask which they prefer. Collect thousands of these comparison pairs.

Train a separate **reward model (RM)** — typically the SFT model with its final LM head replaced by a scalar output — to predict the human preference score for any (prompt, response) pair. The RM is trained with a Bradley-Terry pairwise ranking loss.

After training, the RM acts as a proxy for "what would humans prefer?"

### Stage 3: RL Optimisation (PPO)
Use **PPO (Proximal Policy Optimization)** to fine-tune the SFT model to maximise the reward model's score:

- The **policy** is the LLM being trained
- The **reward signal** comes from the reward model
- A **KL divergence penalty** keeps the policy from drifting too far from the SFT model (prevents reward hacking — generating text that scores high on the RM but becomes incoherent)

The KL penalty takes the form: `reward = RM(prompt, response) - β · KL(policy || SFT)`

## Why RLHF Works

Pretraining on web text teaches the model to predict internet text — including harmful, biased, or unhelpful content. SFT alone teaches format but not nuance. The reward model captures subtle human preferences (helpfulness, harmlessness, honesty) that are hard to specify as rules.

## Variants and Alternatives

**DPO (Direct Preference Optimization)** — skips the explicit reward model and RL entirely. Optimises a reparameterised objective directly on preference pairs. Simpler, more stable, now widely used. Llama-3-Instruct uses DPO.

**RLAIF (AI Feedback)** — uses a stronger AI model to generate preference labels instead of human labellers. Cheaper to scale.

**Constitutional AI (Anthropic)** — uses a set of principles ("the constitution") and AI self-critique to generate preference data. The model critiques and revises its own outputs before human labellers review.

**KTO (Kahneman-Tversky Optimisation)** — uses individual human ratings rather than pairwise comparisons. More data-efficient.

## Common Failure Modes

- **Reward hacking** — the policy learns to game the reward model without actually improving. The KL penalty and careful RM training mitigate this.
- **Reward model collapse** — RM generalises poorly to out-of-distribution prompts. Fixed by training RM on a diverse prompt distribution.
- **Over-refusal** — excessive harmlessness training makes the model refuse benign requests.

## See Also

- [[Fine-Tuning Methods]]
- [[_Ref Fine Tuning]]
- [[lo-ra-adaptations]]
- [[Machine Learning]]
