"""
chatui.py — local RAG chat interface for your Obsidian vault.
All functions are available as /commands within the chat.

/help     list commands          /ingest   rebuild vector DB
/organize tag notes + wikilinks  /savefile review & save notes
/clear    reset history          /web      toggle web search
/browse   file browser           /update   apply directives from config/
/apply    write proposed source   (yes/no, atomic write + git sync hash)
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


_cfg = _load_all_config()

VAULT_PATH        = _cfg.get("vault_path", _SCRIPT_DIR + "/")
DB_PATH           = os.path.join(VAULT_PATH, "local_db")
CONVERSATIONS_DIR = os.path.join(VAULT_PATH, "conversations")

EMBED_MODEL  = _cfg.get("embed_model",  "nomic-embed-text")
CHAT_MODEL   = _cfg.get("chat_model",   "llama3.2:3b")
CODING_MODEL = _cfg.get("coding_model", "qwen2.5-coder:7b")
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



def _snip(src: str, start: str, stop: str) -> str:
    """Return the section of src from `start` to `stop`, prefixed with real line numbers.
    Both markers are anchored to line starts so string literals that happen
    to contain the same text (mid-line, inside function calls) are skipped.
    Line numbers let the coding model write accurate hunk headers."""
    m = re.search(r'(?m)^' + re.escape(start), src)
    if not m:
        return ""
    a = m.start()
    m2 = re.search(r'(?m)^' + re.escape(stop), src[a + 1:])
    section = src[a: a + 1 + m2.start()] if m2 else src[a:]
    first_line = src[:a].count("\n") + 1
    return "".join(
        f"{first_line + i:5d} {line}"
        for i, line in enumerate(section.splitlines(keepends=True))
    )


def _build_chatui_guide(src: str) -> str:
    """Parse chatui.py with the AST and return a structural guide for the coding model.

    The guide tells the model exactly WHERE to insert each type of change so it
    can write accurate diffs without guessing line numbers.
    """
    import ast as _ast

    try:
        tree = _ast.parse(src)
    except SyntaxError:
        return "(could not parse chatui.py)"

    lines = src.splitlines()

    # ── collect classes and their methods ──────────────────────────────────────
    classes: dict[str, dict] = {}
    for node in _ast.walk(tree):
        if isinstance(node, _ast.ClassDef):
            methods = {}
            for child in _ast.walk(node):
                if isinstance(child, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                    if child.col_offset > node.col_offset:
                        methods[child.name] = child.lineno
            classes[node.name] = {"line": node.lineno, "methods": methods}

    # ── find key landmarks via line-anchored regex (avoids matching string literals) ──
    def _line_of(pattern: str) -> int:
        m = re.search(r'(?m)^' + re.escape(pattern), src)
        return src[:m.start()].count("\n") + 1 if m else 0

    def _pos_of(pattern: str) -> int:
        m = re.search(r'(?m)^' + re.escape(pattern), src)
        return m.start() if m else -1

    # _HELP_TEXT bounds
    _ht_open = "_HELP_TEXT = " + '"""'   # split to avoid self-match as a literal
    ht_pos   = _pos_of(_ht_open)
    help_start = src[:ht_pos].count("\n") + 1 if ht_pos >= 0 else 0
    if ht_pos >= 0:
        _ht_close_m = re.search(r'(?m)^"""', src[ht_pos + len(_ht_open):])
        help_end = (src[:ht_pos + len(_ht_open) + _ht_close_m.start()].count("\n") + 1
                    if _ht_close_m else 0)
    else:
        help_end = 0

    # handlers dict bounds — 8 spaces indent (inside _dispatch_command)
    _hd_marker = "        handlers = {"
    handlers_m = re.search(r'(?m)^' + re.escape(_hd_marker), src)
    if handlers_m:
        h_start  = src[:handlers_m.start()].count("\n") + 1
        h_block  = src[handlers_m.start():]
        h_close  = h_block.find("\n        }")
        h_end    = h_start + h_block[:h_close].count("\n") + 1
        last_handler_line = h_end - 1
    else:
        h_start = h_end = last_handler_line = 0

    chatapp      = classes.get("ChatApp", {})
    chatapp_line = chatapp.get("line", 0)
    chatapp_methods = chatapp.get("methods", {})

    # Find a good method insertion point: after _cmd_web, before _cmd_update
    cmd_web_line    = chatapp_methods.get("_cmd_web", 0)
    cmd_update_line = chatapp_methods.get("_cmd_update", 0)
    method_insert   = cmd_update_line - 1 if cmd_update_line else (cmd_web_line + 8)

    filebrowser   = classes.get("FileBrowserScreen", {})
    fb_line       = filebrowser.get("line", 0)
    fb_methods    = filebrowser.get("methods", {})

    # ── format the guide ───────────────────────────────────────────────────────
    parts = [
        "=== chatui.py STRUCTURAL GUIDE ===",
        "",
        f"Total lines: {len(lines)}",
        "",
        "## Key classes",
        f"  ChatApp (line {chatapp_line})          — main TUI class; all /commands live here",
        f"  FileBrowserScreen (line {fb_line})     — modal screen for file/folder selection",
        "",
        "## _HELP_TEXT",
        f"  Defined at line {help_start}, closing \"\"\" at line {help_end}.",
        f"  To add a help entry, insert a new line BEFORE line {help_end}.",
        f"  Format:   [bold #5f87af]/<cmd>[/bold #5f87af]       one-line description",
        "",
        "## handlers dict (inside ChatApp._dispatch_command)",
        f"  Dict literal: lines {h_start}–{h_end}.",
        f"  Last entry is at line {last_handler_line}.",
        f"  To add a new command, insert BEFORE line {h_end} (the closing brace).",
        f"  Format:   \"<name>\": lambda _: self._cmd_<name>(),",
        "",
        "## ChatApp methods",
    ]
    for name, ln in sorted(chatapp_methods.items(), key=lambda x: x[1]):
        parts.append(f"  line {ln:4d}  def {name}()")
    parts += [
        "",
        f"  ↳ INSERT NEW _cmd_* METHODS at line {method_insert}",
        f"    (after _cmd_web at line {cmd_web_line}, before _cmd_update at line {cmd_update_line})",
        "    Pattern to follow: see _cmd_clear / _cmd_web above for style",
        "",
        "## FileBrowserScreen methods",
    ]
    for name, ln in sorted(fb_methods.items(), key=lambda x: x[1]):
        parts.append(f"  line {ln:4d}  def {name}()")
    parts += [
        "",
        "## Module-level variables (add new ones near top of file, before _HELP_TEXT)",
        f"  _HELP_TEXT starts at line {help_start}; insert module vars before this.",
        "",
        "=== END GUIDE ===",
    ]
    return "\n".join(parts)


