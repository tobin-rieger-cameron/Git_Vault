"""
chatui.py — local RAG chat interface for your Obsidian vault.
All functions are available as /commands within the chat.

/help     list commands          /ingest   rebuild vector DB
/organize tag notes + wikilinks  /savefile review & save notes
/clear    reset history          /web      toggle web search
/browse   file browser           /update   detect config drift
/apply    apply /update patch    (yes/no confirmation before write)
"""

from __future__ import annotations

import asyncio
import difflib
import glob
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime

import yaml

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, RichLog, Static
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

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIG_DIR = os.path.join(_SCRIPT_DIR, "config")


def _load_config_file(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return {}
    m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    return yaml.safe_load(m.group(1)) or {} if m else {}


def _load_all_config() -> dict:
    cfg: dict = {}
    for name in ("settings", "models"):
        cfg.update(_load_config_file(os.path.join(_CONFIG_DIR, f"{name}.md")))
    return cfg


_cfg         = _load_all_config()
_startup_cfg = dict(_cfg)

VAULT_PATH        = _cfg.get("vault_path", _SCRIPT_DIR + "/")
DB_PATH           = os.path.join(VAULT_PATH, "local_db")
CONVERSATIONS_DIR = os.path.join(VAULT_PATH, "conversations")

EMBED_MODEL  = _cfg.get("embed_model",  "nomic-embed-text")
CHAT_MODEL   = _cfg.get("chat_model",   "llama3.2:3b")
CODING_MODEL = _cfg.get("coding_model", "llama3.1:8b")
FILE_GLOB    = "**/*.md"

TOP_K                = int(_cfg.get("top_k",                3))
WEB_SEARCH_RESULTS   = int(_cfg.get("web_search_results",   3))
CHUNK_SIZE           = int(_cfg.get("chunk_size",           500))
CHUNK_OVERLAP        = int(_cfg.get("chunk_overlap",        50))
SIMILARITY_THRESHOLD = float(_cfg.get("similarity_threshold", 0.5))
HISTORY_WINDOW       = int(_cfg.get("history_window",       4))

_SKIP_DIRS        = {"__pycache__", "local_db", "conversations", ".git", "config"}
_UNCERTAIN_PREFIX = "i'm not certain"


def _ensure_models() -> None:
    required = _cfg.get("models", [])
    if not required:
        return

    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    if result.returncode != 0:
        print("Warning: could not query ollama — skipping model check.", file=sys.stderr)
        return

    installed: set[str] = set()
    for line in result.stdout.splitlines()[1:]:
        cols = line.split()
        if cols:
            name = cols[0]
            installed.add(name)
            if name.endswith(":latest"):
                installed.add(name[: -len(":latest")])

    def _tagged(name: str) -> str:
        return name if ":" in name else f"{name}:latest"

    for model in required:
        if model not in installed and _tagged(model) not in installed:
            print(f"Pulling {model}…")
            subprocess.run(["ollama", "pull", model])


_ensure_models()

embeddings  = OllamaEmbeddings(model=EMBED_MODEL)
llm         = ChatOllama(model=CHAT_MODEL)
coding_llm  = ChatOllama(model=CODING_MODEL)

# Full-text snapshot of every config/*.md for /update change detection.
# Captured once at startup so diffs show exactly what the user changed this session.
_startup_config_texts: dict[str, str] = {}
for _p in sorted(glob.glob(os.path.join(_CONFIG_DIR, "*.md"))):
    try:
        with open(_p, encoding="utf-8") as _f:
            _startup_config_texts[_p] = _f.read()
    except OSError:
        pass


def _snip(src: str, start: str, stop: str) -> str:
    """Return the section of src from `start` to `stop`.
    Both markers are anchored to line starts so string literals that happen
    to contain the same text (mid-line, inside function calls) are skipped."""
    m = re.search(r'(?m)^' + re.escape(start), src)
    if not m:
        return ""
    a = m.start()
    m2 = re.search(r'(?m)^' + re.escape(stop), src[a + 1:])
    return src[a: a + 1 + m2.start()] if m2 else src[a:]


def _collect_config_diffs() -> dict[str, str]:
    """Return unified diffs for every config/*.md that changed since startup."""
    diffs: dict[str, str] = {}
    current_paths = set(glob.glob(os.path.join(_CONFIG_DIR, "*.md")))
    for path in sorted(current_paths | set(_startup_config_texts.keys())):
        try:
            with open(path, encoding="utf-8") as f:
                current = f.read()
        except OSError:
            current = ""
        baseline = _startup_config_texts.get(path, "")
        if current == baseline:
            continue
        rel  = os.path.relpath(path, _SCRIPT_DIR)
        diff = "".join(difflib.unified_diff(
            baseline.splitlines(keepends=True),
            current.splitlines(keepends=True),
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
        ))
        if diff:
            diffs[rel] = diff
    return diffs


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
    loader = DirectoryLoader(
        VAULT_PATH,
        glob=FILE_GLOB,
        exclude=["conversations/**", "config/**"],
    )
    docs = loader.load()
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

    try:
        return Chroma.from_documents(documents=chunks, embedding=embeddings, persist_directory=DB_PATH)
    except Exception as e:
        if "readonly" in str(e).lower():
            raise RuntimeError(
                "Database is locked by another process. "
                "Close any other running instance of chatui.py and try /ingest again."
            ) from e
        raise


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
class OpenFile:
    path:    str
    rel:     str
    content: str


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
    raw = coding_llm.invoke(prompt).content.strip().lower()
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


def _file_ctx_section(file_ctx: str) -> list[str]:
    return ["--- OPEN FILE ---", file_ctx, "--- END FILE ---", ""] if file_ctx else []


def build_vault_prompt(question: str, chunks: list, history: list[dict], file_ctx: str = "") -> str:
    parts = [
        "You are a helpful assistant with access to the user's personal notes.",
        "Use the context and conversation history to answer the question.",
        "If the answer isn't covered in the context, say so clearly.",
        "",
    ]
    parts += _file_ctx_section(file_ctx)
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


def build_knowledge_prompt(question: str, history: list[dict], file_ctx: str = "") -> str:
    parts = [
        "Answer the following question using your own knowledge.",
        f'If you are not confident, start with: "{_UNCERTAIN_PREFIX.capitalize()}, but"',
        "",
    ]
    parts += _file_ctx_section(file_ctx)
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

#stream {
    display: none;
    margin: 0 2;
    padding: 0 1;
    color: #d4d4d4;
}
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
        event.stop()
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


