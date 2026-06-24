"""
chatui.py — local RAG chat interface for your Obsidian vault.
All functions are available as /commands within the chat.

/help     list commands          /ingest   rebuild vector DB
/organize tag notes + wikilinks  /savefile review & save notes
/clear    reset history          /web      toggle web search
"""

from __future__ import annotations

import asyncio
import glob
import os
import re
import shutil
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

try:
    from duckduckgo_search import DDGS
    _DDG_AVAILABLE = True
except ImportError:
    _DDG_AVAILABLE = False


# ── Config ────────────────────────────────────────────────────────────────────

VAULT_PATH        = "/home/tizz/dev/LLM-sandbox/"
DB_PATH           = "/home/tizz/dev/LLM-sandbox/local_db"
CONVERSATIONS_DIR = os.path.join(VAULT_PATH, "conversations")

EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL  = "llama3.2:3b"
FILE_GLOB   = "**/*.md"

TOP_K              = 3
WEB_SEARCH_RESULTS = 3
CHUNK_SIZE         = 500
CHUNK_OVERLAP      = 50
SIMILARITY_THRESHOLD = 0.5
HISTORY_WINDOW     = 4

embeddings = OllamaEmbeddings(model=EMBED_MODEL)
llm        = ChatOllama(model=CHAT_MODEL)


# ── Tag Helpers ───────────────────────────────────────────────────────────────

def _extract_frontmatter_tags(content: str) -> list[str]:
    if not content.lstrip().startswith("---"):
        return []
    m = re.match(r'^-{3}\s*\n(.*?)\n-{3}', content, re.DOTALL)
    if not m:
        return []
    return re.findall(r'^\s*-\s+(\S+)', m.group(1), re.MULTILINE)


def _tags_to_metadata(tags: list[str]) -> dict:
    return {f"tag_{t}": True for t in tags}


def _get_chunk_tags(doc: Document) -> list[str]:
    return [k[4:] for k, v in doc.metadata.items() if k.startswith("tag_") and v is True]


def _make_tag_filter(tags: list[str]) -> dict:
    if len(tags) == 1:
        return {f"tag_{tags[0]}": True}
    return {"$or": [{f"tag_{t}": True} for t in tags]}


# ── Database ──────────────────────────────────────────────────────────────────

def ingest_vault() -> Chroma:
    loader = DirectoryLoader(VAULT_PATH, glob=FILE_GLOB)
    docs   = loader.load()
    if not docs:
        raise RuntimeError("No markdown files found in vault.")

    for doc in docs:
        src = doc.metadata.get("source", "")
        if src.endswith(".md"):
            try:
                with open(src, encoding="utf-8") as fh:
                    doc.metadata.update(_tags_to_metadata(_extract_frontmatter_tags(fh.read())))
            except OSError:
                pass

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks   = splitter.split_documents(docs)

    if os.path.exists(DB_PATH):
        shutil.rmtree(DB_PATH)

    return Chroma.from_documents(documents=chunks, embedding=embeddings, persist_directory=DB_PATH)


def load_existing_db() -> Chroma | None:
    if not os.path.exists(DB_PATH):
        return None
    return Chroma(persist_directory=DB_PATH, embedding_function=embeddings)


# ── Web Search ────────────────────────────────────────────────────────────────

def web_search(query: str) -> str:
    if not _DDG_AVAILABLE:
        return "duckduckgo-search not installed."
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=WEB_SEARCH_RESULTS))
        if not results:
            return "No results found."
        return "\n\n---\n\n".join(
            f"Source: {r['href']}\nTitle: {r['title']}\n{r['body']}" for r in results
        )
    except Exception as e:
        return f"Web search failed: {e}"


# ── Learning ──────────────────────────────────────────────────────────────────

@dataclass
class PendingNote:
    question:   str
    answer:     str
    source:     str
    suggestion: str