# ── Sync-hash management ──────────────────────────────────────────────────────

_SYNC_FILE = os.path.join(_SCRIPT_DIR, ".chatui_sync")


def _get_sync_hash() -> str | None:
    try:
        with open(_SYNC_FILE) as f:
            h = f.read().strip()
            return h or None
    except OSError:
        return None


def _set_sync_hash(h: str) -> None:
    with open(_SYNC_FILE, "w") as f:
        f.write(h + "\n")


def _git_head_hash() -> str | None:
    r = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=_SCRIPT_DIR
    )
    return r.stdout.strip() if r.returncode == 0 else None


# ── Config diff via git ───────────────────────────────────────────────────────

_DIRECTIVE_PREFIXES = ("CHANGE:", "REMOVE:", "RENAME:", "FIX:")


def _collect_config_diffs_git() -> dict[str, str]:
    """Return per-file unified diffs for config/*.md using git.

    Priority: sync-hash → HEAD (committed changes not yet applied)
    Fallback 1: HEAD → working tree (uncommitted edits)
    Fallback 2: HEAD~1 → HEAD (last commit, first run with no sync hash)
    """
    sync_hash = _get_sync_hash()
    diffs: dict[str, str] = {}

    for path in sorted(glob.glob(os.path.join(_CONFIG_DIR, "*.md"))):
        rel = os.path.relpath(path, _SCRIPT_DIR)

        if sync_hash:
            r = subprocess.run(
                ["git", "diff", sync_hash, "HEAD", "--", rel],
                capture_output=True, text=True, cwd=_SCRIPT_DIR,
            )
            if r.returncode == 0 and r.stdout.strip():
                diffs[rel] = r.stdout
                continue

        # Uncommitted changes
        r = subprocess.run(
            ["git", "diff", "HEAD", "--", rel],
            capture_output=True, text=True, cwd=_SCRIPT_DIR,
        )
        if r.returncode == 0 and r.stdout.strip():
            diffs[rel] = r.stdout
            continue

        # First run, no sync hash — check last commit
        if not sync_hash:
            r = subprocess.run(
                ["git", "diff", "HEAD~1", "HEAD", "--", rel],
                capture_output=True, text=True, cwd=_SCRIPT_DIR,
            )
            if r.returncode == 0 and r.stdout.strip():
                diffs[rel] = r.stdout

    return diffs