# ── File Browser Modal ────────────────────────────────────────────────────────

class FileBrowserScreen(ModalScreen[str | None]):
    """TUI file browser rooted at VAULT_PATH. Returns selected file path or None."""

    CSS = """
    FileBrowserScreen { align: center middle; }

    #browser-box {
        width: 80; height: 36;
        border: thick #5f87af;
        background: #252526;
        padding: 1 2;
    }
    #browser-path { color: #9cdcfe; margin-bottom: 1; }
    #browser-list {
        height: 28;
        background: #1e1e1e;
        border: solid #454545;
        scrollbar-color: #454545;
        scrollbar-background: #1e1e1e;
    }
    #browser-help { color: #6c6c6c; margin-top: 1; }
    """

    BINDINGS = [Binding("escape", "go_up_or_close", "Up/Close", show=False)]

    def __init__(self, root: str) -> None:
        super().__init__()
        self._root    = os.path.realpath(root)
        self._cwd     = self._root
        self._entries: list[tuple[bool, str, str]] = []  # (is_dir, name, full_path)

    def compose(self) -> ComposeResult:
        with Vertical(id="browser-box"):
            yield Label("", id="browser-path")
            yield ListView(id="browser-list")
            yield Label("[dim]↑↓ navigate  ·  Enter=open/select  ·  Esc=up/close[/dim]", id="browser-help")

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        lv  = self.query_one("#browser-list", ListView)
        lv.clear()

        rel = os.path.relpath(self._cwd, self._root)
        display = "./" if rel == "." else f"./{rel}/"
        self.query_one("#browser-path", Label).update(f"[bold]📁  {display}[/bold]")

        self._entries = []
        try:
            names = sorted(os.listdir(self._cwd), key=str.lower)
        except PermissionError:
            names = []

        dirs, files = [], []
        for name in names:
            if name.startswith(".") or name in _SKIP_DIRS:
                continue
            full = os.path.join(self._cwd, name)
            if os.path.isdir(full):
                dirs.append((True, name, full))
            else:
                files.append((False, name, full))

        self._entries = dirs + files
        for is_dir, name, _ in self._entries:
            icon = "📁" if is_dir else _file_icon(name)
            lv.append(ListItem(Label(f"{icon}  {name}")))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx is None or idx >= len(self._entries):
            return
        is_dir, _name, full = self._entries[idx]
        if is_dir:
            self._cwd = full
            self._refresh()
        else:
            self.dismiss(full)

    def action_go_up_or_close(self) -> None:
        if os.path.realpath(self._cwd) == self._root:
            self.dismiss(None)
        else:
            self._cwd = os.path.dirname(self._cwd)
            self._refresh()


