"""
obsidian_brain.py
-----------------
A local RAG (Retrieval-Augmented Generation) tool that lets you query your
Obsidian vault using a locally-running LLM via Ollama, presented as a
full-screen terminal UI.

How it works:
  1. INGEST    — Reads files matching FILE_GLOB, splits them into chunks, and
                 stores vector embeddings in a local ChromaDB database on disk.
  2. RETRIEVE  — When you ask a question, it finds the most relevant chunks
                 using semantic similarity search.
  3. JUDGE     — The LLM checks whether those chunks actually answer the question.
  4. GENERATE  — Answers from the best available source, in order of preference:
                   a) Vault notes      (if the judge says context is sufficient)
                   b) Model knowledge  (always shown, even when uncertain)
                   c) Web search       (supplemented when model flags uncertainty)
  5. CONVERSE  — Full back-and-forth conversation history is kept and included
                 in every prompt so the model can refer to earlier exchanges.
  6. LEARN     — Answers from model knowledge or web search are queued as pending
                 notes. Press Ctrl+S at any time to review them, preview their
                 content, confirm or rename each filename, and save to the vault.

Dependencies (install into your venv):
  pip install langchain langchain-ollama langchain-community chromadb duckduckgo-search textual

Ollama models needed (pull once):
  ollama pull nomic-embed-text   # embedding model
  ollama pull llama3.2           # chat/generation model
"""

# ── Imports ───────────────────────────────────────────────────────────────────

import asyncio
import glob
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, Label, RichLog
from rich.markdown import Markdown
from rich.text import Text

from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import DirectoryLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from duckduckgo_search import DDGS


# ── Configuration ─────────────────────────────────────────────────────────────
# Edit these paths to match your setup.

VAULT_PATH = "/home/tizz/dev/LLM-sandbox/"
DB_PATH    = "/home/tizz/dev/LLM-sandbox/local_db"

EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL  = "llama3.2:3b"

FILE_GLOB = "**/*.md"

TOP_K              = 3
WEB_SEARCH_RESULTS = 3
CHUNK_SIZE         = 500
CHUNK_OVERLAP      = 50

# Minimum relevance score (0–1) for a vault chunk to count as a sufficient answer.
# Raise this to be stricter (fewer vault hits); lower it to be more permissive.
SIMILARITY_THRESHOLD = 0.5

# How many past exchanges to include in prompts (each exchange = 1 user + 1 assistant turn).
HISTORY_WINDOW = 4


# ── Model Setup ───────────────────────────────────────────────────────────────

embeddings = OllamaEmbeddings(model=EMBED_MODEL)
llm        = ChatOllama(model=CHAT_MODEL)


# ── Ingestion ─────────────────────────────────────────────────────────────────

def ingest_vault() -> Chroma:
    """
    Load files matching FILE_GLOB from VAULT_PATH, split them into chunks, embed them,
    and store the result in a ChromaDB database at DB_PATH.

    Overwrites any existing database — safe to re-run whenever notes change.
    Returns the loaded Chroma vector store ready for querying.
    """
    print(f"📚 Loading notes from: {VAULT_PATH}")

    loader = DirectoryLoader(VAULT_PATH, glob=FILE_GLOB)
    docs   = loader.load()

    if not docs:
        print("⚠️  No files found. Check your VAULT_PATH and FILE_GLOB.")
        sys.exit(1)

    print(f"   Found {len(docs)} files. Splitting into chunks...")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(docs)

    print(f"   Embedding {len(chunks)} chunks and saving to: {DB_PATH}")

    db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=DB_PATH,
    )

    print(f"✅ Ingestion complete — {len(chunks)} chunks stored.\n")
    return db


def load_existing_db() -> Chroma:
    """
    Load an already-ingested ChromaDB database from disk.
    Raises FileNotFoundError if the database doesn't exist yet.
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"No database found at '{DB_PATH}'.\n"
            "Run the script with --ingest first to build it."
        )
    print(f"📂 Loading existing database from: {DB_PATH}\n")
    return Chroma(persist_directory=DB_PATH, embedding_function=embeddings)


# ── Web Search ─────────────────────────────────────────────────────────────────

def web_search(query: str) -> str:
    """Search DuckDuckGo and return a plain-text summary of top results."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=WEB_SEARCH_RESULTS))

        if not results:
            return "No results found."

        return "\n\n---\n\n".join(
            f"Source: {r['href']}\nTitle: {r['title']}\n{r['body']}"
            for r in results
        )

    except Exception as e:
        return f"Web search failed: {e}"