def get_concept_suggestion(question: str, answer: str) -> str:
    prompt = (
        "Identify the single core concept this question and answer are about.\n"
        "Reply with only 1-3 words, lowercase, no punctuation. Used as a filename.\n"
        f"Question: {question}\nAnswer: {answer}\nCore concept:"
    )
    raw = llm.invoke(prompt).content.strip().lower()
    return re.sub(r"\s+", "-", re.sub(r"[^a-z0-9\s-]", "", raw).strip()) or "general"


def save_to_vault(concept: str, question: str, answer: str, source: str, db: Chroma) -> None:
    filepath  = os.path.join(VAULT_PATH, f"{concept}.md")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry     = f"\n## Q: {question}\n*Source: {source} — {timestamp}*\n\n{answer}\n"

    if os.path.exists(filepath):
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(entry)
    else:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {concept.replace('-', ' ').title()}\n{entry}")

    try:
        with open(filepath, encoding="utf-8") as fh:
            tags = _extract_frontmatter_tags(fh.read())
    except OSError:
        tags = []

    meta = {"source": filepath}
    meta.update(_tags_to_metadata(tags))
    db.add_documents([Document(page_content=f"Q: {question}\n\n{answer}", metadata=meta)])


# ── Prompts ───────────────────────────────────────────────────────────────────

def _format_history(history: list[dict]) -> str:
    recent = history[-(HISTORY_WINDOW * 2):]
    lines  = []
    for msg in recent:
        role    = "User" if msg["role"] == "user" else "Assistant"
        content = msg["content"][:600] + ("…" if len(msg["content"]) > 600 else "")
        lines.append(f"{role}: {content}")
    return "\n\n".join(lines)


def build_vault_prompt(question: str, chunks: list, history: list[dict]) -> str:
    parts = [
        "You are a helpful assistant with access to the user's personal notes.",
        "Use the context and conversation history to answer the question.",
        "If the answer isn't covered in the context, say so clearly.",
        "",
    ]
    if history:
        parts += ["--- CONVERSATION HISTORY ---", _format_history(history), "--- END HISTORY ---", ""]
    parts += [
        "--- CONTEXT FROM NOTES ---",
        "\n\n---\n\n".join(c.page_content for c in chunks),
        "--- END CONTEXT ---",
        "",
        f"Question: {question}",
        "Answer:",
    ]
    return "\n".join(parts)


def build_knowledge_prompt(question: str, history: list[dict]) -> str:
    parts = [
        "Answer the following question using your own knowledge.",
        'If you are not confident, start with: "I\'m not certain, but"',
        "",
    ]
    if history:
        parts += ["--- CONVERSATION HISTORY ---", _format_history(history), "--- END HISTORY ---", ""]
    parts += [f"Question: {question}", "Answer:"]
    return "\n".join(parts)