def _file_icon(name: str) -> str:
    icons = {".md": "📝", ".py": "🐍", ".txt": "📄", ".json": "📋", ".yaml": "📋", ".yml": "📋"}
    return icons.get(os.path.splitext(name)[1].lower(), "📄")


# ── Help text ─────────────────────────────────────────────────────────────────

_HELP_TEXT = """\
[bold]Available commands[/bold]

  [bold #5f87af]/help[/bold #5f87af]         show this message
  [bold #5f87af]/browse[/bold #5f87af]       open file browser to load a file as context
  [bold #5f87af]/ingest[/bold #5f87af]       rebuild the vector database from vault files
  [bold #5f87af]/organize[/bold #5f87af]     add YAML tags and wikilinks to vault notes
  [bold #5f87af]/savefile[/bold #5f87af]     review and save pending notes to the vault
  [bold #5f87af]/clear[/bold #5f87af]        reset conversation history and open file
  [bold #5f87af]/web[/bold #5f87af]          toggle web search fallback on / off
  [bold #5f87af]/update[/bold #5f87af]       detect config drift and propose code patches
  [bold #5f87af]/apply[/bold #5f87af]        apply the diff proposed by /update (asks yes/no first)

[dim]Ctrl+S  /savefile  ·  Ctrl+B  /browse  ·  Ctrl+Q  quit[/dim]\
"""


# ── Chat App ──────────────────────────────────────────────────────────────────

