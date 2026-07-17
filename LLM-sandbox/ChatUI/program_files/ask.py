"""Verb 1 — Ask: vault-first RAG, falling back to weak-match/model-knowledge, with optional web supplement."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from chatui.llm import ModelClient
from chatui.models import AskResult, Chunk, RetrievalPath
from chatui.retrieval import Retriever
from chatui.vault import Vault
from chatui.web import search_web

_log = logging.getLogger(__name__)

_UNCERTAIN_PREFIX = "i'm not certain"

_TOPIC_RE = re.compile(
    r"^\s*(?:what\s+(?:is|are|was|were)|explain(?:\s+to\s+me)?|describe|"
    r"overview\s+of|introduction\s+to|tell\s+me\s+about|"
    r"how\s+does|how\s+do)\s+(?:the\s+|a\s+|an\s+)?(.+?)[?.!]?\s*$",
    re.IGNORECASE,
)

_STOP_WORDS = {"the", "a", "an", "of", "in", "is", "are", "and", "to", "for"}


async def ask(
    question: str,
    vault: Vault,
    retriever: Retriever,
    model: ModelClient,
    history: list[tuple[str, str]],
    web_enabled: bool,
    *,
    top_k: int = 5,
    similarity_threshold: float = 0.65,
    history_window: int = 2,
    web_search_results: int = 3,
) -> AskResult:
    """Route the question through VAULT/WEAK_MATCH/MODEL_KNOWLEDGE per CLAUDE.md's retrieval table."""
    chunks = retriever.search(question, top_k)
    if chunks:
        top_tags = chunks[0].tags
        if top_tags:
            # Re-search scoped to the top hit's tags; keep the scoped set only if it's not
            # meaningfully worse, since a tag-filtered search can surface a better-fitting chunk
            # that the unscoped top-k cutoff missed.
            scoped = retriever.search_scoped(question, top_tags, top_k * 2)
            if scoped and max(c.score for c in scoped) >= max(c.score for c in chunks) * 0.9:
                chunks = scoped

    path = choose_retrieval_path(chunks, similarity_threshold)
    _log.debug(
        "path=%s scores=%s threshold=%s question=%r",
        path.name, [round(c.score, 3) for c in chunks], similarity_threshold, question,
    )
    history_text = _format_history(history, history_window)
    sources = sorted({_relative_to_vault(c.source_path, vault) for c in chunks}, key=str)

    topic = _extract_topic(question)
    depth = _depth_hint(topic) if topic else ""

    web_supplement: str | None = None

    if path is RetrievalPath.VAULT:
        answer = await model.stream(_build_vault_prompt(question, chunks, history_text, depth))
        if web_enabled and topic and not source_covers_topic(sources, topic):
            web_supplement = await _web_supplement(model, question, web_search_results, history_text)
    elif path is RetrievalPath.WEAK_MATCH:
        answer = await model.stream(_build_weak_match_prompt(question, chunks, history_text, depth))
    else:
        answer = await model.stream(_build_knowledge_prompt(question, history_text, depth))
        if web_enabled:
            web_supplement = await _web_supplement(model, question, web_search_results, history_text)

    return AskResult(answer=answer, path=path, sources=sources, web_supplement=web_supplement)


def choose_retrieval_path(chunks: list[Chunk], threshold: float) -> RetrievalPath:
    """Choose VAULT if the top chunk clears threshold, WEAK_MATCH if chunks exist but don't, else MODEL_KNOWLEDGE."""
    if not chunks:
        return RetrievalPath.MODEL_KNOWLEDGE
    top_score = max(c.score for c in chunks)
    return RetrievalPath.VAULT if top_score >= threshold else RetrievalPath.WEAK_MATCH


def is_broad_topic_question(question: str) -> bool:
    """Return True for phrasing like "what is X"/"explain X" that _TOPIC_RE recognizes as topic-shaped."""
    return _extract_topic(question) is not None


def source_covers_topic(sources: list[Path], topic: str) -> bool:
    """Return True if any source filename shares a non-stopword with the topic phrase (a heuristic, not exact matching)."""
    topic_words = {w for w in re.findall(r"\w+", topic.lower()) if w not in _STOP_WORDS and len(w) > 2}
    if not topic_words:
        return False
    for source in sources:
        stem_words = set(re.findall(r"\w+", source.stem.lower()))
        if topic_words & stem_words:
            return True
    return False