# ── Learning ──────────────────────────────────────────────────────────────────

@dataclass
class PendingNote:
    """A learnable answer queued for review before being written to the vault."""
    question:   str
    answer:     str
    source:     str
    suggestion: str  # LLM-suggested filename stem, e.g. "photosynthesis"


def get_concept_suggestion(question: str, answer: str) -> str:
    """Ask the LLM for a short concept name; return a sanitised filename stem."""
    prompt = f"""Identify the single core concept or subject that this question and answer are about.
Reply with only 1-3 words, lowercase, no punctuation. This will be used as a filename.

Examples:
  Q: What are cupcakes? → cupcakes
  Q: How does photosynthesis work? → photosynthesis
  Q: Who invented the telephone? → telephone

Question: {question}
Answer: {answer}
Core concept:"""

    raw = llm.invoke(prompt).content.strip().lower()
    sanitised = re.sub(r"[^a-z0-9\s-]", "", raw)
    return re.sub(r"\s+", "-", sanitised.strip()) or "general"


def save_to_vault(concept: str, question: str, answer: str, source: str, db: Chroma) -> None:
    """
    Write a Q/A entry to the vault and add it to the live ChromaDB index.

    Args:
        concept:  Sanitised filename stem chosen by the user (e.g. "cupcakes").
        question: The original user question.
        answer:   The generated answer.
        source:   Where the answer came from.
        db:       Live Chroma instance to update in place.
    """
    filepath  = os.path.join(VAULT_PATH, f"{concept}.md")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    entry = f"\n## Q: {question}\n*Source: {source} — {timestamp}*\n\n{answer}\n"

    if os.path.exists(filepath):
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(entry)
    else:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {concept.replace('-', ' ').title()}\n")
            f.write(entry)

    db.add_documents([Document(
        page_content=f"Q: {question}\n\n{answer}",
        metadata={"source": filepath},
    )])


# ── Retrieval + Generation ─────────────────────────────────────────────────────

def _format_history(history: list[dict]) -> str:
    """Return the last HISTORY_WINDOW exchanges as a plain-text block."""
    recent = history[-(HISTORY_WINDOW * 2):]
    lines  = []
    for msg in recent:
        role    = "User" if msg["role"] == "user" else "Assistant"
        content = msg["content"]
        if len(content) > 600:
            content = content[:600] + "…"
        lines.append(f"{role}: {content}")
    return "\n\n".join(lines)


def build_vault_prompt(question: str, context_chunks: list, history: list[dict]) -> str:
    parts = [
        "You are a helpful assistant with access to the user's personal notes.",
        "Use the context and conversation history below to answer the question.",
        "If the answer isn't covered in the context, say so clearly — don't guess.",
        "",
    ]
    if history:
        parts += ["--- CONVERSATION HISTORY ---", _format_history(history), "--- END HISTORY ---", ""]
    parts += [
        "--- CONTEXT FROM NOTES ---",
        "\n\n---\n\n".join(c.page_content for c in context_chunks),
        "--- END CONTEXT ---",
        "",
        f"Question: {question}",
        "Answer:",
    ]
    return "\n".join(parts)


def build_knowledge_prompt(question: str, history: list[dict]) -> str:
    parts = [
        "Answer the following question using your own knowledge.",
        "If you are not confident in your answer, start your response with the",
        'exact phrase: "I\'m not certain, but"',
        "",
    ]
    if history:
        parts += ["--- CONVERSATION HISTORY ---", _format_history(history), "--- END HISTORY ---", ""]
    parts += [f"Question: {question}", "Answer:"]
    return "\n".join(parts)


def build_web_prompt(question: str, web_context: str, history: list[dict]) -> str:
    parts = [
        "Answer the following question using the web search results below.",
        "Summarise the relevant information clearly and cite the sources where helpful.",
        "",
    ]
    if history:
        parts += ["--- CONVERSATION HISTORY ---", _format_history(history), "--- END HISTORY ---", ""]
    parts += [
        "--- WEB SEARCH RESULTS ---",
        web_context,
        "--- END RESULTS ---",
        "",
        f"Question: {question}",
        "Answer:",
    ]
    return "\n".join(parts)




