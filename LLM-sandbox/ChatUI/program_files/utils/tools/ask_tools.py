"""answer_question — the ask command: agentic retrieval over the vault via search_vault/read_vault_file/web_search."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Callable

from program_files.utils import agent
from program_files.utils.llm import ModelClient
from program_files.utils.models import AskResult, Chunk, RetrievalPath
from program_files.utils.retrieval import Retriever
from program_files.utils.tools import ToolSpec
from program_files.utils.tools.vault_tools import build_vault_tools
from program_files.utils.tools.web_tools import build_web_tools
from program_files.utils.vault import Vault

_log = logging.getLogger(__name__)

_TOPIC_RE = re.compile(
    r"^\s*(?:what\s+(?:is|are|was|were)|explain(?:\s+to\s+me)?|describe|"
    r"overview\s+of|introduction\s+to|tell\s+me\s+about|"
    r"how\s+does|how\s+do)\s+(?:the\s+|a\s+|an\s+)?(.+?)[?.!]?\s*$",
    re.IGNORECASE,
)


def build_ask_tools(vault: Vault, retriever: Retriever, model: ModelClient, web_search_results: int) -> list[ToolSpec]:
    """Build the answer_question command tool, closing over the app's Vault/Retriever/ModelClient."""

    async def _answer_question(args: dict) -> AskResult:
        return await answer_question(
            args["question"],
            vault,
            retriever,
            model,
            args.get("history", []),
            args.get("web_enabled", False),
            top_k=args.get("top_k", 5),
            similarity_threshold=args.get("similarity_threshold", 0.65),
            history_window=args.get("history_window", 2),
            web_search_results=web_search_results,
            on_tool_call=args.get("on_tool_call"),
            on_token=args.get("on_token"),
            on_status=args.get("on_status"),
        )

    return [
        ToolSpec(
            name="answer_question",
            description="Answer a question using the vault as primary context, agentically searching/reading/web-searching as needed.",
            parameters={
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "history": {"type": "array"},
                    "web_enabled": {"type": "boolean"},
                },
                "required": ["question"],
            },
            handler=_answer_question,
        )
    ]


async def answer_question(
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
    on_tool_call: Callable[[str, dict], None] | None = None,
    on_token: Callable[[str], None] | None = None,
    on_status: Callable[[str], None] | None = None,
) -> AskResult:
    """Route the question through VAULT/WEAK_MATCH/MODEL_KNOWLEDGE per CLAUDE.md's retrieval table, agentically."""
    if on_status is not None:
        on_status("searching vault…")
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
    if on_status is not None:
        on_status(_status_for_path(path, chunks))
    history_text = _format_history(history, history_window)
    topic = _extract_topic(question)
    depth = _depth_hint(topic) if topic else ""

    touched_sources: list[Path] = [c.source_path for c in chunks]
    toolbox = build_vault_tools(vault, retriever, touched_sources)
    if web_enabled:
        toolbox += build_web_tools(web_search_results)

    if path is RetrievalPath.VAULT:
        prompt = _build_vault_prompt(question, chunks, history_text, depth, web_enabled)
    elif path is RetrievalPath.WEAK_MATCH:
        prompt = _build_weak_match_prompt(question, chunks, history_text, depth, web_enabled)
    else:
        prompt = _build_knowledge_prompt(question, history_text, depth, web_enabled)

    if on_status is not None:
        on_status(f"asking {model.chat_model_name}…")
    result = await agent.run(model, prompt, toolbox, touched_sources, on_tool_call=on_tool_call, on_token=on_token)
    sources = sorted({_relative_to_vault(p, vault) for p in result.sources}, key=str)
    return AskResult(answer=result.answer, path=path, sources=sources)


def _status_for_path(path: RetrievalPath, chunks: list[Chunk]) -> str:
    """Phase-status line for the retrieval path just chosen, for UI display while the model runs."""
    if path is RetrievalPath.VAULT:
        return f"found {len(chunks)} relevant note(s), top score {chunks[0].score:.2f}"
    if path is RetrievalPath.WEAK_MATCH:
        return "weak vault match — answering mostly from training knowledge"
    return "no relevant notes — answering from training knowledge"


def choose_retrieval_path(chunks: list[Chunk], threshold: float) -> RetrievalPath:
    """Choose VAULT if the top chunk clears threshold, WEAK_MATCH if chunks exist but don't, else MODEL_KNOWLEDGE."""
    if not chunks:
        return RetrievalPath.MODEL_KNOWLEDGE
    top_score = max(c.score for c in chunks)
    return RetrievalPath.VAULT if top_score >= threshold else RetrievalPath.WEAK_MATCH


def is_broad_topic_question(question: str) -> bool:
    """Return True for phrasing like "what is X"/"explain X" that _TOPIC_RE recognizes as topic-shaped."""
    return _extract_topic(question) is not None


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


def _tool_usage_note(path: RetrievalPath, web_enabled: bool) -> str:
    lines = []
    if path is RetrievalPath.VAULT:
        lines.append("You have search_vault and read_vault_file available if the context above isn't enough.")
    elif path is RetrievalPath.WEAK_MATCH:
        lines.append("The notes above only weakly match — try search_vault with different phrasing, or "
                      "read_vault_file for full detail, before falling back to your own knowledge.")
    else:
        lines.append("No matching notes were found by the initial search — use search_vault to double-check "
                      "before concluding there's nothing relevant.")
    if web_enabled:
        lines.append("web_search is also available for current information not in your training data or the vault.")
    return " ".join(lines)


def _build_vault_prompt(
    question: str, chunks: list[Chunk], history_text: str, depth: str = "", web_enabled: bool = False
) -> str:
    parts = [
        "You are a helpful assistant with access to the user's personal notes.",
        "Use the context to answer the question as specifically as possible.",
        "If the context does not contain enough information, supplement it with "
        "your own knowledge and say which parts came from your training rather "
        "than the notes.",
        "",
        _tool_usage_note(RetrievalPath.VAULT, web_enabled),
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


def _build_weak_match_prompt(
    question: str, chunks: list[Chunk], history_text: str, depth: str = "", web_enabled: bool = False
) -> str:
    parts = [
        "You are a helpful assistant. Answer the question fully using your own training knowledge.",
        "The following notes from the user's vault may add useful context — incorporate "
        "them only if they directly address the question. Do not let off-topic notes "
        "distort your answer.",
        "",
        _tool_usage_note(RetrievalPath.WEAK_MATCH, web_enabled),
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


def _build_knowledge_prompt(question: str, history_text: str, depth: str = "", web_enabled: bool = False) -> str:
    parts = [
        "Answer the following question, using your own knowledge.",
        "",
        _tool_usage_note(RetrievalPath.MODEL_KNOWLEDGE, web_enabled),
    ]
    if depth:
        parts += ["", depth]
    parts += [""]
    if history_text:
        parts += ["--- CONVERSATION HISTORY ---", history_text, "--- END HISTORY ---", ""]
    parts += [f"Question: {question}", "Answer:"]
    return "\n".join(parts)