def _extract_topic(question: str) -> str | None:
    match = _TOPIC_RE.match(question.strip())
    return match.group(1).strip() if match else None


def _relative_to_vault(path: Path, vault: Vault) -> Path:
    try:
        return path.relative_to(vault.root)
    except ValueError:
        return path


def _format_history(history: list[tuple[str, str]], window: int) -> str:
    recent = history[-window:] if window > 0 else []
    lines = []
    for question, answer in recent:
        lines.append(f"User: {_truncate(question)}")
        lines.append(f"Assistant: {_truncate(answer)}")
    return "\n\n".join(lines)


def _truncate(text: str, limit: int = 600) -> str:
    return text if len(text) <= limit else text[:limit] + "…"


def _depth_hint(topic: str) -> str:
    return (
        f'This is a broad question about "{topic}". '
        "Answer conversationally but comprehensively — cover the definition, "
        "historical context, key subfields or variants, applications, and "
        "relationship to adjacent concepts. Draw on your training knowledge to "
        "fill any gaps the notes don't cover. Write in fluent prose. Do not use "
        "markdown headers, bullet lists, or article formatting — this is a "
        "conversation, not a document."
    )


def _build_vault_prompt(question: str, chunks: list[Chunk], history_text: str, depth: str = "") -> str:
    parts = [
        "You are a helpful assistant with access to the user's personal notes.",
        "Use the context to answer the question as specifically as possible.",
        "If the context does not contain enough information, supplement it with "
        "your own knowledge and say which parts came from your training rather "
        "than the notes.",
    ]
    if depth:
        parts += ["", depth]
    parts += [""]
    if history_text:
        parts += ["--- CONVERSATION HISTORY ---", history_text, "--- END HISTORY ---", ""]
    parts += [
        "--- CONTEXT FROM NOTES ---",
        "\n\n---\n\n".join(c.text for c in chunks),
        "--- END CONTEXT ---",
        "",
        f"Question: {question}",
        "Answer:",
    ]
    return "\n".join(parts)


def _build_weak_match_prompt(question: str, chunks: list[Chunk], history_text: str, depth: str = "") -> str:
    parts = [
        "You are a helpful assistant. Answer the question fully using your own training knowledge.",
        "The following notes from the user's vault may add useful context — incorporate "
        "them only if they directly address the question. Do not let off-topic notes "
        "distort your answer.",
    ]
    if depth:
        parts += ["", depth]
    parts += [""]
    if history_text:
        parts += ["--- CONVERSATION HISTORY ---", history_text, "--- END HISTORY ---", ""]
    parts += [
        "--- CONTEXT FROM NOTES ---",
        "\n\n---\n\n".join(c.text for c in chunks),
        "--- END CONTEXT ---",
        "",
        f"Question: {question}",
        "Answer:",
    ]
    return "\n".join(parts)


def _build_knowledge_prompt(question: str, history_text: str, depth: str = "") -> str:
    parts = [
        "Answer the following question using your own knowledge.",
        f'If you are not confident, start with: "{_UNCERTAIN_PREFIX.capitalize()}, but"',
    ]
    if depth:
        parts += ["", depth]
    parts += [""]
    if history_text:
        parts += ["--- CONVERSATION HISTORY ---", history_text, "--- END HISTORY ---", ""]
    parts += [f"Question: {question}", "Answer:"]
    return "\n".join(parts)


def _build_web_prompt(question: str, web_context: str, history_text: str) -> str:
    parts = [
        "Answer the following question using the web search results below.",
        "Summarise the relevant information clearly and cite sources where helpful.",
        "",
    ]
    if history_text:
        parts += ["--- CONVERSATION HISTORY ---", history_text, "--- END HISTORY ---", ""]
    parts += [
        "--- WEB SEARCH RESULTS ---",
        web_context,
        "--- END RESULTS ---",
        "",
        f"Question: {question}",
        "Answer:",
    ]
    return "\n".join(parts)


async def _web_supplement(model: ModelClient, question: str, max_results: int, history_text: str) -> str | None:
    results = search_web(question, max_results)
    if not results:
        return None
    web_context = "\n\n---\n\n".join(f"Source: {r.url}\nTitle: {r.title}\n{r.snippet}" for r in results)
    return await model.stream(_build_web_prompt(question, web_context, history_text))