# ── Shared TUI Styles ─────────────────────────────────────────────────────────

_CSS = """
Screen {
    background: #1e1e1e;
}

Header {
    background: #252526;
    color: #cccccc;
}

Footer {
    background: #252526;
    color: #6c6c6c;
}

RichLog {
    height: 1fr;
    background: #1e1e1e;
    padding: 1 2;
    scrollbar-color: #454545;
    scrollbar-background: #1e1e1e;
}

Input {
    margin: 0 1 1 1;
    background: #252526;
    color: #d4d4d4;
    border: tall #454545;
    padding: 0 1;
}

Input:focus {
    border: tall #5f87af;
}
"""


# ── Note Review Screen ────────────────────────────────────────────────────────

class NoteReviewScreen(ModalScreen[list[tuple[str, PendingNote]]]):
    """
    Modal that walks through all pending notes one at a time.

    For each note the user sees:
      - A scrollable preview of the Q/A content
      - The model's suggested filename
      - An input to confirm, rename, or skip

    Dismissed with the list of (concept, note) pairs the user confirmed.
    The caller is responsible for saving them to the vault.
    """

    CSS = """
    NoteReviewScreen {
        align: center middle;
    }

    #review-box {
        width: 86;
        height: 36;
        border: thick #5f87af;
        background: #252526;
        padding: 1 2;
    }

    #review-header {
        color: #cccccc;
        margin-bottom: 1;
    }

    #preview-log {
        height: 18;
        background: #1e1e1e;
        border: solid #454545;
        padding: 0 1;
        margin-bottom: 1;
        scrollbar-color: #454545;
        scrollbar-background: #1e1e1e;
    }

    #review-suggestion {
        color: #d4d4d4;
        margin-bottom: 1;
    }

    #review-input {
        margin: 0 0 1 0;
        background: #1e1e1e;
        color: #d4d4d4;
        border: tall #454545;
    }

    #review-input:focus {
        border: tall #5f87af;
    }

    #review-help {
        color: #6c6c6c;
    }
    """

    BINDINGS = [Binding("escape", "finish", "Done")]

    def __init__(self, pending: list[PendingNote]) -> None:
        super().__init__()
        self._pending   = pending
        self._confirmed: list[tuple[str, PendingNote]] = []
        self._idx       = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="review-box"):
            yield Label("", id="review-header")
            yield RichLog(id="preview-log", markup=False, wrap=True, highlight=False)
            yield Label("", id="review-suggestion")
            yield Input(id="review-input")
            yield Label(
                "[dim]Enter to save  ·  type 'skip' to skip  ·  Esc to finish[/dim]",
                id="review-help",
            )

    def on_mount(self) -> None:
        self._refresh()
        self.query_one("#review-input", Input).focus()

    def _refresh(self) -> None:
        note  = self._pending[self._idx]
        total = len(self._pending)

        self.query_one("#review-header", Label).update(
            f"[bold]Review notes  {self._idx + 1} / {total}[/bold]"
        )

        log = self.query_one("#preview-log", RichLog)
        log.clear()
        log.write(Markdown(
            f"**Q:** {note.question}\n\n*Source: {note.source}*\n\n{note.answer}"
        ))

        self.query_one("#review-suggestion", Label).update(
            f"Filename: [bold #5f87af]{note.suggestion}.md[/bold #5f87af]"
        )

        inp             = self.query_one("#review-input", Input)
        inp.placeholder = note.suggestion
        inp.value       = ""

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw  = event.value.strip()
        note = self._pending[self._idx]

        if raw.lower() != "skip":
            if raw:
                sanitised = re.sub(r"[^a-z0-9\s-]", "", raw.lower())
                concept   = re.sub(r"\s+", "-", sanitised.strip()) or note.suggestion
            else:
                concept = note.suggestion
            self._confirmed.append((concept, note))

        self._idx += 1
        if self._idx >= len(self._pending):
            self.dismiss(self._confirmed)
        else:
            self._refresh()

    def action_finish(self) -> None:
        self.dismiss(self._confirmed)


# ── Chat App ──────────────────────────────────────────────────────────────────