def _extract_directives(diffs: dict[str, str]) -> list[dict]:
    """Parse CHANGE:/REMOVE:/RENAME:/FIX: lines from added lines in config diffs."""
    directives: list[dict] = []
    for path, diff in diffs.items():
        for line in diff.splitlines():
            if not line.startswith("+") or line.startswith("+++"):
                continue
            stripped = line[1:].strip()
            for prefix in _DIRECTIVE_PREFIXES:
                if stripped.upper().startswith(prefix):
                    directives.append({
                        "type":   prefix.rstrip(":").lower(),
                        "text":   stripped[len(prefix):].strip(),
                        "source": path,
                    })
                    break
    return directives


# ── Code-block extraction helpers ─────────────────────────────────────────────

def _extract_handlers_block(source: str) -> str:
    """Extract the handlers = {...} literal from _dispatch_command."""
    m = re.search(r'(?m)^        handlers = \{', source)
    if not m:
        return ""
    rest  = source[m.end():]
    close = re.search(r'(?m)^        \}', rest)
    if not close:
        return ""
    return source[m.start(): m.end() + close.end()]


def _extract_help_block(source: str) -> str:
    """Extract _HELP_TEXT = \"\"\"...\"\"\" including its delimiters."""
    m = re.search(r'(?m)^_HELP_TEXT = """', source)
    if not m:
        return ""
    rest  = source[m.end():]
    close = re.search(r'(?m)^"""', rest)
    if not close:
        return ""
    return source[m.start(): m.end() + close.end()]


def _extract_method_block(source: str, name: str) -> str:
    """Extract a named function/method from source using the AST."""
    import ast as _ast
    try:
        tree = _ast.parse(source)
    except SyntaxError:
        return ""
    lines = source.splitlines(keepends=True)
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)) and node.name == name:
            return "".join(lines[node.lineno - 1: node.end_lineno])
    return ""


def _insert_method_after(source: str, after_method: str, new_method_code: str) -> str:
    """Splice new_method_code into source immediately after after_method."""
    import ast as _ast
    try:
        tree = _ast.parse(source)
    except SyntaxError:
        return source
    lines = source.splitlines(keepends=True)
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)) and node.name == after_method:
            insert_at = node.end_lineno
            block = "\n" + new_method_code
            if not block.endswith("\n"):
                block += "\n"
            return "".join(lines[:insert_at]) + block + "".join(lines[insert_at:])
    return source


# ── Source validation ─────────────────────────────────────────────────────────