def build_web_prompt(question: str, web_context: str, history: list[dict]) -> str:
    parts = [
        "Answer the following question using the web search results below.",
        "Summarise the relevant information clearly and cite sources where helpful.",
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


# ── Shared CSS ────────────────────────────────────────────────────────────────

_CSS = """
Screen { background: #1e1e1e; }
Header { background: #252526; color: #cccccc; }
Footer { background: #252526; color: #6c6c6c; }

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

Input:focus { border: tall #5f87af; }
"""


# ── Note Review Modal ─────────────────────────────────────────────────────────

class NoteReviewScreen(ModalScreen[list[tuple[str, PendingNote]]]):
    """Walk through pending notes one at a time: preview, rename, save or skip."""

    CSS = """
    NoteReviewScreen { align: center middle; }

    #review-box {
        width: 86; height: 36;
        border: thick #5f87af;
        background: #252526;
        padding: 1 2;
    }
    #review-header { color: #cccccc; margin-bottom: 1; }
    #preview-log {
        height: 18;
        background: #1e1e1e;
        border: solid #454545;
        padding: 0 1;
        margin-bottom: 1;
        scrollbar-color: #454545;
        scrollbar-background: #1e1e1e;
    }
    #review-suggestion { color: #d4d4d4; margin-bottom: 1; }
    #review-input { margin: 0 0 1 0; background: #1e1e1e; color: #d4d4d4; border: tall #454545; }
    #review-input:focus { border: tall #5f87af; }
    #review-help { color: #6c6c6c; }
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
            yield Label("[dim]Enter=save  ·  skip=skip  ·  Esc=finish[/dim]", id="review-help")

    def on_mount(self) -> None:
        self._refresh()
        self.query_one("#review-input", Input).focus()

    def _refresh(self) -> None:
        note = self._pending[self._idx]
        self.query_one("#review-header", Label).update(
            f"[bold]Review notes  {self._idx + 1} / {len(self._pending)}[/bold]"
        )
        log = self.query_one("#preview-log", RichLog)
        log.clear()
        log.write(Markdown(f"**Q:** {note.question}\n\n*Source: {note.source}*\n\n{note.answer}"))
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
            concept = re.sub(r"\s+", "-", re.sub(r"[^a-z0-9\s-]", "", raw.lower()).strip()) if raw else note.suggestion
            self._confirmed.append((concept or note.suggestion, note))
        self._idx += 1
        if self._idx >= len(self._pending):
            self.dismiss(self._confirmed)
        else:
            self._refresh()

    def action_finish(self) -> None:
        self.dismiss(self._confirmed)


# ── Chat App ──────────────────────────────────────────────────────────────────

_HELP_TEXT = """\
[bold]Available commands[/bold]

  [bold #5f87af]/help[/bold #5f87af]         show this message
  [bold #5f87af]/ingest[/bold #5f87af]       rebuild the vector database from vault files
  [bold #5f87af]/organize[/bold #5f87af]     add YAML tags and wikilinks to vault notes
  [bold #5f87af]/savefile[/bold #5f87af]     review and save pending notes to the vault
  [bold #5f87af]/clear[/bold #5f87af]        reset conversation history
  [bold #5f87af]/web[/bold #5f87af]          toggle web search fallback on / off

[dim]Ctrl+S  shortcut for /savefile  ·  Ctrl+Q  quit[/dim]\
"""


class ChatApp(App[None]):
    TITLE     = "ChatUI"
    SUB_TITLE = CHAT_MODEL

    CSS = _CSS

    BINDINGS = [
        Binding("ctrl+q", "quit",         "Quit"),
        Binding("ctrl+s", "savefile",     "Save notes"),
        Binding("escape", "clear_input",  "Clear input", show=False),
    ]

    def __init__(self, db: Chroma | None) -> None:
        super().__init__()
        self.db              = db
        self._busy           = False
        self._history:  list[dict]        = []
        self._pending:  list[PendingNote] = []
        self._web_on         = True
        self._organize_queue: asyncio.Queue[str] | None = None
        self._session_file:   str | None = None

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(id="log", markup=True, wrap=True, highlight=False)
        yield Input(placeholder="Ask anything, or type /help for commands...", id="input")
        yield Footer()

    def on_mount(self) -> None:
        os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._session_file = os.path.join(CONVERSATIONS_DIR, f"{ts}.md")
        with open(self._session_file, "w", encoding="utf-8") as f:
            f.write(f"# Chat Session — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        if self.db is None:
            self._log("[yellow]No vault database found. Run [bold]/ingest[/bold] to build it.[/yellow]\n")
        else:
            self._log("[dim]Vault loaded. Ask anything, or type /help for commands.[/dim]\n")

        self.query_one(Input).focus()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _log(self, markup: str) -> None:
        self.query_one(RichLog).write(Text.from_markup(markup))

    def _queue_note(self, question: str, answer: str, source: str, suggestion: str) -> None:
        self._pending.append(PendingNote(question, answer, source, suggestion))
        n = len(self._pending)
        self.sub_title = f"{CHAT_MODEL}  ·  {n} unsaved note{'s' if n != 1 else ''}"

    def _append_to_session(self, role: str, content: str) -> None:
        if not self._session_file:
            return
        ts    = datetime.now().strftime("%H:%M")
        label = "User" if role == "user" else "Assistant"
        with open(self._session_file, "a", encoding="utf-8") as f:
            f.write(f"## [{ts}] {label}\n\n{content}\n\n")

    # ── Input routing ─────────────────────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.value = ""

        # Organize mode: pipe everything to the organize worker's queue
        if self._organize_queue is not None:
            self._organize_queue.put_nowait(text)
            return

        if not text or self._busy:
            return

        if text.startswith("/"):
            self._dispatch_command(text)
        else:
            self._busy = True
            self._log(f"\n[bold #ce9178]> {text}[/bold #ce9178]")
            self._append_to_session("user", text)
            self._process(text)

    # ── Command dispatcher ────────────────────────────────────────────────────

    def _dispatch_command(self, text: str) -> None:
        parts = text[1:].split(maxsplit=1)
        cmd   = parts[0].lower() if parts else ""
        args  = parts[1] if len(parts) > 1 else ""
        self._append_to_session("user", text)

        handlers = {
            "help":     lambda _: self._cmd_help(),
            "ingest":   self._cmd_ingest,
            "organize": self._cmd_organize,
            "savefile": lambda _: self.action_savefile(),
            "clear":    lambda _: self._cmd_clear(),
            "web":      self._cmd_web,
        }

        if cmd in handlers:
            handlers[cmd](args)
        else:
            self._log(f"[red]Unknown command: /{cmd}[/red]  — type /help for the list.")

    def _cmd_help(self) -> None:
        self._log(_HELP_TEXT)

    def _cmd_clear(self) -> None:
        self._history.clear()
        self._log("[dim]Conversation history cleared.[/dim]")

    def _cmd_web(self, args: str) -> None:
        if args.lower() in ("on", "off"):
            self._web_on = args.lower() == "on"
        else:
            self._web_on = not self._web_on
        state = "[green]on[/green]" if self._web_on else "[red]off[/red]"
        self._log(f"[dim]Web search fallback: {state}[/dim]")

    # ── /ingest command ───────────────────────────────────────────────────────

    @work
    async def _cmd_ingest(self, _args: str = "") -> None:
        self._busy = True
        self._log("[dim]📚 Ingesting vault…[/dim]")
        try:
            new_db   = await asyncio.to_thread(ingest_vault)
            self.db  = new_db
            n        = new_db._collection.count()
            self._log(f"[dim]✅ Ingested {n} chunks. Vault database updated.[/dim]")
        except Exception as e:
            self._log(f"[red]Ingest failed: {e}[/red]")
        finally:
            self._busy = False
            self.query_one(Input).focus()

    # ── /organize command (inline, was OrganizeApp) ───────────────────────────

    @work
    async def _cmd_organize(self, _args: str = "") -> None:
        self._organize_queue = asyncio.Queue()
        inp = self.query_one(Input)
        inp.placeholder = "Enter to accept  ·  skip to skip  ·  type to override…"

        try:
            await self._run_organize()
        finally:
            self._organize_queue = None
            inp.placeholder = "Ask anything, or type /help for commands..."
            self.query_one(Input).focus()

    async def _org_prompt(self, hint: str = "") -> str:
        if hint:
            self._log(f"[dim]{hint}[/dim]")
        return await self._organize_queue.get()  # type: ignore[union-attr]

    async def _run_organize(self) -> None:
        md_files = sorted(glob.glob(os.path.join(VAULT_PATH, "*.md")))
        if not md_files:
            self._log("[red]No .md files found in vault root.[/red]")
            return

        notes: dict[str, dict] = {}
        for path in md_files:
            stem = os.path.splitext(os.path.basename(path))[0]
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
            h1 = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            notes[stem] = {"path": path, "title": h1.group(1).strip() if h1 else stem, "content": content}

        self._log(f"[bold]Organising {len(notes)} notes…[/bold]\n")

        # ── Pass 1: YAML frontmatter tags ─────────────────────────────────────

        note_list_str = "\n".join(
            f"- {s} ({d['title']}): {d['content'][:300].strip()}" for s, d in notes.items()
        )
        tag_prompt = (
            "You are organising a personal knowledge vault.\n"
            "Suggest 1-3 lowercase tags for each note. Use the same tags across related notes.\n"
            "Reply in this exact format, one note per line:\nstem: tag1, tag2\n\nNotes:\n"
            f"{note_list_str}\n\nTags:"
        )
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
            if data["content"].lstrip().startswith("---"):
                self._log(f"[dim]⏭  {stem}.md — already has frontmatter[/dim]")
                continue
            suggested = tag_map.get(stem)
            if not suggested:
                continue

            self._log(f"\n[bold #5f87af]{stem}.md[/bold #5f87af]")
            self._log(f"  Suggested tags: [bold]{', '.join(suggested)}[/bold]")

            raw = await self._org_prompt("  Enter=accept  ·  skip=skip  ·  comma list=override:")
            if raw.lower() == "skip":
                continue

            final       = [t.strip() for t in raw.split(",")] if raw else suggested
            frontmatter = "---\ntags:\n" + "".join(f"  - {t}\n" for t in final) + "---\n"
            new_content = frontmatter + data["content"]

            with open(data["path"], "w", encoding="utf-8") as f:
                f.write(new_content)
            notes[stem]["content"] = new_content
            self._log("  [green]✓ Tags written.[/green]")

        # ── Pass 2: Wikilinks ─────────────────────────────────────────────────

        self._log("\n[bold]Scanning for wikilink opportunities…[/bold]")

        for stem, data in notes.items():
            content     = data["content"]
            other_notes = {s: d["title"] for s, d in notes.items() if s != stem}
            if not other_notes:
                continue

            link_prompt = (
                "You are editing a markdown note to add Obsidian [[wikilinks]].\n"
                f"Available notes:\n{chr(10).join(f'  {s}: {t}' for s, t in other_notes.items())}\n\n"
                "Find phrases in the note BODY that clearly refer to one of the above notes.\n"
                "Only the FIRST occurrence. Nothing inside --- frontmatter or existing [[...]].\n"
                'Reply one per line as: "exact phrase" -> target_stem  — or reply "none".\n\n'
                f"Note:\n{content}\n\nSuggestions:"
            )
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

            raw = await self._org_prompt("  Enter=accept  ·  skip=skip:")
            if raw.lower() == "skip":
                continue

            fm_end   = (content.find("---", content.index("---") + 3) + 3) if content.lstrip().startswith("---") else 0
            fm_block = content[:fm_end]
            body     = content[fm_end:]

            for phrase, target in subs:
                title_t = notes[target]["title"]
                link    = f"[[{target}]]" if phrase.lower() in (target.lower(), title_t.lower()) else f"[[{target}|{phrase}]]"
                body    = body.replace(phrase, link, 1)

            new_content = fm_block + body
            if new_content != content:
                with open(data["path"], "w", encoding="utf-8") as f:
                    f.write(new_content)
                notes[stem]["content"] = new_content
                self._log("  [green]✓ Links added.[/green]")

        self._log("\n[bold green]✓ Vault organisation complete.[/bold green]")

    # ── /savefile command + Ctrl+S ────────────────────────────────────────────

    def action_savefile(self) -> None:
        if not self._pending:
            self._log("[dim]No pending notes to review.[/dim]")
            return
        self.push_screen(NoteReviewScreen(list(self._pending)), callback=self._after_review)

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
            await asyncio.to_thread(lambda: save_to_vault(c, n.question, n.answer, n.source, self.db))
        self._log(f"[dim]📝  {len(confirmed)} note{'s' if len(confirmed) != 1 else ''} saved.[/dim]")

    # ── RAG chat worker ───────────────────────────────────────────────────────

    @work
    async def _process(self, question: str) -> None:
        log = self.query_one(RichLog)
        self._history.append({"role": "user", "content": question})

        try:
            if self.db is None:
                self._log("[red]No database — run /ingest first.[/red]")
                return

            # ── Vault retrieval with tag-aware second pass ─────────────────────
            results   = await asyncio.to_thread(
                lambda: self.db.similarity_search_with_relevance_scores(question, k=TOP_K)
            )
            chunks    = [doc for doc, _ in results]
            top_score = max((s for _, s in results), default=0.0)

            if results:
                active_tags = _get_chunk_tags(results[0][0])
                if active_tags:
                    filtered = await asyncio.to_thread(
                        lambda: self.db.similarity_search_with_relevance_scores(
                            question, k=TOP_K, filter=_make_tag_filter(active_tags)
                        )
                    )
                    filtered_top = max((s for _, s in filtered), default=0.0)
                    if filtered_top >= top_score * 0.9:
                        chunks    = [doc for doc, _ in filtered]
                        top_score = filtered_top
                        self._log(f"[dim]🏷  Scoped to: {', '.join(active_tags)}[/dim]")

            self._log(f"[dim]🔍  Best vault match: {top_score:.2f}[/dim]")

            if top_score >= SIMILARITY_THRESHOLD:
                self._log("[dim]📓  Source: vault notes[/dim]")
                answer = await asyncio.to_thread(
                    lambda: llm.invoke(build_vault_prompt(question, chunks, self._history[:-1])).content
                )
                self._history.append({"role": "assistant", "content": answer})
                self._append_to_session("assistant", answer)
                log.write(Markdown(answer))
                return

            # ── Model knowledge (always shown) ─────────────────────────────────
            self._log("[dim]🧠  Vault score too low — asking model[/dim]")
            model_answer = await asyncio.to_thread(
                lambda: llm.invoke(build_knowledge_prompt(question, self._history[:-1])).content
            )
            uncertain = model_answer.strip().lower().startswith("i'm not certain")
            self._log(f"[dim]🧠  Model knowledge{'  (uncertain)' if uncertain else ''}[/dim]")
            log.write(Markdown(model_answer))
            self._history.append({"role": "assistant", "content": model_answer})
            self._append_to_session("assistant", model_answer)

            suggestion = await asyncio.to_thread(lambda: get_concept_suggestion(question, model_answer))
            self._queue_note(question, model_answer, "model knowledge" + (" (uncertain)" if uncertain else ""), suggestion)

            # ── Web search supplement when uncertain ───────────────────────────
            if uncertain and self._web_on:
                self._log("[dim]🌐  Supplementing with web search…[/dim]")
                web_ctx = await asyncio.to_thread(lambda: web_search(question))

                if not web_ctx.startswith(("No results", "Web search failed", "duckduckgo")):
                    web_answer = await asyncio.to_thread(
                        lambda: llm.invoke(build_web_prompt(question, web_ctx, self._history)).content
                    )
                    self._log("[dim]🌐  Web result:[/dim]")
                    log.write(Markdown(web_answer))
                    web_suggestion = await asyncio.to_thread(lambda: get_concept_suggestion(question, web_answer))
                    self._queue_note(question, web_answer, "web search", web_suggestion)
                else:
                    self._log("[dim]🌐  No web results.[/dim]")

        finally:
            self._busy = False
            self.query_one(Input).focus()

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_clear_input(self) -> None:
        self.query_one(Input).value = ""

    def action_quit(self) -> None:
        self.exit()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ChatApp(load_existing_db()).run()