class ChatApp(App[None]):
    """Main interactive chat TUI with conversation history and deferred note saving."""

    TITLE     = "Obsidian Brain"
    SUB_TITLE = CHAT_MODEL

    CSS = _CSS

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+s", "review_notes", "Save notes"),
        Binding("escape", "clear_input", "Clear input", show=False),
    ]

    def __init__(self, db: Chroma) -> None:
        super().__init__()
        self.db       = db
        self._busy    = False
        self._history: list[dict] = []
        self._pending: list[PendingNote] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(id="log", markup=True, wrap=True, highlight=False)
        yield Input(placeholder="Ask anything about your notes...", id="input")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one(RichLog)
        log.write(Text.from_markup(
            "[dim]Obsidian Brain ready. Ask anything about your notes.[/dim]"
        ))
        log.write(Text.from_markup(
            "[dim]Ctrl+S to review & save pending notes  ·  Ctrl+Q to quit[/dim]\n"
        ))
        self.query_one(Input).focus()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _log(self, markup: str) -> None:
        self.query_one(RichLog).write(Text.from_markup(markup))

    def _queue_note(self, question: str, answer: str, source: str, suggestion: str) -> None:
        self._pending.append(PendingNote(question, answer, source, suggestion))
        count = len(self._pending)
        self.sub_title = f"{CHAT_MODEL}  ·  {count} unsaved note{'s' if count != 1 else ''}"

    # ── Input handling ────────────────────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        question = event.value.strip()
        if not question or self._busy:
            return
        event.input.value = ""
        self._busy = True
        self._log(f"\n[bold #ce9178]> {question}[/bold #ce9178]")
        self._process(question)

    @work
    async def _process(self, question: str) -> None:
        log = self.query_one(RichLog)
        self._history.append({"role": "user", "content": question})

        try:
            # ── Step 1: Vault retrieval ────────────────────────────────────────
            results = await asyncio.to_thread(
                lambda: self.db.similarity_search_with_relevance_scores(question, k=TOP_K)
            )
            chunks    = [doc for doc, _ in results]
            top_score = max((score for _, score in results), default=0.0)

            self._log(f"[dim]🔍  Best vault match: {top_score:.2f}[/dim]")

            if top_score >= SIMILARITY_THRESHOLD:
                self._log("[dim]📓  Source: vault notes[/dim]")
                answer = await asyncio.to_thread(
                    lambda: llm.invoke(
                        build_vault_prompt(question, chunks, self._history[:-1])
                    ).content
                )
                self._history.append({"role": "assistant", "content": answer})
                log.write(Markdown(answer))
                return

            # ── Step 2: Model knowledge (always shown) ─────────────────────────
            self._log("[dim]🧠  Vault score too low — asking model[/dim]")
            model_answer = await asyncio.to_thread(
                lambda: llm.invoke(
                    build_knowledge_prompt(question, self._history[:-1])
                ).content
            )
            uncertain = model_answer.strip().lower().startswith("i'm not certain")

            if uncertain:
                self._log("[dim]🧠  Model knowledge (uncertain)[/dim]")
            else:
                self._log("[dim]🧠  Source: model knowledge[/dim]")

            log.write(Markdown(model_answer))
            self._history.append({"role": "assistant", "content": model_answer})

            suggestion = await asyncio.to_thread(
                lambda: get_concept_suggestion(question, model_answer)
            )
            source = "model knowledge (uncertain)" if uncertain else "model knowledge"
            self._queue_note(question, model_answer, source, suggestion)

            # ── Step 3: Supplement with web search when uncertain ──────────────
            if uncertain:
                self._log("[dim]🌐  Supplementing with web search…[/dim]")
                web_ctx = await asyncio.to_thread(lambda: web_search(question))

                if not web_ctx.startswith("No results") and not web_ctx.startswith("Web search failed"):
                    web_answer = await asyncio.to_thread(
                        lambda: llm.invoke(
                            build_web_prompt(question, web_ctx, self._history)
                        ).content
                    )
                    self._log("[dim]🌐  Web search result:[/dim]")
                    log.write(Markdown(web_answer))

                    web_suggestion = await asyncio.to_thread(
                        lambda: get_concept_suggestion(question, web_answer)
                    )
                    self._queue_note(question, web_answer, "web search", web_suggestion)
                else:
                    self._log("[dim]🌐  Web search returned no results.[/dim]")

        finally:
            self._busy = False
            self.query_one(Input).focus()

    # ── Note review ───────────────────────────────────────────────────────────

    def action_review_notes(self) -> None:
        if not self._pending:
            self._log("[dim]No pending notes to review.[/dim]")
            return
        self.push_screen(
            NoteReviewScreen(list(self._pending)),
            callback=self._after_review,
        )

    def _after_review(self, confirmed: list[tuple[str, PendingNote]]) -> None:
        self._pending.clear()
        self.sub_title = CHAT_MODEL
        if confirmed:
            self._save_confirmed(confirmed)
        else:
            self._log("[dim]No notes saved.[/dim]")

    @work
    async def _save_confirmed(self, confirmed: list[tuple[str, PendingNote]]) -> None:
        for concept, note in confirmed:
            c, n = concept, note
            await asyncio.to_thread(
                lambda: save_to_vault(c, n.question, n.answer, n.source, self.db)
            )
        count = len(confirmed)
        self._log(
            f"[dim]📝  {count} note{'s' if count != 1 else ''} saved to vault.[/dim]"
        )

    # ── Other actions ─────────────────────────────────────────────────────────

    def action_clear_input(self) -> None:
        self.query_one(Input).value = ""

    def action_quit(self) -> None:
        self.exit()