def _validate_source(source: str) -> str | None:
    """Return an error string if source has a syntax/compile error, else None."""
    import ast as _ast, py_compile, tempfile
    try:
        _ast.parse(source)
    except SyntaxError as e:
        return f"SyntaxError at line {e.lineno}: {e.msg}"
    with tempfile.NamedTemporaryFile(
        suffix=".py", mode="w", encoding="utf-8", delete=False
    ) as tf:
        tf.write(source)
        tmp = tf.name
    try:
        py_compile.compile(tmp, doraise=True)
        return None
    except py_compile.PyCompileError as e:
        return str(e)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


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
  [bold #5f87af]/update[/bold #5f87af]       detect config directives and propose code changes
  [bold #5f87af]/apply[/bold #5f87af]        apply the diff proposed by /update (asks yes/no first)
  [bold #5f87af]/status[/bold #5f87af]       show current session state (web, file, history, vault)
  [bold #5f87af]/version[/bold #5f87af]      print the chatui.py version string
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
        self._pending_source: str | None = None
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

        self._update_subtitle()

        if self.db is None:
            self._log("[yellow]No vault database found. Run [bold]/ingest[/bold] to build it.[/yellow]\n")
        else:
            self._log("[dim]Vault loaded. Ask anything, or type /help for commands.[/dim]\n")

        self.query_one(Input).focus()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _log(self, markup: str, save: bool = True) -> None:
        self.query_one(RichLog).write(Text.from_markup(markup))
        if save:
            plain = re.sub(r'\[/?[^\]]*\]', '', markup).strip()
            if plain:
                self._append_to_session("assistant", plain)

    def _log_md(self, text: str, save: bool = True) -> None:
        self.query_one(RichLog).write(Markdown(text))
        if save:
            self._append_to_session("assistant", text)

    def _update_subtitle(self) -> None:
        parts = [CHAT_MODEL]
        parts.append("web: on" if self._web_on else "web: off")
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
            self._log(f"\n[bold #ce9178]> {text}[/bold #ce9178]", save=False)
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
            "version":   lambda _: self._cmd_version(),
            "status":    lambda _: self._cmd_status(),
        }

        if cmd in handlers:
            handlers[cmd](args)
        else:
            close = difflib.get_close_matches(cmd, handlers.keys(), n=1, cutoff=0.6)
            hint = f"  Did you mean [bold]/{ close[0]}[/bold]?" if close else "  Type [bold]/help[/bold] for the list."
            self._log(f"[red]Unknown command: /{cmd}[/red]{hint}")

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
        self._update_subtitle()
        state = "[green]on[/green]" if self._web_on else "[red]off[/red]"
        self._log(f"[dim]Web search fallback: {state}[/dim]")

    @work
    async def _cmd_version(self, args: str = "") -> None:
        version = "0.1.0"  # Default version string
        try:
            with open("VERSION", "r") as file:
                version = file.read().strip()
        except FileNotFoundError:
            pass
        self._log(f"[dim]ChatUI.py version: {version}[/dim]")

    def _cmd_status(self) -> None:
        web = "[green]on[/green]" if self._web_on else "[red]off[/red]"
        lines = [
            "[bold]Session status[/bold]",
            f"  web search:    {web}",
            f"  open file:     {self._open_file.rel if self._open_file else '[dim]none[/dim]'}",
            f"  history:       {len(self._history) // 2} exchange{'s' if len(self._history) // 2 != 1 else ''}",
            f"  pending notes: {len(self._pending)}",
            f"  vault:         {'loaded' if self.db else '[yellow]not loaded — run /ingest[/yellow]'}",
            f"  patch pending: {'yes' if self._pending_source else 'no'}",
        ]
        self._log("\n".join(lines))

    # ── /update command ─────────────────────────────────────────────────────────────

    @work
    async def _cmd_update(self, _args: str = "") -> None:
        self._log("[bold]🔄  Scanning config changes via git…[/bold]")

        config_diffs = await asyncio.to_thread(_collect_config_diffs_git)
        if not config_diffs:
            self._log("[dim]No config changes found since last sync.[/dim]")
            return

        for rel, diff in sorted(config_diffs.items()):
            n = sum(1 for ln in diff.splitlines()
                    if ln.startswith(("+", "-")) and not ln.startswith(("+++", "---")))
            self._log(f"[dim]  📝 {rel}  ({n} changed lines)[/dim]")

        directives = _extract_directives(config_diffs)
        if not directives:
            self._log(
                "[dim]No actionable directives found. "
                "Add CHANGE:/REMOVE:/RENAME:/FIX: lines to config files.[/dim]"
            )
            return

        self._log("[cyan]  Directives:[/cyan]")
        for d in directives:
            self._log(f"  [dim]  • [{d['type'].upper()}] {d['text']}[/dim]")

        try:
            with open(os.path.abspath(__file__), encoding="utf-8") as f:
                source = f.read()
        except OSError as e:
            self._log(f"[red]Could not read chatui.py: {e}[/red]")
            return

        guide  = _build_chatui_guide(source)
        result = source

        for d in directives:
            updated = await self._apply_directive(result, d, guide)
            if updated is not None:
                result = updated

        ok, result = await self._validate_and_heal(result)
        if not ok:
            return

        diff_lines = list(difflib.unified_diff(
            source.splitlines(keepends=True),
            result.splitlines(keepends=True),
            fromfile="chatui.py (current)",
            tofile="chatui.py (proposed)",
            n=3,
        ))

        if not diff_lines:
            self._log("[dim]No changes generated.[/dim]")
            return

        self._log_md("```diff\n" + "".join(diff_lines) + "\n```")
        self._pending_source = result
        self._log(
            "\n[dim]Review the diff above, then run "
            "[bold]/apply[/bold] to write it — or edit chatui.py manually.[/dim]"
        )

    async def _apply_directive(self, source: str, d: dict, guide: str) -> str | None:
        """Route a single directive to the appropriate handler; return updated source."""
        dtype = d["type"]
        text  = d["text"]

        cmd_m = re.search(r'/(\w+)', text)
        name  = cmd_m.group(1).lower() if cmd_m else None

        if dtype == "change" and name:
            return await self._directive_add_command(source, name, text, guide)

        if dtype == "remove" and name:
            return self._directive_remove_command(source, name)

        if dtype == "rename":
            old_m = re.search(r'/(\w+)', text)
            new_m = re.search(r'[→>]\s*/(\w+)', text) or re.search(r'\bto\s+/(\w+)', text, re.I)
            if old_m and new_m:
                return self._directive_rename_command(source, old_m.group(1), new_m.group(1))

        return await self._directive_model_guided(source, text, guide)

    async def _directive_add_command(
        self, source: str, name: str, description: str, guide: str
    ) -> str:
        self._log(f"[dim]  ➕  Adding /{name}…[/dim]")

        # Handler entry (deterministic)
        handlers_block = _extract_handlers_block(source)
        if handlers_block and f'"{name}"' not in handlers_block:
            new_entry    = '            "' + name + '":   lambda _: self._cmd_' + name + '(),\n'
            new_handlers = handlers_block.replace('\n        }', '\n' + new_entry + '        }', 1)
            source       = source.replace(handlers_block, new_handlers, 1)

        # Help line (deterministic)
        help_block = _extract_help_block(source)
        if help_block and f"/{name}" not in help_block:
            pad         = max(1, 14 - len(name))
            new_help_ln = f"  [bold #5f87af]/{name}[/bold #5f87af]{' ' * pad}{description[:55]}\n"
            new_help    = help_block.replace("[dim]Ctrl", new_help_ln + "[dim]Ctrl", 1)
            source      = source.replace(help_block, new_help, 1)

        # Method body (model-generated, ~60-line context)
        if f"def _cmd_{name}" not in source:
            examples    = "\n\n".join(filter(None, [
                _extract_method_block(source, "_cmd_clear"),
                _extract_method_block(source, "_cmd_web"),
            ]))
            method_code = await self._generate_new_method(name, description, examples)
            if method_code:
                # Strip markdown fences and normalise to 4-space class-method indent
                method_code = re.sub(r'^```\w*\s*\n?', '', method_code)
                method_code = re.sub(r'\n?```\s*$', '', method_code).strip()
                lines_m = method_code.splitlines()
                min_ind = min((len(l) - len(l.lstrip()) for l in lines_m if l.strip()), default=0)
                if min_ind != 4:
                    method_code = "\n".join(
                        "    " + l[min_ind:] if l.strip() else l for l in lines_m
                    )
                # Validate in isolation before inserting into the full source
                import ast as _ast
                try:
                    _ast.parse("class _T:\n" + method_code + "\n")
                except SyntaxError as e:
                    self._log(f"[yellow]⚠  Generated /{name} method invalid ({e.msg}) — inserting stub[/yellow]")
                    method_code = (
                        f"    def _cmd_{name}(self, _args: str = \"\") -> None:\n"
                        f"        self._log(\"[dim]/{name} — stub (edit manually)[/dim]\")\n"
                    )
                source = _insert_method_after(source, "_cmd_web", method_code)

        return source

    def _directive_remove_command(self, source: str, name: str) -> str:
        self._log(f"[dim]  ➖  Removing /{name}…[/dim]")

        source = re.sub(rf'(?m)^ +"{{re.escape(name)}}":[^\n]+\n', "", source)
        source = re.sub(
            rf'(?m)^ +\[bold #5f87af\]/{{re.escape(name)}}\[/bold #5f87af\][^\n]*\n', "", source
        )

        import ast as _ast
        try:
            tree = _ast.parse(source)
            for node in _ast.walk(tree):
                if (isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef))
                        and node.name == f"_cmd_{name}"):
                    lines  = source.splitlines(keepends=True)
                    source = "".join(lines[:node.lineno - 1]) + "".join(lines[node.end_lineno:])
                    break
        except SyntaxError:
            pass

        return source

    def _directive_rename_command(self, source: str, old: str, new: str) -> str:
        self._log(f"[dim]  ✏️   Renaming /{old} → /{new}…[/dim]")
        source = source.replace(f'"{old}":', f'"{new}":')
        source = source.replace(f"_cmd_{old}", f"_cmd_{new}")
        source = source.replace(f"/{old}", f"/{new}")
        return source

    async def _directive_model_guided(self, source: str, instruction: str, guide: str) -> str:
        """Ask coding_llm to make a targeted change described by instruction."""
        self._log(f"[dim]  🤖  {CODING_MODEL}: {instruction[:70]}…[/dim]")

        relevant_block = ""
        for m in re.finditer(r'_cmd_\w+', instruction):
            block = _extract_method_block(source, m.group(0))
            if block:
                relevant_block = block
                break

        prompt = "\n".join([
            "Make the following targeted change to chatui.py:",
            instruction,
            "",
            "STRUCTURAL GUIDE:",
            guide[:600],
            "",
            *(["RELEVANT CODE:", relevant_block, ""] if relevant_block else []),
            "Return the updated code for the changed section only. No explanation, no fences.",
        ])
        updated = await asyncio.to_thread(lambda: coding_llm.invoke(prompt).content.strip())

        if relevant_block and updated and updated.strip() != relevant_block.strip():
            return source.replace(relevant_block, updated, 1)
        return source

    async def _generate_new_method(self, cmd_name: str, description: str, examples: str) -> str:
        prompt = "\n".join([
            f"Write a `_cmd_{cmd_name}(self, _args: str = \"\")` method for the ChatApp Textual TUI class.",
            f"Purpose: {description}",
            "",
            "Style examples — copy indentation and patterns exactly:",
            examples,
            "",
            "Rules:",
            "  - 4-space indent (method is inside a class)",
            "  - Use self._log() to write output to the UI",
            "  - Add @work decorator and make it async if the operation could take time",
            "",
            "Return ONLY the method definition. No class wrapper, no explanation, no fences.",
        ])
        return await asyncio.to_thread(lambda: coding_llm.invoke(prompt).content.strip())

    async def _validate_and_heal(self, source: str) -> tuple[bool, str]:
        """Validate source; self-heal on syntax error (max 2 retries). Returns (ok, source)."""
        for attempt in range(3):
            error = _validate_source(source)
            if error is None:
                return True, source

            self._log(f"[yellow]⚠  Syntax error (attempt {attempt + 1}/3): {error}[/yellow]")
            if attempt == 2:
                self._log("[red]Could not heal source after 3 attempts — aborting.[/red]")
                return False, source

            lines  = source.splitlines(keepends=True)
            m      = re.search(r'line (\d+)', error)
            err_ln = int(m.group(1)) if m else len(lines)
            start  = max(0, err_ln - 15)
            end    = min(len(lines), err_ln + 15)
            region = "".join(
                f"{start + i + 1:5d} {ln}" for i, ln in enumerate(lines[start:end])
            )

            heal_prompt = "\n".join([
                f"Fix this Python syntax error: {error}",
                "",
                "Problematic region:",
                region,
                "",
                f"Return ONLY the corrected code for lines {start + 1}–{end}. No explanation.",
            ])
            fixed  = await asyncio.to_thread(lambda: coding_llm.invoke(heal_prompt).content.strip())
            fixed  = re.sub(r'^```\w*\s*\n?', '', fixed)
            fixed  = re.sub(r'\n?```\s*$', '', fixed)
            fixed  = re.sub(r'(?m)^\d+\s+', '', fixed)  # strip leading line numbers only
            source = "".join(lines[:start]) + fixed + "\n" + "".join(lines[end:])

        return False, source

    # ── /apply command ────────────────────────────────────────────────────────────────

    @work
    async def _cmd_apply(self, _args: str = "") -> None:
        if not self._pending_source:
            self._log("[dim]No pending changes — run /update first.[/dim]")
            return

        self._log("[bold yellow]⚠  Apply pending changes to chatui.py?[/bold yellow]")
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

        target = os.path.abspath(__file__)
        tmp    = target + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(self._pending_source)
            os.replace(tmp, target)
        except OSError as e:
            self._log(f"[red]✗  Write failed: {e}[/red]")
            try:
                os.unlink(tmp)
            except OSError:
                pass
            return

        head = _git_head_hash()
        if head:
            _set_sync_hash(head)

        self._pending_source = None
        self._log("[green]✓  Changes written to chatui.py.[/green]")
        self._log("[dim]Quit and restart to load the new code.[/dim]")
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

    async def _stream_llm(
        self, prompt: str, *, model: ChatOllama | None = None, log_result: bool = True
    ) -> str:
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
        if accumulated and log_result:
            self._log_md(accumulated, save=False)
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