class ChatApp(App[None]):
    TITLE     = "ChatUI"
    SUB_TITLE = CHAT_MODEL

    CSS = _CSS

    BINDINGS = [
        Binding("ctrl+q", "quit",        "Quit"),
        Binding("ctrl+s", "savefile",     "Save notes"),
        Binding("ctrl+b", "browse",      "Browse files"),
        Binding("escape", "clear_input", "Clear input", show=False),
    ]

    def __init__(self, db: Chroma | None) -> None:
        super().__init__()
        self.db              = db
        self._busy           = False
        self._history:  list[dict]        = []
        self._pending:  list[PendingNote] = []
        self._web_on         = True
        self._organize_queue: asyncio.Queue[str] | None = None
        self._apply_queue:    asyncio.Queue[str] | None = None
        self._pending_patch:  str | None = None
        self._session_file:   str | None = None
        self._open_file:      OpenFile | None = None

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(id="log", markup=True, wrap=True, highlight=False)
        yield Static("", id="stream")
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

    def _log_md(self, text: str) -> None:
        self.query_one(RichLog).write(Markdown(text))

    def _update_subtitle(self) -> None:
        parts = [CHAT_MODEL]
        if self._pending:
            n = len(self._pending)
            parts.append(f"{n} unsaved note{'s' if n != 1 else ''}")
        if self._open_file:
            parts.append(f"📄 {self._open_file.rel}")
        self.sub_title = "  ·  ".join(parts)

    def _queue_note(self, question: str, answer: str, source: str, suggestion: str) -> None:
        self._pending.append(PendingNote(question, answer, source, suggestion))
        self._update_subtitle()

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

        if self._organize_queue is not None:
            self._organize_queue.put_nowait(text)
            return

        if self._apply_queue is not None:
            self._apply_queue.put_nowait(text)
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
            "browse":   lambda _: self.action_browse(),
            "ingest":   self._cmd_ingest,
            "organize": self._cmd_organize,
            "savefile": lambda _: self.action_savefile(),
            "clear":    lambda _: self._cmd_clear(),
            "web":      self._cmd_web,
            "update":   self._cmd_update,
            "apply":    self._cmd_apply,
        }

        if cmd in handlers:
            handlers[cmd](args)
        else:
            self._log(f"[red]Unknown command: /{cmd}[/red]  — type /help for the list.")

    def _cmd_help(self) -> None:
        self._log(_HELP_TEXT)

    def _cmd_clear(self) -> None:
        self._history.clear()
        self._open_file = None
        self._update_subtitle()
        self._log("[dim]Conversation history and open file cleared.[/dim]")

    def _cmd_web(self, args: str) -> None:
        if args.lower() in ("on", "off"):
            self._web_on = args.lower() == "on"
        else:
            self._web_on = not self._web_on
        state = "[green]on[/green]" if self._web_on else "[red]off[/red]"
        self._log(f"[dim]Web search fallback: {state}[/dim]")

    # ── /update command ───────────────────────────────────────────────────────

    @work
    async def _cmd_update(self, _args: str = "") -> None:
        self._log("[bold]🔄  Scanning config/ for changes…[/bold]")

        # ── Frontmatter drift: quick human-readable summary ───────────────────
        live_cfg = _load_all_config()
        all_keys = set(_startup_cfg) | set(live_cfg)
        drift    = {k: (_startup_cfg.get(k), live_cfg.get(k))
                    for k in all_keys if _startup_cfg.get(k) != live_cfg.get(k)}
        if drift:
            self._log("[yellow]Setting / model changes (restart to apply):[/yellow]")
            for key, (old, new) in sorted(drift.items()):
                if old is None:
                    self._log(f"  [green]+[/green] {key}: {new}")
                elif new is None:
                    self._log(f"  [red]-[/red] {key}: {old}")
                else:
                    self._log(f"  [yellow]~[/yellow] {key}: {old!r} → {new!r}")

        # ── Full-text diff of all config/*.md files ───────────────────────────
        config_diffs = await asyncio.to_thread(_collect_config_diffs)

        if not config_diffs:
            self._log("[dim]  No config changes detected.[/dim]")
            return

        for rel in sorted(config_diffs):
            n = sum(1 for ln in config_diffs[rel].splitlines()
                    if ln.startswith(("+", "-")) and not ln.startswith(("+++", "---")))
            self._log(f"[dim]  📝 {rel}  ({n} changed lines)[/dim]")

        await self._propose_changes_from_config_diffs(config_diffs)

    async def _propose_changes_from_config_diffs(
        self, config_diffs: dict[str, str]
    ) -> None:
        try:
            with open(os.path.abspath(__file__), encoding="utf-8") as f:
                source = f.read()
        except OSError as e:
            self._log(f"[red]Could not read chatui.py: {e}[/red]")
            return

        ctx = "\n\n# ...\n\n".join(filter(None, [
            _snip(source, "_HELP_TEXT = ",          "# ── Chat App"),
            _snip(source, "    def _dispatch_command(", "    def _cmd_help("),
            _snip(source, "    def _cmd_clear(", "    # ── /update command"),
            _snip(source, "class FileBrowserScreen(", "def _file_icon("),
            _snip(source, "    def action_browse(self) -> None", "    # ── /ingest command ─"),
        ]))

        all_diffs = "\n\n".join(
            f"=== {rel} ===\n{diff}" for rel, diff in sorted(config_diffs.items())
        )

        prompt = "\n".join([
            "You are reviewing config file changes for chatui.py (a Python Textual TUI).",
            "Analyse what changed and propose any corresponding code modifications.",
            "",
            "CONFIG FILE CHANGES (unified diff format):",
            all_diffs,
            "",
            "When reviewing, consider:",
            "  - Lines beginning with 'CHANGE:' are explicit feature requests —",
            "    read the surrounding section to understand the feature, then implement it",
            "    using the relevant chatui.py code shown below.",
            "  - New/removed entries in commands.md → add/remove handler in _dispatch_command,",
            "    add _cmd_<name> method with self._log placeholder, update _HELP_TEXT",
            "  - Changed setting descriptions or defaults → update code defaults or logic",
            "  - New features described in markdown prose → implement or add a stub",
            "  - Wording, formatting, or documentation-only changes → no code change needed",
            "",
            'If no code changes are required, reply with exactly: "No code changes required."',
            "Otherwise reply with ONLY a unified diff (diff -u format). No explanation. No markdown fences.",
            "",
            "RELEVANT chatui.py SECTIONS:",
            ctx,
            "\nResponse:",
        ])

        self._log(f"\n[dim]🤖  Asking {CODING_MODEL} to analyse changes…[/dim]")
        patch = await self._stream_llm(prompt, model=coding_llm)

        if patch.strip().lower().startswith(("no code changes", "no changes")):
            self._log("[dim]  No code changes suggested.[/dim]")
            return

        if patch.strip():
            self._pending_patch = patch
            self._log(
                "\n[dim]Review the diff above, then run "
                "[bold]/apply[/bold] to write it — or edit chatui.py manually.[/dim]"
            )

    # ── /apply command ────────────────────────────────────────────────────────

    @work
    async def _cmd_apply(self, _args: str = "") -> None:
        if not self._pending_patch:
            self._log("[dim]No pending patch — run /update first.[/dim]")
            return

        self._log("[bold yellow]⚠  Apply pending patch to chatui.py?[/bold yellow]")
        self._log("[dim]Type [bold]yes[/bold] to apply, anything else to cancel.[/dim]")

        inp = self.query_one(Input)
        inp.placeholder = "yes / no…"
        self._apply_queue = asyncio.Queue()
        try:
            resp = (await self._apply_queue.get()).strip().lower()
        finally:
            self._apply_queue = None
            inp.placeholder = "Ask anything, or type /help for commands..."

        if resp != "yes":
            self._log("[dim]Cancelled.[/dim]")
            return

        script_dir = os.path.dirname(os.path.abspath(__file__))
        patch_data = self._pending_patch

        def _run_patch(p_level: int, dry_run: bool) -> subprocess.CompletedProcess:
            args = ["patch", f"-p{p_level}"]
            if dry_run:
                args.append("--dry-run")
            return subprocess.run(
                args, input=patch_data, capture_output=True, text=True, cwd=script_dir
            )

        # Try dry-run at -p1 (git-style headers) then -p0 (bare filename headers)
        chosen = None
        result = None
        for level in (1, 0):
            result = await asyncio.to_thread(_run_patch, level, True)
            if result.returncode == 0:
                chosen = level
                break

        if chosen is None:
            self._log("[red]✗  Patch cannot be applied cleanly:[/red]")
            if result:
                self._log(f"[dim]{(result.stdout + result.stderr).strip()}[/dim]")
            self._log("[dim]Edit chatui.py manually using the diff shown above.[/dim]")
            return

        result = await asyncio.to_thread(_run_patch, chosen, False)
        if result.returncode == 0:
            self._log("[green]✓  Patch applied successfully.[/green]")
            self._log("[dim]Quit and restart chatui.py to load the changes.[/dim]")
            self._pending_patch = None
        else:
            self._log(f"[red]✗  patch failed:[/red] {(result.stdout + result.stderr).strip()}")

    # ── /browse command + Ctrl+B ──────────────────────────────────────────────

    def action_browse(self) -> None:
        self.push_screen(FileBrowserScreen(VAULT_PATH), callback=self._after_browse)

    @work
    async def _after_browse(self, path: str | None) -> None:
        if path is None:
            return
        rel = os.path.relpath(path, VAULT_PATH)
        try:
            def _read() -> str:
                with open(path, encoding="utf-8") as f:
                    return f.read()
            content = await asyncio.to_thread(_read)
            self._open_file = OpenFile(path=path, rel=rel, content=content)
            self._update_subtitle()
            self._log(f"[dim]📄  Loaded: [bold]{rel}[/bold] — ask anything about it[/dim]")
        except (OSError, UnicodeDecodeError) as e:
            self._log(f"[red]Could not read {rel}: {e}[/red]")

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

    # ── /organize command ─────────────────────────────────────────────────────

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
        raw_tags = await asyncio.to_thread(lambda: coding_llm.invoke(tag_prompt).content.strip())

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
            raw = await asyncio.to_thread(lambda: coding_llm.invoke(link_prompt).content.strip())
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

    # ── /savemd command + Ctrl+S ──────────────────────────────────────────────

    def action_savefile(self) -> None:
        if not self._pending:
            self._log("[dim]No pending notes to review.[/dim]")
            return
        self.push_screen(NoteReviewScreen(list(self._pending)), callback=self._after_review)

    def _after_review(self, confirmed: list[tuple[str, PendingNote]]) -> None:
        self._pending.clear()
        self._update_subtitle()
        if confirmed:
            self._save_confirmed(confirmed)
        else:
            self._log("[dim]No notes saved.[/dim]")

    @work
    async def _save_confirmed(self, confirmed: list[tuple[str, PendingNote]]) -> None:
        await asyncio.gather(*[
            asyncio.to_thread(save_to_vault, concept, note.question, note.answer, note.source, self.db)
            for concept, note in confirmed
        ])
        self._log(f"[dim]📝  {len(confirmed)} note{'s' if len(confirmed) != 1 else ''} saved.[/dim]")

    # ── Streaming LLM helper ──────────────────────────────────────────────────

    async def _stream_llm(self, prompt: str, *, model: ChatOllama | None = None) -> str:
        m = model if model is not None else llm
        stream_widget = self.query_one("#stream", Static)
        stream_widget.display = True
        parts: list[str] = []
        try:
            async for chunk in m.astream(prompt):
                parts.append(chunk.content)
                stream_widget.update(Text("".join(parts)))
        finally:
            stream_widget.display = False
        accumulated = "".join(parts)
        if accumulated:
            self._log_md(accumulated)
        return accumulated

    # ── RAG chat worker ───────────────────────────────────────────────────────

    @work
    async def _process(self, question: str) -> None:
        self._history.append({"role": "user", "content": question})

        file_ctx = ""
        if self._open_file:
            file_ctx = f"File: {self._open_file.rel}\n\n{self._open_file.content}"
            self._log(f"[dim]📄  Context: {self._open_file.rel}[/dim]")

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
                answer = await self._stream_llm(build_vault_prompt(question, chunks, self._history[:-1], file_ctx))
                self._history.append({"role": "assistant", "content": answer})
                self._append_to_session("assistant", answer)
                return

            # ── Model knowledge (always shown) ─────────────────────────────────
            self._log("[dim]🧠  Vault score too low — asking model[/dim]")
            model_answer = await self._stream_llm(build_knowledge_prompt(question, self._history[:-1], file_ctx))
            uncertain = model_answer.strip().lower().startswith(_UNCERTAIN_PREFIX)
            self._log(f"[dim]🧠  Model knowledge{'  (uncertain)' if uncertain else ''}[/dim]")
            self._history.append({"role": "assistant", "content": model_answer})
            self._append_to_session("assistant", model_answer)

            suggestion = await asyncio.to_thread(lambda: get_concept_suggestion(question, model_answer))
            self._queue_note(question, model_answer, "model knowledge" + (" (uncertain)" if uncertain else ""), suggestion)

            # ── Web search supplement when uncertain ───────────────────────────
            if uncertain and self._web_on:
                self._log("[dim]🌐  Supplementing with web search…[/dim]")
                web_ctx = await asyncio.to_thread(lambda: web_search(question))

                if not web_ctx.startswith(("No results", "Web search failed", "duckduckgo")):
                    self._log("[dim]🌐  Web result:[/dim]")
                    web_answer = await self._stream_llm(build_web_prompt(question, web_ctx, self._history))
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