# ── Organise App ──────────────────────────────────────────────────────────────

class OrganizeApp(App[None]):
    """
    Standalone TUI for vault organisation: adds YAML frontmatter tags and
    inserts Obsidian [[wikilinks]]. Launched with --organize.

    Each suggestion is shown in the log; the input at the bottom accepts:
      Enter          — accept the suggestion as-is
      'skip'         — skip this note
      custom text    — override (comma-separated tags, or a renamed filename)
    """

    TITLE     = "Obsidian Brain  ·  Organise Vault"
    SUB_TITLE = "Tags & Wikilinks"

    CSS = _CSS

    BINDINGS = [Binding("ctrl+q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(id="log", markup=True, wrap=True, highlight=False)
        yield Input(
            placeholder="Enter to accept  ·  'skip' to skip  ·  type to override…",
            id="input",
        )
        yield Footer()

    def on_mount(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self.query_one(Input).focus()
        self._run_organize()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.input.value = ""
        self._queue.put_nowait(event.value.strip())

    def _log(self, markup: str) -> None:
        self.query_one(RichLog).write(Text.from_markup(markup))

    async def _prompt(self, hint: str = "") -> str:
        if hint:
            self._log(f"[dim]{hint}[/dim]")
        return await self._queue.get()

    @work
    async def _run_organize(self) -> None:
        md_files = sorted(glob.glob(os.path.join(VAULT_PATH, "*.md")))
        if not md_files:
            self._log("[red]No .md files found in vault.[/red]")
            return

        notes = {}
        for path in md_files:
            stem = os.path.splitext(os.path.basename(path))[0]
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
            h1 = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            notes[stem] = {
                "path":    path,
                "title":   h1.group(1).strip() if h1 else stem,
                "content": content,
            }

        self._log(f"[bold]Organising {len(notes)} notes…[/bold]\n")

        # ── Pass 1: Frontmatter tags ───────────────────────────────────────────

        note_list_str = "\n".join(
            f"- {s} ({d['title']}): {d['content'][:300].strip()}"
            for s, d in notes.items()
        )

        tag_prompt = f"""You are organising a personal knowledge vault.
Suggest 1-3 lowercase tags for each note. Use the same tags across related notes
so they can be found together (e.g. both a "machine learning" note and a "language
models" note should share an "ai" tag).
Reply in this exact format, one note per line:
stem: tag1, tag2

Notes:
{note_list_str}

Tags:"""

        self._log("[dim]Generating tag suggestions…[/dim]")
        raw_tags = await asyncio.to_thread(lambda: llm.invoke(tag_prompt).content.strip())

        tag_map: dict[str, list[str]] = {}
        for line in raw_tags.splitlines():
            if ":" not in line:
                continue
            stem_part, tags_part = line.split(":", 1)
            key  = stem_part.strip().lstrip("- ").strip()
            tags = [t.strip() for t in tags_part.split(",") if t.strip()]
            for note_stem in notes:
                if note_stem.lower() == key.lower() or key.lower() in note_stem.lower():
                    tag_map[note_stem] = tags
                    break

        for stem, data in notes.items():
            content = data["content"]
            if content.lstrip().startswith("---"):
                self._log(f"[dim]⏭  {stem}.md — already has frontmatter[/dim]")
                continue
            suggested = tag_map.get(stem)
            if not suggested:
                continue

            self._log(f"\n[bold #5f87af]{stem}.md[/bold #5f87af]")
            self._log(f"  Suggested tags: [bold]{', '.join(suggested)}[/bold]")

            raw = await self._prompt(
                "  Enter to accept · 'skip' to skip · comma-separated to override:"
            )
            if raw.lower() == "skip":
                continue

            final       = [t.strip() for t in raw.split(",")] if raw else suggested
            frontmatter = "---\ntags:\n" + "".join(f"  - {t}\n" for t in final) + "---\n"
            new_content = frontmatter + content

            with open(data["path"], "w", encoding="utf-8") as f:
                f.write(new_content)
            notes[stem]["content"] = new_content
            self._log("  [green]✓ Tags written.[/green]")

        # ── Pass 2: Wikilinks ──────────────────────────────────────────────────

        self._log("\n[bold]Scanning for wikilink opportunities…[/bold]")

        for stem, data in notes.items():
            content     = data["content"]
            other_notes = {s: d["title"] for s, d in notes.items() if s != stem}
            if not other_notes:
                continue

            link_prompt = f"""You are editing a markdown note to add Obsidian [[wikilinks]].
Available notes to link to:
{chr(10).join(f"  {s}: {t}" for s, t in other_notes.items())}

Find phrases in the note BODY that clearly refer to one of the above notes.
Rules:
- Only suggest the FIRST occurrence of each phrase.
- Do not suggest anything inside existing [[...]] brackets.
- Do not suggest anything inside the YAML frontmatter block (between --- markers).
Reply one suggestion per line in this exact format, or reply "none":
"exact phrase" -> target_stem

Note:
{content}

Suggestions:"""

            raw = await asyncio.to_thread(lambda: llm.invoke(link_prompt).content.strip())
            if not raw or raw.lower() == "none":
                continue

            subs: list[tuple[str, str]] = []
            for line in raw.splitlines():
                if "->" not in line:
                    continue
                phrase_part, target_part = line.split("->", 1)
                phrase = phrase_part.strip().strip('"').strip("'")
                target = target_part.strip().strip('"').strip("'")
                if target in notes and phrase and phrase in content:
                    subs.append((phrase, target))

            if not subs:
                continue

            self._log(f"\n[bold #5f87af]{stem}.md[/bold #5f87af] — suggested links:")
            for phrase, target in subs:
                self._log(f"  '[yellow]{phrase}[/yellow]'  →  [[{target}]]")

            raw = await self._prompt("  Enter to accept · 'skip' to skip:")
            if raw.lower() == "skip":
                continue

            if content.lstrip().startswith("---"):
                fm_end   = content.find("---", content.index("---") + 3) + 3
                fm_block = content[:fm_end]
                body     = content[fm_end:]
            else:
                fm_block = ""
                body     = content

            for phrase, target in subs:
                title_t = notes[target]["title"]
                link = (
                    f"[[{target}]]"
                    if phrase.lower() in (target.lower(), title_t.lower())
                    else f"[[{target}|{phrase}]]"
                )
                body = body.replace(phrase, link, 1)

            new_content = fm_block + body
            if new_content != content:
                with open(data["path"], "w", encoding="utf-8") as f:
                    f.write(new_content)
                notes[stem]["content"] = new_content
                self._log("  [green]✓ Links added.[/green]")

        self._log("\n[bold green]✓ Vault organisation complete.[/bold green]")
        self._log("[dim]Press Ctrl+Q to exit.[/dim]")

    def action_quit(self) -> None:
        self.exit()


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Usage:
    #   python obsidian_brain.py             # start chat TUI (uses existing DB)
    #   python obsidian_brain.py --ingest    # rebuild DB from vault, then start chat TUI
    #   python obsidian_brain.py --organize  # organise vault (tags + wikilinks)

    if "--organize" in sys.argv:
        OrganizeApp().run()
        sys.exit(0)

    if "--ingest" in sys.argv:
        db = ingest_vault()
    else:
        try:
            db = load_existing_db()
        except FileNotFoundError as e:
            print(f"❌ {e}")
            sys.exit(1)

    ChatApp(db).run()
