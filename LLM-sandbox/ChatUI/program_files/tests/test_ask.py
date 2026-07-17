from pathlib import Path

import pytest

from chatui.ask import (
    ask,
    choose_retrieval_path,
    is_broad_topic_question,
    source_covers_topic,
)
from chatui.models import Chunk, RetrievalPath
from chatui.vault import Vault


def _chunk(text: str, score: float, source: str = "A.md", tags: list[str] | None = None) -> Chunk:
    return Chunk(text=text, source_path=Path(source), tags=tags or [], score=score)


def test_choose_retrieval_path_no_chunks_is_model_knowledge() -> None:
    assert choose_retrieval_path([], threshold=0.65) is RetrievalPath.MODEL_KNOWLEDGE


def test_choose_retrieval_path_above_threshold_is_vault() -> None:
    chunks = [_chunk("x", 0.7), _chunk("y", 0.5)]
    assert choose_retrieval_path(chunks, threshold=0.65) is RetrievalPath.VAULT


def test_choose_retrieval_path_below_threshold_is_weak_match() -> None:
    chunks = [_chunk("x", 0.4)]
    assert choose_retrieval_path(chunks, threshold=0.65) is RetrievalPath.WEAK_MATCH


def test_choose_retrieval_path_uses_top_score_not_first_chunk() -> None:
    chunks = [_chunk("low", 0.3), _chunk("high", 0.9)]
    assert choose_retrieval_path(chunks, threshold=0.65) is RetrievalPath.VAULT


@pytest.mark.parametrize(
    "question",
    [
        "What is taxonomy?",
        "Explain fine-tuning methods",
        "Tell me about RLHF",
        "How does gradient descent work",
        "Describe the transformer architecture",
    ],
)
def test_is_broad_topic_question_true_for_class_questions(question: str) -> None:
    assert is_broad_topic_question(question) is True


@pytest.mark.parametrize("question", ["Did I write anything about cupcakes last week?", "yes", "ok thanks"])
def test_is_broad_topic_question_false_for_narrow_questions(question: str) -> None:
    assert is_broad_topic_question(question) is False


def test_source_covers_topic_matches_shared_keyword() -> None:
    sources = [Path("Fine Tuning Methods.md"), Path("Cupcakes.md")]
    assert source_covers_topic(sources, "fine-tuning methods") is True


def test_source_covers_topic_false_when_no_overlap() -> None:
    sources = [Path("Cupcakes.md")]
    assert source_covers_topic(sources, "reinforcement learning from human feedback") is False


def test_source_covers_topic_false_for_empty_sources() -> None:
    assert source_covers_topic([], "taxonomy") is False


class _FakeRetriever:
    def __init__(self, chunks: list[Chunk], scoped_chunks: list[Chunk] | None = None) -> None:
        self._chunks = chunks
        self._scoped_chunks = scoped_chunks or []
        self.search_calls: list[tuple[str, int]] = []
        self.scoped_calls: list[tuple[str, list[str], int]] = []

    def search(self, query: str, top_k: int) -> list[Chunk]:
        self.search_calls.append((query, top_k))
        return self._chunks

    def search_scoped(self, query: str, tags: list[str], top_k: int) -> list[Chunk]:
        self.scoped_calls.append((query, tags, top_k))
        return self._scoped_chunks


class _FakeModel:
    def __init__(self, answer: str = "an answer") -> None:
        self.answer = answer
        self.prompts: list[str] = []

    async def stream(self, prompt: str, on_token=None) -> str:
        self.prompts.append(prompt)
        return self.answer


@pytest.mark.asyncio
async def test_ask_vault_path_no_web_when_disabled(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    chunks = [_chunk("Taxonomy is...", 0.9, source=str(tmp_path / "Taxonomy.md"))]
    retriever = _FakeRetriever(chunks)
    model = _FakeModel("Taxonomy is the science of classification.")

    result = await ask(
        "What is taxonomy?", vault, retriever, model, history=[], web_enabled=False,
        similarity_threshold=0.65,
    )

    assert result.path is RetrievalPath.VAULT
    assert result.answer == "Taxonomy is the science of classification."
    assert result.sources == [Path("Taxonomy.md")]
    assert result.web_supplement is None
    assert len(model.prompts) == 1


@pytest.mark.asyncio
async def test_ask_model_knowledge_path_when_no_chunks(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    retriever = _FakeRetriever(chunks=[])
    model = _FakeModel("Some answer from training knowledge.")

    result = await ask("Random question", vault, retriever, model, history=[], web_enabled=False)

    assert result.path is RetrievalPath.MODEL_KNOWLEDGE
    assert result.sources == []


@pytest.mark.asyncio
async def test_ask_weak_match_path_below_threshold(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    chunks = [_chunk("tangential note", 0.3, source=str(tmp_path / "Other.md"))]
    retriever = _FakeRetriever(chunks)
    model = _FakeModel("An answer mostly from training knowledge.")

    result = await ask(
        "What is quantum computing?", vault, retriever, model, history=[], web_enabled=True,
        similarity_threshold=0.65,
    )

    assert result.path is RetrievalPath.WEAK_MATCH
    # weak-match path never adds a web supplement, even with web enabled
    assert result.web_supplement is None


@pytest.mark.asyncio
async def test_ask_passes_history_into_prompt(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    retriever = _FakeRetriever(chunks=[])
    model = _FakeModel("answer")

    await ask(
        "Follow-up question", vault, retriever, model,
        history=[("Earlier question", "Earlier answer")], web_enabled=False,
    )

    assert "Earlier question" in model.prompts[0]
    assert "Earlier answer" in model.prompts[0]


@pytest.mark.asyncio
async def test_ask_tag_rescope_used_when_close_to_top_score(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    initial = [_chunk("broad match", 0.7, source="Broad.md", tags=["ai"])]
    scoped = [_chunk("scoped match", 0.68, source="Scoped.md", tags=["ai"])]
    retriever = _FakeRetriever(initial, scoped_chunks=scoped)
    model = _FakeModel("answer")

    result = await ask("What is AI?", vault, retriever, model, history=[], web_enabled=False)

    assert retriever.scoped_calls, "expected a tag-scoped second search to have run"
    assert result.sources == [Path("Scoped.md")]
