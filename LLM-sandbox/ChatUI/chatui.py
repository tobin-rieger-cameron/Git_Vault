"""
chatui.py — local RAG chat interface for your Obsidian vault.
All functions are available as /commands within the chat.
"""

from __future__ import annotations

import asyncio
import difflib
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

import yaml

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, RichLog, Static, TextArea
from rich.markdown import Markdown
from rich.markup import escape as rich_escape
from rich.text import Text

import chromadb

from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

try:
    from ddgs import DDGS
    _DDG_AVAILABLE = True
except ImportError:
    _DDG_AVAILABLE = False

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    _WATCHDOG_AVAILABLE = True
except ImportError:
    _WATCHDOG_AVAILABLE = False


# ── Config ────────────────────────────────────────────────────────────────────

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT  = os.path.dirname(_SCRIPT_DIR)
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

# ── Paths — edit these if you reorganise the folder layout ───────────────────
VAULT_PATH        = _cfg.get("vault_path", os.path.join(_REPO_ROOT, "Knowledge"))
CONVERSATIONS_DIR = os.path.join(VAULT_PATH, "conversations")
DB_PATH           = os.path.join(_SCRIPT_DIR, "local_db")
_MANIFEST_PATH       = os.path.join(DB_PATH, "manifest.json")
_STRUCTURE_PLAN_PATH = os.path.join(_SCRIPT_DIR, "config", "vault-structure-plan.md")
_ORGANIZE_FEEDBACK_PATH = os.path.join(_SCRIPT_DIR, "config", "organize_feedback.md")
# ─────────────────────────────────────────────────────────────────────────────

# Vault folder hierarchy (mirrors config/vault-structure-plan.md)
_DEWEY_FOLDERS = [
    "000-information", "100-philosophy", "200-religion",
    "300-social-sciences", "400-language", "500-natural-sciences",
    "600-applied-sciences", "700-arts", "800-literature", "900-history",
    "misc",
]

_TAG_TO_FOLDER: dict[str, str] = {
    "taxonomy":            "000-information",
    "information-science": "000-information",
    "index":               "000-information",
    "philosophy":          "100-philosophy",
    "ethics":              "100-philosophy",
    "religion":            "200-religion",
    "social-sciences":     "300-social-sciences",
    "mathematics":         "500-natural-sciences",
    "physics":             "500-natural-sciences",
    "biology":             "500-natural-sciences",
    "chemistry":           "500-natural-sciences",
    "ai":                  "600-applied-sciences",
    "machinelearning":     "600-applied-sciences",
    "engineering":         "600-applied-sciences",
    "medicine":            "600-applied-sciences",
    "arts":                "700-arts",
    "language":            "400-language",
    "linguistics":         "400-language",
    "literature":          "800-literature",
    "history":             "900-history",
    "geography":           "900-history",
}

# Tags that carry type/quality meaning rather than topic placement
_PLACEMENT_SKIP_TAGS = {"general", "meta"}

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

_SKIP_DIRS        = {"__pycache__", "local_db", ".git", "config"}
_UNCERTAIN_PREFIX = "i'm not certain"

_CLASS_Q_RE = re.compile(
    r'^\s*(what\s+(?:is|are|was|were)|explain|describe|'
    r'overview\s+of|introduction\s+to|tell\s+me\s+about|'
    r'how\s+does|how\s+do)\b',
    re.IGNORECASE,
)
_CLASS_Q_TOPIC_RE = re.compile(
    r'^\s*(?:what\s+(?:is|are|was|were)|explain(?:\s+to\s+me)?|describe|'
    r'overview\s+of|introduction\s+to|tell\s+me\s+about|'
    r'how\s+does|how\s+do)\s+(?:the\s+|a\s+|an\s+)?(.+?)[\?\.!]?\s*$',
    re.IGNORECASE,
)

def _detect_class_question(question: str) -> tuple[bool, str]:
    """Return (is_class_q, topic). Topic is the subject noun extracted from the question."""
    m = _CLASS_Q_TOPIC_RE.match(question.strip())
    if m:
        return True, m.group(1).strip()
    return False, ""

def _source_covers_topic(sources: list[str], topic: str) -> bool:
    """True if at least one source file stem shares a keyword with the topic."""
    stop = {"the", "a", "an", "of", "in", "is", "are", "and", "to", "for"}
    topic_words = {w for w in re.findall(r'\w+', topic.lower()) if w not in stop and len(w) > 2}
    for src in sources:
        stem_words = set(re.findall(r'\w+', os.path.splitext(os.path.basename(src))[0].lower()))
        if topic_words & stem_words:
            return True
    return False


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
_PID_FILE  = os.path.join(_SCRIPT_DIR, ".chatui.pid")


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
    parsed = yaml.safe_load(m.group(1)) or {}
    tags = parsed.get("tags", [])
    if isinstance(tags, list):
        return [str(t).strip() for t in tags if t]
    if isinstance(tags, str):
        return [tags.strip()]
    return []


def _tags_to_metadata(tags: list[str]) -> dict:
    return {f"tag_{t}": True for t in tags}


def _get_chunk_tags(doc: Document) -> list[str]:
    return [k[4:] for k, v in doc.metadata.items() if k.startswith("tag_") and v is True]


def _make_tag_filter(tags: list[str]) -> dict:
    if len(tags) == 1:
        return {f"tag_{tags[0]}": True}
    return {"$or": [{f"tag_{t}": True} for t in tags]}


# ── Database ──────────────────────────────────────────────────────────────────

def _discover_vault_files() -> list[str]:
    """All .md files under VAULT_PATH that should be ingested (conversations excluded)."""
    conv_prefix = CONVERSATIONS_DIR + os.sep
    return sorted(
        p for p in glob.glob(os.path.join(VAULT_PATH, "**", "*.md"), recursive=True)
        if not p.startswith(conv_prefix)
    )


def _needs_placement(path: str) -> bool:
    """True if the file is in the vault root or misc/ — i.e. not yet filed."""
    parts = os.path.relpath(path, VAULT_PATH).split(os.sep)
    return len(parts) == 1 or parts[0] == "misc"


def _classify_for_placement(tags: list[str], content: str, llm) -> str:
    """Return the target Dewey folder for a file. Tag map first, LLM fallback."""
    for tag in tags:
        if tag in _PLACEMENT_SKIP_TAGS:
            continue
        folder = _TAG_TO_FOLDER.get(tag)
        if folder:
            return folder
    # LLM fallback — read structure plan for context
    try:
        plan = open(_STRUCTURE_PLAN_PATH, encoding="utf-8").read()
    except OSError:
        plan = ""
    folder_list = ", ".join(_DEWEY_FOLDERS)
    feedback = _load_organize_feedback("placement")
    prompt = (
        f"{feedback}\n\n" if feedback else ""
    ) + (
        "You are classifying a knowledge vault article into a folder.\n\n"
        f"Available folders:\n{folder_list}\n\n"
        f"Folder descriptions (from vault-structure-plan.md):\n{plan[:1200]}\n\n"
        f"Article content (first 400 chars):\n{content[:400]}\n\n"
        f"Reply with ONLY one folder name from this list: {folder_list}\n"
        "If uncategorisable, reply: misc\n\nFolder:"
    )
    result = llm.invoke(prompt).content.strip().lower()
    for folder in _DEWEY_FOLDERS:
        if folder in result:
            return folder
    return "misc"


def _log_organize_feedback(kind: str, path: str, proposed: str, chosen: str, reason: str) -> None:
    """Append a record of a manual override to config/organize_feedback.md, so future
    /organize and /distill suggestion prompts can learn from past corrections."""
    ts = datetime.now().strftime("%Y-%m-%d")
    name = os.path.basename(path)
    entry = (
        f"\n## {ts} — {name} ({kind})\n"
        f"Proposed: {proposed.strip()[:300]}\n"
        f"Chosen: {chosen.strip()[:300]}\n"
        f"Reason: {reason.strip() if reason.strip() else '(none given)'}\n"
    )
    if not os.path.exists(_ORGANIZE_FEEDBACK_PATH):
        with open(_ORGANIZE_FEEDBACK_PATH, "w", encoding="utf-8") as f:
            f.write(
                "---\nsummary: Log of manual overrides during /organize and /distill review "
                "— fed back into future tag/wikilink/placement suggestion prompts.\n---\n\n"
                "# Organize Feedback\n"
            )
    with open(_ORGANIZE_FEEDBACK_PATH, "a", encoding="utf-8") as f:
        f.write(entry)


def _load_organize_feedback(kind: str, limit: int = 8) -> str:
    """Return the last `limit` override entries for `kind`, formatted for prompt
    injection. Empty string if the log doesn't exist or has no matching entries."""
    if not os.path.exists(_ORGANIZE_FEEDBACK_PATH):
        return ""
    try:
        content = open(_ORGANIZE_FEEDBACK_PATH, encoding="utf-8").read()
    except OSError:
        return ""
    entries = re.findall(
        rf'^## .+? — .+? \({re.escape(kind)}\)\n(.+?)(?=\n## |\Z)', content, re.MULTILINE | re.DOTALL
    )
    if not entries:
        return ""
    recent = [e.strip() for e in entries[-limit:]]
    return "Past corrections to consider:\n" + "\n---\n".join(recent)


def _validate_wikilinks(dry_run: bool = False, only_path: str | None = None) -> dict[str, list[tuple[str, str]]]:
    """Scan all vault files for [[wikilinks]] pointing at stale filenames (e.g. the
    pre-rename kebab-case stems left over from the Session 16 Title Case migration)
    and rewrite them to match the real current filename. Only touches links that
    resolve to a real vault file once hyphens/spaces/case are normalised — never
    invents or removes a link target. Returns {file: [(old_target, new_target), ...]}.
    `only_path`, if given, applies fixes to just that one file (stem map is still
    built from the whole vault)."""
    files = _discover_vault_files()
    stems = [os.path.splitext(os.path.basename(p))[0] for p in files]

    def _norm(s: str) -> str:
        return re.sub(r'[-\s_]+', ' ', s).strip().lower()

    norm_map: dict[str, str] = {}
    for stem in stems:
        norm_map.setdefault(_norm(stem), stem)

    fixes: dict[str, list[tuple[str, str]]] = {}
    for path in files:
        if only_path and os.path.abspath(path) != os.path.abspath(only_path):
            continue
        with open(path, encoding="utf-8") as fh:
            content = fh.read()

        file_fixes: list[tuple[str, str]] = []

        def _repl(m: re.Match) -> str:
            target, _, alias = m.group(1).partition('|')
            target = target.strip()
            real = norm_map.get(_norm(target))
            if real and real != target:
                file_fixes.append((target, real))
                return f'[[{real}|{alias}]]' if alias else f'[[{real}]]'
            return m.group(0)

        new_content = re.sub(r'\[\[([^\]]+)\]\]', _repl, content)

        if file_fixes:
            fixes[path] = file_fixes
            if not dry_run:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(new_content)

    return fixes


def _load_manifest() -> dict[str, float]:
    try:
        with open(_MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_manifest(paths: list[str]) -> None:
    os.makedirs(DB_PATH, exist_ok=True)
    with open(_MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump({p: os.path.getmtime(p) for p in paths}, f)


def _docs_to_chunks(docs: list[Document]) -> list[Document]:
    """Enrich docs with tag metadata then split into chunks."""
    for doc in docs:
        src = doc.metadata.get("source", "")
        if src.endswith(".md"):
            doc.metadata.update(_tags_to_metadata(_extract_frontmatter_tags(doc.page_content)))

    _MD_HEADERS   = [("#", "h1"), ("##", "h2"), ("###", "h3")]
    md_splitter   = MarkdownHeaderTextSplitter(headers_to_split_on=_MD_HEADERS, strip_headers=False)
    char_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    chunks: list[Document] = []
    for doc in docs:
        try:
            md_splits = md_splitter.split_text(doc.page_content)
        except Exception:
            md_splits = [doc]
        for split in md_splits:
            split.metadata.update(doc.metadata)
        chunks.extend(char_splitter.split_documents(md_splits))
    return chunks


def _load_files(paths: list[str]) -> list[Document]:
    docs = []
    for path in paths:
        try:
            content = open(path, encoding="utf-8").read()
            docs.append(Document(page_content=content, metadata={"source": path}))
        except OSError:
            pass
    return docs


def ingest_vault(force: bool = False) -> tuple[Chroma, dict[str, int]]:
    """Ingest vault into ChromaDB. Incremental by default; force=True rebuilds from scratch."""
    current_files = _discover_vault_files()
    if not current_files:
        raise RuntimeError("No markdown files found in vault.")

    manifest    = _load_manifest()
    db_exists   = os.path.exists(os.path.join(DB_PATH, "chroma.sqlite3"))

    if force or not db_exists or not manifest:
        # ── Full rebuild ──────────────────────────────────────────────────────
        docs   = _load_files(current_files)
        chunks = _docs_to_chunks(docs)
        if not chunks:
            raise RuntimeError("No content chunks produced from vault.")
        if os.path.exists(DB_PATH):
            shutil.rmtree(DB_PATH)
        try:
            client = chromadb.PersistentClient(path=DB_PATH)
            db = Chroma.from_documents(documents=chunks, embedding=embeddings, client=client, collection_name="vault")
        except Exception as e:
            if any(k in str(e).lower() for k in ("readonly", "locked", "lock")):
                raise RuntimeError(
                    "Database is locked by another process. "
                    "Close any other running instance of chatui.py and try /ingest again."
                ) from e
            raise
        _save_manifest(current_files)
        return db, {"new": len(current_files), "updated": 0, "removed": 0, "unchanged": 0}

    # ── Incremental update ────────────────────────────────────────────────────
    current_set  = set(current_files)
    manifest_set = set(manifest.keys())

    new_files     = [p for p in current_files if p not in manifest_set]
    changed_files = [p for p in current_files if p in manifest_set and os.path.getmtime(p) > manifest[p]]
    removed_files = [p for p in manifest_set  if p not in current_set]
    n_unchanged   = len(current_files) - len(new_files) - len(changed_files)

    client = chromadb.PersistentClient(path=DB_PATH)
    db     = Chroma(embedding_function=embeddings, client=client, collection_name="vault")

    for path in changed_files + removed_files:
        db._collection.delete(where={"source": path})

    to_embed = new_files + changed_files
    if to_embed:
        docs   = _load_files(to_embed)
        chunks = _docs_to_chunks(docs)
        if chunks:
            db.add_documents(chunks)

    _save_manifest(current_files)
    return db, {
        "new":       len(new_files),
        "updated":   len(changed_files),
        "removed":   len(removed_files),
        "unchanged": n_unchanged,
    }


def load_existing_db() -> Chroma | None:
    if not os.path.exists(DB_PATH):
        return None
    client = chromadb.PersistentClient(path=DB_PATH)
    return Chroma(embedding_function=embeddings, client=client, collection_name="vault")


def _reingest_file(path: str, db: Chroma) -> int:
    """Incrementally update a single file's chunks in an existing ChromaDB."""
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return 0
    db._collection.delete(where={"source": path})
    tags = _extract_frontmatter_tags(content)
    meta: dict = {"source": path}
    meta.update(_tags_to_metadata(tags))
    doc = Document(page_content=content, metadata=meta)
    _MD_HEADERS  = [("#", "h1"), ("##", "h2"), ("###", "h3")]
    md_sp  = MarkdownHeaderTextSplitter(headers_to_split_on=_MD_HEADERS, strip_headers=False)
    ch_sp  = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    try:
        splits = md_sp.split_text(content)
    except Exception:
        splits = [doc]
    for s in splits:
        s.metadata.update(meta)
    chunks = ch_sp.split_documents(splits)
    if chunks:
        db.add_documents(chunks)
    return len(chunks)


# ── Session utilities ─────────────────────────────────────────────────────────

def _finalize_session(path: str | None) -> None:
    """Rewrite session frontmatter with final turn count, commands, and topics."""
    if not path or not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return

    fname = os.path.basename(path)
    ts_m     = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})\.md', fname)
    day_only = re.match(r'(\d{4}-\d{2}-\d{2})\.md', fname)
    if ts_m:
        date_str = f"{ts_m.group(1)} {ts_m.group(2).replace('-', ':')}"
    elif day_only:
        date_str = day_only.group(1)
    else:
        date_m = re.search(r'# (?:Chat Session|Conversations) — (.+)', text)
        date_str = date_m.group(1).strip() if date_m else datetime.now().strftime("%Y-%m-%d")

    user_blocks = re.findall(
        r'^## \[\d+:\d+\] User\n\n(.*?)(?=\n^## |\Z)', text, re.MULTILINE | re.DOTALL
    )
    user_turns = len(user_blocks)
    commands = sorted({m for b in user_blocks for m in re.findall(r'^/\w+', b, re.MULTILINE)})
    questions = [b.strip() for b in user_blocks if not b.strip().startswith("/")]
    try:
        prompt = f"Extract 2-4 short topic keywords or noun phrases from these questions. Reply ONLY with a comma-separated list, nothing else.\n" + "\n".join(f"- {q[:120].replace(chr(10), ' ')}" for q in questions[:5])
        raw_topics = llm.invoke(prompt).content.strip()
        items = [item.strip() for item in raw_topics.split(",") if len(item.strip()) >= 3]
        topics = "; ".join(items[:4])
    except Exception:
        _qs = re.compile(r"^(?:what\s+(?:is|are)|how\s+(?:does|do|is|are)|why\s+is|what|how|why)\s+", re.IGNORECASE)
        topics = "; ".join(_qs.sub("", q).strip()[:50].replace("\n", " ") for q in questions[:3] if _qs.sub("", q).strip())

    fm_lines = ["---", f"date: {date_str}", f"user_turns: {user_turns}"]
    if commands:
        fm_lines.append("commands: [" + ", ".join(commands) + "]")
    if topics:
        fm_lines.append(f'topics: "{topics}"')
    fm_lines.append("---")
    new_fm = "\n".join(fm_lines) + "\n"

    if text.lstrip().startswith("---"):
        end_idx = text.find("---", text.index("---") + 3)
        if end_idx != -1:
            text = new_fm + "\n" + text[end_idx + 3:].lstrip("\n")
    else:
        text = new_fm + "\n" + text

    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _rebuild_conversation_index(conversations_dir: str) -> int:
    """Regenerate INDEX.md from all session files. Returns entry count."""
    files = sorted(glob.glob(os.path.join(conversations_dir, "*.md")))
    index_path = os.path.join(conversations_dir, "INDEX.md")
    entries: list[str] = []

    for fpath in files:
        fname = os.path.basename(fpath)
        if fname == "INDEX.md":
            continue
        try:
            with open(fpath, encoding="utf-8") as fh:
                content = fh.read()
        except OSError:
            continue

        turns, topics, cmds = "?", "", ""
        is_daily = "_daily" in fname

        if content.lstrip().startswith("---"):
            end = content.find("---", content.index("---") + 3)
            if end != -1:
                for line in content[content.index("---") + 3:end].splitlines():
                    if line.startswith("user_turns:"):
                        turns = line.split(":", 1)[1].strip()
                    elif line.startswith("topics:"):
                        topics = line.split(":", 1)[1].strip().strip('"')
                    elif line.startswith("commands:"):
                        cmds = line.split(":", 1)[1].strip().strip("[]")

        if turns == "?" and not is_daily:
            turns = str(len(re.findall(r'^## \[\d+:\d+\] User', content, re.MULTILINE)))

        ts_m   = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})\.md', fname)
        day_m  = re.match(r'(\d{4}-\d{2}-\d{2})_daily\.md', fname)
        date_m = re.match(r'(\d{4}-\d{2}-\d{2})\.md', fname)
        if ts_m:
            label = f"{ts_m.group(1)} {ts_m.group(2).replace('-', ':')}"
        elif day_m:
            label = f"{day_m.group(1)} (daily summary)"
        elif date_m:
            n_sess = len(re.findall(r'^## Session —', content, re.MULTILINE))
            label = f"{date_m.group(1)} ({n_sess} session{'s' if n_sess != 1 else ''})"
        else:
            label = fname

        parts = [f"[{label}]({fname})"]
        if not is_daily:
            parts.append(f"{turns} turns")
        if cmds:
            parts.append(cmds)
        entry = "- " + " · ".join(parts)
        if topics:
            entry += f" — {topics}"
        entries.append(entry)

    index_content = (
        f"# Conversation Index\n_Updated: {datetime.now().strftime('%Y-%m-%d')}_\n\n"
        + "\n".join(entries) + "\n"
    )
    with open(index_path, "w", encoding="utf-8") as fh:
        fh.write(index_content)
    return len(entries)


# ── Web Search ────────────────────────────────────────────────────────────────

def web_search(query: str) -> str:
    if not _DDG_AVAILABLE:
        return "ddgs not installed."
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


@dataclass
class Proposal:
    """A single suggested change, reviewed via ChatApp._review() before being applied."""
    kind:     str                    # "tags" | "wikilink" | "placement" | "wikilink_fix" | "distill_article"
    path:     str                    # file this targets (may not exist yet, e.g. a new /distill article)
    label:    str                    # short heading shown to the user, e.g. "Taxonomy.md"
    detail:   str                    # human-readable preview text
    proposed: str                    # the proposed final value (tag list / article body / target folder / ...)
    apply:    Callable[[str], None]  # writes the accepted-or-edited value


_DISTILL_TAG_MAP: list[tuple[str, list[str]]] = [
    ("machinelearning", ["machine learning", "fine tun", "fine-tun", "lora", "lo ra", "rlhf",
                         "distillation", "embedding", "transformer", "language model",
                         "neural network", "training", "llm", "pre train", "pre-train",
                         "knowledge distil"]),
    ("ai",             ["artificial intelligence", "deep learning", "llm", "language model",
                         "rag", "retrieval augmented", "retrieval-augmented", "prompt engineer",
                         "vector search", "vector database", "sparse retrieval", "dense retrieval",
                         "agentic", "agent pattern", "chatbot", "alignment", "constitutional"]),
    ("physics",        ["kinematic", "motion", "velocity", "mechanics", "dynamics", "force"]),
    ("mathematics",    ["math", "formal science", "logic", "algebra", "calculus", "statistic",
                         "set theory", "proof"]),
    ("biology",        ["biology", "photosynthesis", "evolution", "genetic", "organism",
                         "ecology", "cell"]),
    ("taxonomy",       ["taxonomy", "ontolog", "classification", "categor", "hierarch",
                         "folksonomy", "dewey", "knowledge organi", "discipline", "knowledge branch"]),
    ("philosophy",     ["philosophy", "epistemology", "metaphysics", "ethics"]),
    ("language",       ["linguistic", "grammar", "syntax", "semantic", "natural language",
                         "morpholog"]),
    ("history",        ["history", "historical", "civilization", "era", "ancient"]),
]


def _distill_tags(question: str, slug: str) -> list[str]:
    text = (question + " " + slug.replace("-", " ")).lower()
    return sorted(tag for tag, kws in _DISTILL_TAG_MAP if any(kw in text for kw in kws)) or ["general"]


def get_concept_suggestion(question: str, answer: str) -> str:
    prompt = (
        "Identify the single core concept this question and answer are about.\n"
        "Reply with only 1-3 words, lowercase, no punctuation. Used as a filename.\n"
        f"Question: {question}\nAnswer: {answer}\nCore concept:"
    )
    raw = coding_llm.invoke(prompt).content.strip().lower()
    return re.sub(r"\s+", "-", re.sub(r"[^a-z0-9\s-]", "", raw).strip()) or "general"


def save_to_vault(concept: str, question: str, answer: str, source: str, db: Chroma) -> None:
    filepath   = os.path.join(VAULT_PATH, f"{concept}.md")
    timestamp  = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry      = f"\n## Q: {question}\n*Source: {source} — {timestamp}*\n\n{answer}\n"
    write_path = filepath

    if os.path.exists(filepath):
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(entry)
    else:
        # Check for a semantically similar existing note before creating a new file
        try:
            hits = db.similarity_search_with_relevance_scores(f"Q: {question}", k=1)
            if hits and hits[0][1] >= 0.85:
                existing = hits[0][0].metadata.get("source", "")
                if existing and existing.endswith(".md") and os.path.exists(existing):
                    write_path = existing
        except Exception:
            pass

        if write_path == filepath:
            with open(write_path, "w", encoding="utf-8") as f:
                f.write(f"# {concept.replace('-', ' ').title()}\n{entry}")
        else:
            with open(write_path, "a", encoding="utf-8") as f:
                f.write(entry)

    if db is None:
        return

    try:
        with open(write_path, encoding="utf-8") as fh:
            tags = _extract_frontmatter_tags(fh.read())
    except OSError:
        tags = []

    meta = {"source": write_path}
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


def _depth_hint(topic: str) -> str:
    return (
        f'This is a broad question about "{topic}". '
        "Answer conversationally but comprehensively — cover the definition, "
        "historical context, key subfields or variants, applications, and "
        "relationship to adjacent concepts. "
        "Draw on your training knowledge to fill any gaps the notes don't cover. "
        "Write in fluent prose. Do not use markdown headers, bullet lists, or "
        "article formatting — this is a conversation, not a document."
    )


def build_vault_prompt(question: str, chunks: list, history: list[dict],
                       file_ctx: str = "", depth: str = "") -> str:
    parts = [
        "You are a helpful assistant with access to the user's personal notes.",
        "Use the context to answer the question as specifically as possible.",
        "If the context does not contain enough information, supplement it with your own knowledge and say which parts came from your training rather than the notes.",
    ]
    if depth:
        parts += ["", depth]
    parts += [""]
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


def build_grounded_prompt(question: str, chunks: list, history: list[dict],
                          file_ctx: str = "", depth: str = "") -> str:
    parts = [
        "You are a helpful assistant. Answer the question fully using your own training knowledge.",
        "The following notes from the user's vault may add useful context — incorporate them only if they directly address the question. Do not let off-topic notes distort your answer.",
    ]
    if depth:
        parts += ["", depth]
    parts += [""]
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


def build_knowledge_prompt(question: str, history: list[dict],
                           file_ctx: str = "", depth: str = "") -> str:
    parts = [
        "Answer the following question using your own knowledge.",
        f'If you are not confident, start with: "{_UNCERTAIN_PREFIX.capitalize()}, but"',
    ]
    if depth:
        parts += ["", depth]
    parts += [""]
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


# ── Vault file watcher ───────────────────────────────────────────────────────

if _WATCHDOG_AVAILABLE:
    class _VaultEventHandler(FileSystemEventHandler):
        _SKIP = {"__pycache__", ".git", "conversations"}

        def __init__(self, app: "ChatApp") -> None:
            self._app = app

        def _handle(self, path: str) -> None:
            if not path.endswith(".md"):
                return
            rel = os.path.relpath(path, VAULT_PATH)
            if any(rel.startswith(s) for s in self._SKIP):
                return
            self._app.call_from_thread(self._app._on_vault_file_changed, path)

        def on_modified(self, event) -> None:  # type: ignore[override]
            if not event.is_directory:
                self._handle(event.src_path)

        def on_created(self, event) -> None:  # type: ignore[override]
            if not event.is_directory:
                self._handle(event.src_path)


# ── Shared CSS ────────────────────────────────────────────────────────────────

_CSS = """
Screen { background: #1e1e1e; }
Header { background: #252526; color: #cccccc; }
Footer { background: #252526; color: #6c6c6c; }

RichLog {
    height: 1fr;
    background: #1e1e1e;
    padding: 1 4;
    scrollbar-color: #454545;
    scrollbar-background: #1e1e1e;
    overflow-x: hidden;
}

Input {
    margin: 0 4 1 4;
    background: #252526;
    color: #d4d4d4;
    border: tall #454545;
    padding: 0 1;
}

Input:focus { border: tall #5f87af; }

#stream {
    display: none;
    margin: 0 4;
    padding: 0 1;
    color: #d4d4d4;
}

#busy-bar {
    display: none;
    height: 1;
    background: #252526;
    color: #5f87af;
    text-align: center;
}

#main-body { height: 1fr; }

#chat-pane { width: 1fr; height: 1fr; }

#review-panel {
    display: none;
    width: 44;
    height: 1fr;
    border-right: solid #454545;
    padding: 0 1;
}

#review-panel-header { color: #cccccc; margin: 1 0 1 0; }

#review-list {
    height: 1fr;
    background: #1e1e1e;
    border: solid #454545;
    scrollbar-color: #454545;
    scrollbar-background: #1e1e1e;
}

#review-detail {
    height: auto;
    max-height: 14;
    color: #d4d4d4;
    padding: 1 0;
    overflow-y: auto;
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


# ── Proposal Edit Modal ──────────────────────────────────────────────────────

class ProposalEditScreen(ModalScreen[str | None]):
    """Full-text edit of a Proposal's suggested value before it's applied.
    Returns the edited text, or None if cancelled."""

    CSS = """
    ProposalEditScreen { align: center middle; }

    #edit-box {
        width: 92; height: 40;
        border: thick #5f87af;
        background: #252526;
        padding: 1 2;
    }
    #edit-header { color: #cccccc; text-style: bold; margin-bottom: 1; height: auto; }
    #edit-area {
        height: 1fr;
        background: #1e1e1e;
        border: solid #454545;
    }
    #edit-area:focus { border: tall #5f87af; }
    #edit-help { color: #6c6c6c; margin-top: 1; height: auto; }
    """

    BINDINGS = [
        Binding("ctrl+s", "save",   "Save"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, label: str, proposed: str) -> None:
        super().__init__()
        self._label    = label
        self._proposed = proposed

    def compose(self) -> ComposeResult:
        with Vertical(id="edit-box"):
            # markup=False: self._label is an arbitrary proposal label (filename /
            # rel path), not something safe to run through the Rich markup parser.
            yield Label(f"Edit — {self._label}", id="edit-header", markup=False)
            yield TextArea(self._proposed, id="edit-area")
            yield Label("[dim]Ctrl+S=save  ·  Esc=cancel[/dim]", id="edit-help")

    def on_mount(self) -> None:
        self.query_one("#edit-area", TextArea).focus()

    def action_save(self) -> None:
        self.dismiss(self.query_one("#edit-area", TextArea).text)

    def action_cancel(self) -> None:
        self.dismiss(None)


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
  [bold #5f87af]/edit[/bold #5f87af]         LLM-guided edit of a vault file (or the open file)
  [bold #5f87af]/daily[/bold #5f87af]        summarise today's chat sessions; optionally save
  [bold #5f87af]/export[/bold #5f87af]       export Q&A pairs as fine-tuning data (jsonl/alpaca/csv)
  [bold #5f87af]/status[/bold #5f87af]       show session state, model, vault stats
  [bold #5f87af]/version[/bold #5f87af]      print the chatui.py version string
  [bold #5f87af]/readme[/bold #5f87af]       regenerate README.md (shows diff, asks to confirm)
  [bold #5f87af]/harvest[/bold #5f87af]      promote INDEX topics into vault notes with \\[\\[links]]
  [bold #5f87af]/distill[/bold #5f87af]      distil a session file into structured vault articles
  [bold #5f87af]/model[/bold #5f87af] \\[name]  show or switch the chat model at runtime
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
        self._chat_model     = CHAT_MODEL
        self._organize_queue: asyncio.Queue[str] | None = None
        self._apply_queue:    asyncio.Queue[str] | None = None
        self._pending_source: str | None = None
        self._session_file:   str | None = None
        self._session_events: list[str]  = []
        self._open_file:      OpenFile | None = None
        self._review_proposals:     list[Proposal] | None = None
        self._review_active_index:  int | None = None

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-body"):
            with Vertical(id="review-panel"):
                yield Label("", id="review-panel-header")
                yield ListView(id="review-list")
                yield Static("", id="review-detail", markup=False)
            with Vertical(id="chat-pane"):
                # min_width=0: RichLog defaults to a 78-column floor, which forces a
                # phantom horizontal scrollbar once the review panel narrows this pane
                # below that on anything but a wide terminal.
                yield RichLog(id="log", markup=True, wrap=True, highlight=False, min_width=0)
                yield Static("", id="stream")
        yield Static("", id="busy-bar")
        yield Input(placeholder="Ask anything, or type /help for commands...", id="input")
        yield Footer()

    def on_mount(self) -> None:
        os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        ts    = now.strftime("%Y-%m-%d %H:%M:%S")
        self._session_file = os.path.join(CONVERSATIONS_DIR, f"{today}.md")
        if os.path.exists(self._session_file):
            with open(self._session_file, "a", encoding="utf-8") as f:
                f.write(f"\n---\n\n## Session — {ts}\n\n")
        else:
            with open(self._session_file, "w", encoding="utf-8") as f:
                f.write(
                    f"---\ndate: {today}\nstatus: active\n---\n\n"
                    f"# Conversations — {today}\n\n"
                    f"---\n\n## Session — {ts}\n\n"
                )

        self._update_subtitle()

        if self.db is None:
            self._log("[yellow]No vault database found. Run [bold]/ingest[/bold] to build it.[/yellow]\n")
        else:
            self._log("[dim]Vault loaded. Ask anything, or type /help for commands.[/dim]\n")

        if _WATCHDOG_AVAILABLE and self.db is not None:
            self._observer = Observer()
            self._observer.schedule(_VaultEventHandler(self), VAULT_PATH, recursive=True)
            self._observer.start()
            self._log("[dim]👁  Vault watcher active — edits auto-reingest.[/dim]", save=False)

        self.query_one(Input).focus()

    def on_unmount(self) -> None:
        if _WATCHDOG_AVAILABLE and hasattr(self, "_observer") and self._observer:
            self._observer.stop()
        _finalize_session(self._session_file)

    @work
    async def _on_vault_file_changed(self, path: str) -> None:
        if self.db is None or self._busy:
            return
        await asyncio.sleep(1.0)
        rel = os.path.relpath(path, VAULT_PATH)
        try:
            n = await asyncio.to_thread(_reingest_file, path, self.db)
            self._log(f"[dim]🔄  Auto-reingested {rel} ({n} chunk(s))[/dim]", save=False)
            self._note_event(f"reingest:{rel}")
        except Exception as e:
            self._log(f"[dim][yellow]Auto-reingest failed for {rel}: {e}[/yellow][/dim]", save=False)

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
        parts = [self._chat_model]
        parts.append("web: on" if self._web_on else "web: off")
        if self._pending:
            n = len(self._pending)
            parts.append(f"{n} unsaved note{'s' if n != 1 else ''}")
        if self._open_file:
            parts.append(f"📄 {self._open_file.rel}")
        self.sub_title = "  ·  ".join(parts)

    def _set_busy(self, busy: bool, label: str = "Processing…") -> None:
        self._busy = busy
        try:
            bar = self.query_one("#busy-bar", Static)
            bar.update(f"  ⏳  {label}" if busy else "")
            bar.display = busy
        except Exception:
            pass

    def _set_status(self, label: str) -> None:
        try:
            self.query_one("#busy-bar", Static).update(f"  ⏳  {label}")
        except Exception:
            pass

    def _note_event(self, event: str) -> None:
        self._session_events.append(event)

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
            if role == "assistant" and self._session_events:
                f.write("<!-- " + " · ".join(self._session_events) + " -->\n\n")
                self._session_events.clear()

    # ── Input routing ─────────────────────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.value = ""

        if self._organize_queue is not None:
            if text:
                self._append_to_session("user", text)
            self._organize_queue.put_nowait(text)
            return

        if self._apply_queue is not None:
            if text.startswith("/"):
                self._log("[yellow]Please respond yes or no before running another command.[/yellow]")
                return
            if text:
                self._append_to_session("user", text)
            self._apply_queue.put_nowait(text)
            return

        if not text or self._busy:
            return

        if text.startswith("/"):
            self._dispatch_command(text)
        else:
            self._set_busy(True)
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
            "edit":     self._cmd_edit,
            "daily":    self._cmd_daily,
            "export":   self._cmd_export,
            "version":  lambda _: self._cmd_version(),
            "status":   lambda _: self._cmd_status(),
            "stats":    lambda _: self._cmd_stats(),
            "readme":   lambda _: self._cmd_readme(),
            "harvest":   lambda _: self._cmd_harvest(),
            "distill":   lambda a: self._cmd_distill(a),
            "model":     self._cmd_model,
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

    def _cmd_model(self, args: str) -> None:
        global llm
        name = args.strip()
        if not name:
            self._log(f"[bold]Chat model:[/bold] {self._chat_model}  [dim](default: {CHAT_MODEL})[/dim]")
            return
        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
            installed = {line.split()[0].split(":")[0] for line in result.stdout.splitlines()[1:] if line.strip()}
            short = name.split(":")[0]
            if short not in installed:
                self._log(f"[yellow]⚠ '{name}' not found locally (ollama list). Pull it first or the next query will fail.[/yellow]")
        except Exception:
            pass  # ollama not on PATH or timed out — proceed anyway
        llm = ChatOllama(model=name)
        self._chat_model = name
        self._update_subtitle()
        self._log(f"[green]✓ Switched to {name}[/green]  [dim](restoring default: /model {CHAT_MODEL})[/dim]")

    @work
    async def _cmd_harvest(self, _args: str = "") -> None:
        self._set_busy(True, "Harvesting topics…")
        created = 0
        updated = 0
    
        index_path = os.path.join(CONVERSATIONS_DIR, "INDEX.md")
        if not os.path.exists(index_path):
            self._log("[yellow]conversations/INDEX.md not found.\nRun /organize → Pass 1 (tags) generates INDEX.md as a side-effect.[/yellow]")
            self._set_busy(False)
            return
    
        with open(index_path, encoding="utf-8") as fh:
            lines = fh.readlines()
    
        topics: set[str] = set()
        for line in lines:
            m = re.search(r"— (.+)$", line.rstrip())
            if not m:
                continue
            for phrase in re.split(r";", m.group(1)):
                phrase = re.sub(r"^(?:what\s+(?:is|are)|how\s+(?:does|do|is|are)|why\s+is|what|how|why)\s+", "", phrase.strip(), flags=re.IGNORECASE)
                phrase = re.sub(r"^(?:a|an|the)\s+", "", phrase, flags=re.IGNORECASE)
                words = phrase.split()
                if len(words) > 2:
                    phrase = " ".join(words[:2])
                phrase = re.sub(r"\b(?:in|of|a|an|the|to|and|or|for|between)\b\s*$", "", phrase, flags=re.IGNORECASE)
                if len(phrase) >= 4:
                    topics.add(phrase)
    
        if not topics:
            self._log("[dim]No topics found in INDEX.md.[/dim]")
            self._set_busy(False)
            return
    
        self._log(f"[dim]Found {len(topics)} topic(s) to harvest…[/dim]")
    
        existing = {
            os.path.splitext(os.path.basename(p))[0].lower(): p
            for p in glob.glob(os.path.join(VAULT_PATH, "*.md"))
        }
    
        for topic in sorted(topics):
            slug = re.sub(r"[^\w]+", "-", topic.lower()).strip("-")
            existing_path = existing.get(slug) or existing.get(slug.replace("-", " "))
    
            if not existing_path:
                topic_words = [w for w in re.split(r"\W+", slug) if len(w) >= 5]
                for stem, path in existing.items():
                    if any(w in stem for w in topic_words) or slug in stem:
                        existing_path = path
                        break
    
            if existing_path:
                with open(existing_path, encoding="utf-8") as fh:
                    content = fh.read()
                if "[[INDEX]]" not in content:
                    with open(existing_path, "a", encoding="utf-8") as fh:
                        fh.write("\n\nSee also: [[INDEX]]\n")
                    self._log(f"[dim]  🔗  Linked {os.path.basename(existing_path)}[/dim]")
                    updated += 1
            else:
                stub_path = os.path.join(VAULT_PATH, f"{slug}.md")
                desc = await asyncio.to_thread(
                    lambda t=topic: llm.invoke(
                        f"In one sentence, describe the concept '{t}'. Be concise and factual."
                    ).content.strip()
                )
                title = topic[0].upper() + topic[1:]
                with open(stub_path, "w", encoding="utf-8") as fh:
                    fh.write(f"# {title}\n\n{desc}\n\nSee also: [[INDEX]]\n")
                self._log(f"[dim]  📄  Created {slug}.md[/dim]")
                created += 1
    
        self._set_busy(False)
        self._log(f"[green]✓ Harvest complete — {created} created, {updated} linked.[/green]")

    @work
    async def _cmd_distill(self, args: str = "") -> None:
        """Distil a conversation session into structured vault articles."""
        self._set_busy(True, "Distilling session…")

        # ── 1. Resolve session file ───────────────────────────────────────────
        target = args.strip()
        if not target:
            session_files = sorted(glob.glob(os.path.join(CONVERSATIONS_DIR, "*.md")))
            session_files = [f for f in session_files if not f.endswith("INDEX.md")]
            if session_files:
                recent = "\n".join(f"  {os.path.basename(f)}" for f in session_files[-5:])
                self._log(f"[yellow]Usage: /distill <session_file>[/yellow]\nRecent sessions:\n{recent}", save=False)
            else:
                self._log("[yellow]Usage: /distill <session_file>  (no sessions found yet)[/yellow]", save=False)
            self._set_busy(False)
            return
        for candidate in [target,
                          os.path.join(CONVERSATIONS_DIR, target),
                          os.path.join(CONVERSATIONS_DIR, target + ".md")]:
            if os.path.exists(candidate):
                target = candidate
                break
        if not os.path.exists(target):
            self._log(f"[red]Session file not found: {target}[/red]", save=False)
            self._set_busy(False)
            return

        # ── 2. Bootstrap article guide if missing ─────────────────────────────
        guide_path = os.path.join(_SCRIPT_DIR, "_article-guide.md")
        if not os.path.exists(guide_path):
            self._set_status("Bootstrapping article guide…")
            guide = await asyncio.to_thread(lambda: llm.invoke(
                "Write a concise guide (under 300 words) for writing structured markdown "
                "knowledge-base articles. Cover: YAML frontmatter with title + tags, H1 title, "
                "opening summary paragraph, H2 sections for key concepts, [[wikilinks]] for related "
                "notes, See also section. Focus on clarity and scannability. Output only the guide, "
                "no preamble or explanation."
            ).content.strip())
            with open(guide_path, "w", encoding="utf-8") as fh:
                fh.write(f"---\ntitle: Article Writing Guide\ntags: [meta]\n---\n\n"
                         f"# Article Writing Guide\n\n{guide}\n")
            self._log("[dim]📝 Created _article-guide.md[/dim]")
            if self.db:
                await asyncio.to_thread(lambda: _reingest_file(guide_path, self.db))
        with open(guide_path, encoding="utf-8") as fh:
            guide_ctx = fh.read()[:2000]

        # ── 3. Load taxonomy for hierarchy + tag awareness ────────────────────
        taxonomy_ctx = ""
        taxonomy_path = os.path.join(VAULT_PATH, "Taxonomy.md")
        if os.path.exists(taxonomy_path):
            with open(taxonomy_path, encoding="utf-8") as fh:
                taxonomy_ctx = fh.read()[:1500]

        # ── 4. Parse Q&A pairs from the session file ──────────────────────────
        with open(target, encoding="utf-8") as fh:
            text = fh.read()
        # Q&A pairs already distilled on a prior run are marked with this comment
        # right after their answer block, so re-running /distill on a growing
        # daily session file only processes what's new.
        _DISTILL_MARKER = "<!-- distilled -->"
        all_blocks = list(re.finditer(
            r'^## \[\d+:\d+\] (User|Assistant)\n\n(.*?)(?=^## \[|\Z)',
            text, re.MULTILINE | re.DOTALL
        ))
        qa_pairs: list[tuple[str, str, int]] = []
        i = 0
        while i < len(all_blocks):
            role, content = all_blocks[i].group(1), all_blocks[i].group(2)
            content = content.strip()
            if role == "User" and content and not content.startswith("/"):
                answer_parts = []
                j = i + 1
                while j < len(all_blocks) and all_blocks[j].group(1) == "Assistant":
                    part = all_blocks[j].group(2).strip()
                    # Skip status/emoji-only lines
                    if part and not re.match(r'^[🔍📓🏷🧠⏳👁📚✅⚠➕✏]\s', part):
                        answer_parts.append(part)
                    j += 1
                if answer_parts:
                    combined = "\n\n".join(answer_parts)
                    if _DISTILL_MARKER not in combined:
                        qa_pairs.append((content, combined, all_blocks[j - 1].end()))
                i = j
            else:
                i += 1

        if not qa_pairs:
            self._log("[yellow]No new (undistilled) Q&A pairs found in session.[/yellow]")
            self._set_busy(False)
            return
        self._log(f"[dim]Found {len(qa_pairs)} Q&A pairs.[/dim]")

        # ── 5. Existing vault stems for wikilink candidates ───────────────────
        vault_stems = [
            os.path.splitext(os.path.basename(p))[0]
            for p in _discover_vault_files()
            if not os.path.basename(p).startswith("_") and os.path.basename(p) != "README.md"
        ]
        stems_str = ", ".join(vault_stems)

        # ── 6. Generate one article per Q&A pair ──────────────────────────────
        created, updated = 0, 0
        marked_positions: list[int] = []
        for question, answer, mark_pos in qa_pairs:
            self._set_status(f"Writing article {created + updated + 1}/{len(qa_pairs)}…")

            # Derive filename slug from question
            slug_raw = await asyncio.to_thread(lambda q=question: llm.invoke(
                f"Give a 1-3 word lowercase hyphenated slug for this topic. "
                f"No articles, no verbs. Examples: 'lora-fine-tuning', 'vector-databases', "
                f"'knowledge-taxonomy'.\nTopic: {q}\nReply with ONLY the slug, nothing else."
            ).content.strip().lower())
            slug = re.sub(r'[^a-z0-9-]', '-', slug_raw).strip('-')[:50]
            if len(slug) < 3:
                continue

            # Trim source to clean prose (drop raw Q&A artifact lines)
            clean_answer = re.sub(r'^#+\s+Q:.*$', '', answer[:2000], flags=re.MULTILINE).strip()

            # Don't ask the 3b model to generate frontmatter — it produces malformed output.
            # Build it programmatically from the slug + keyword-based tag extraction.
            tags  = _distill_tags(question, slug)
            title = re.sub(r'-+', ' ', slug).strip().title()
            frontmatter = f'---\ntitle: "{title}"\ntags: [{", ".join(tags)}]\n---\n\n'

            # Check for a near-duplicate existing file before creating a new one —
            # save_to_vault uses 0.85 for /savefile's dedup, but empirically a genuine
            # topical duplicate here (e.g. "Q: what is LoRA..." against the existing
            # LoRA Adaptations.md prose) only scores ~0.69 — 0.85 never fires in practice
            # for this query shape. 0.7 is set from that measurement, not copied blindly.
            fpath = None
            if self.db is not None:
                try:
                    dedup_hits = await asyncio.to_thread(
                        lambda q=question: self.db.similarity_search_with_relevance_scores(f"Q: {q}", k=1)
                    )
                    if dedup_hits and dedup_hits[0][1] >= 0.7:
                        existing = dedup_hits[0][0].metadata.get("source", "")
                        if existing and existing.endswith(".md") and os.path.exists(existing):
                            fpath = existing
                except Exception:
                    pass

            if fpath is None:
                # Route into the same Dewey-style folder /organize would file this under,
                # and use the vault's Title Case With Spaces filename convention —
                # otherwise every /distill article lands unfiled in the vault root.
                folder = await asyncio.to_thread(_classify_for_placement, tags, clean_answer, coding_llm)
                target_dir = os.path.join(VAULT_PATH, folder)
                os.makedirs(target_dir, exist_ok=True)
                fpath = os.path.join(target_dir, title + ".md")

            already_exists = os.path.exists(fpath)

            vault_ref_ctx = ""
            if self.db is not None:
                try:
                    ref_results = await asyncio.to_thread(
                        lambda q=question: self.db.similarity_search_with_score(q, k=3)
                    )
                    good = [doc.page_content for doc, score in ref_results if score >= 0.45][:2]
                    if good:
                        vault_ref_ctx = "\n---\n".join(good)
                except Exception:
                    pass

            art_prompt = (
                f"ARTICLE WRITING GUIDE — follow every rule exactly:\n{guide_ctx}\n\n"
                f"---\n\n"
                f"TOPIC: {question}\n\n"
                f"SOURCE (distil into prose, do not quote verbatim):\n{clean_answer}\n\n"
                f"{f'REFERENCE MATERIAL FROM VAULT (treat as ground truth):{chr(10)}{vault_ref_ctx}{chr(10)}{chr(10)}' if vault_ref_ctx else ''}"
                f"EXISTING VAULT NOTES (ONLY use [[note-name]] wikilinks from this exact list — no others): {stems_str}\n"
                f"For See Also, prefer notes on the same specific subtopic (e.g. the exact classification "
                f"system or mechanism discussed) over notes that only share a broad field."
                f"{f'{chr(10)}TAXONOMY CONTEXT:{chr(10)}{taxonomy_ctx[:400]}' if taxonomy_ctx else ''}\n\n"
                f"Write the article body now (no YAML frontmatter — it will be added automatically):"
            )

            body = await asyncio.to_thread(lambda p=art_prompt: llm.invoke(p).content.strip())
            # Strip stray markdown fences
            body = re.sub(r'^```\w*\n?', '', body, flags=re.MULTILINE).strip()
            body = re.sub(r'\n?```\s*$', '', body, flags=re.MULTILINE).strip()
            # Strip any frontmatter the model added anyway (unclosed --- blocks etc.)
            if body.startswith('---'):
                close = body.find('\n---', 3)
                body = body[close + 4:].lstrip('\n') if close != -1 else re.sub(r'^-+\s*', '', body)

            # Strip invented wikilinks — only keep [[X]] where X matches a real vault stem
            vault_stems_set = {s.lower().replace('-', ' ') for s in vault_stems}
            vault_stems_set.update(s.lower().replace(' ', '-') for s in vault_stems)
            vault_stems_set.update(s.lower() for s in vault_stems)
            body = re.sub(
                r'\[\[([^\]]+)\]\]',
                lambda m: f'[[{m.group(1)}]]' if m.group(1).lower() in vault_stems_set
                          or m.group(1).lower().replace('-', ' ') in vault_stems_set
                          or m.group(1).lower().replace(' ', '-') in vault_stems_set
                          else m.group(1),
                body
            )

            article = frontmatter + body
            rel_fpath = os.path.relpath(fpath, VAULT_PATH)

            def _make_distill_apply(fpath: str, already_exists: bool, rel_fpath: str, mark_pos: int):
                def _apply(final_article: str) -> None:
                    nonlocal created, updated
                    if already_exists:
                        with open(fpath, "a", encoding="utf-8") as fh:
                            fh.write(f"\n\n---\n\n## Additional notes\n\n{final_article}\n")
                        self._log(f"[dim]✏️  Updated: {rel_fpath}[/dim]")
                        updated += 1
                    else:
                        with open(fpath, "w", encoding="utf-8") as fh:
                            fh.write(final_article + "\n")
                        self._log(f"[dim]📝 Created: {rel_fpath}[/dim]")
                        created += 1
                    marked_positions.append(mark_pos)
                return _apply

            self._log(f"\n[bold]Review — {rel_fpath}[/bold]")
            await self._review([Proposal(
                kind="distill_article", path=fpath, label=rel_fpath,
                detail=question.strip()[:100],
                proposed=article,
                apply=_make_distill_apply(fpath, already_exists, rel_fpath, mark_pos),
            )])

            if self.db and os.path.exists(fpath):
                await asyncio.to_thread(lambda p=fpath: _reingest_file(p, self.db))

        # Mark distilled Q&A pairs in the session file so a re-run only picks up
        # what's new. Insert from the highest offset down so earlier offsets stay valid.
        if marked_positions:
            for pos in sorted(set(marked_positions), reverse=True):
                text = text[:pos] + f"\n{_DISTILL_MARKER}\n" + text[pos:]
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(text)

        self._log(f"✅ Distilled {os.path.basename(target)}: {created} created, {updated} updated.")
        self._set_busy(False)

    @work
    async def _cmd_readme(self, _args: str = "") -> None:
        self._set_busy(True, "Generating README…")
        try:
            with open(os.path.abspath(__file__), encoding="utf-8") as fh:
                source = fh.read()

            handlers_raw = _extract_handlers_block(source)
            cmd_names    = re.findall(r'"(\w+)":', handlers_raw)
            help_raw     = _extract_help_block(source)

            help_rows: list[str] = []
            for name in cmd_names:
                m       = re.search(rf'\[bold[^\]]*\]/{re.escape(name)}\[/bold[^\]]*\]\s*(.+)', help_raw)
                purpose = re.sub(r'\[/?[^\]]*\]', '', m.group(1)).strip() if m else ""
                help_rows.append(f"| `/{name}` | {purpose} |")
            commands_table = "| Command | Description |\n|---|---|\n" + "\n".join(help_rows)

            cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "settings.md")
            with open(cfg_path, encoding="utf-8") as fh:
                cfg_text = fh.read()
            cfg_m = re.search(r'(## Settings.*?)(?=## |\Z)', cfg_text, re.DOTALL)
            cfg_section = cfg_m.group(1).strip() if cfg_m else ""

            prompt = "\n".join([
                "Write a concise README.md for ChatUI, a local-first vault RAG assistant.",
                "Include sections: Overview, Commands, Configuration, Architecture, Stack.",
                "",
                "COMMANDS (use these exact entries):",
                commands_table,
                "",
                "CONFIGURATION:",
                cfg_section,
                "",
                "ARCHITECTURE: local Ollama LLMs + ChromaDB vector store + Textual TUI.",
                f"STACK: {CHAT_MODEL} (chat), {CODING_MODEL} (code/organize), {EMBED_MODEL} (embeddings),"
                " ChromaDB, LangChain, Textual.",
                "",
                "Tone: terse technical docs. No fluff. Markdown tables where appropriate.",
                "Return only the README markdown, no fences.",
            ])
            self._set_status("✍ Writing README…")
            readme_text = await asyncio.to_thread(lambda: coding_llm.invoke(prompt).content.strip())

            readme_path = os.path.join(_REPO_ROOT, "README.md")
            existing = ""
            if os.path.exists(readme_path):
                with open(readme_path, encoding="utf-8") as fh:
                    existing = fh.read()

            diff_lines = list(difflib.unified_diff(
                existing.splitlines(keepends=True),
                readme_text.splitlines(keepends=True),
                fromfile="README.md (current)",
                tofile="README.md (proposed)",
                n=3,
            ))
            if not diff_lines:
                self._log("[dim]README is already up to date.[/dim]")
                return

            diff_str = "".join(diff_lines)
            coloured = re.sub(r'^(\+[^+].*)', r'[green]\1[/green]', diff_str, flags=re.MULTILINE)
            coloured = re.sub(r'^(-[^-].*)', r'[red]\1[/red]', coloured, flags=re.MULTILINE)
            self._log(f"[bold]README diff:[/bold]\n{coloured}")
            self._log("[dim]Write this README? Type [bold]yes[/bold] or anything else to cancel.[/dim]")
            inp = self.query_one(Input)
            inp.placeholder = "yes / no…"
            self._apply_queue = asyncio.Queue()
            try:
                resp = (await self._apply_queue.get()).strip().lower()
            finally:
                self._apply_queue = None
                inp.placeholder = "Ask anything, or type /help for commands..."
            if resp != "yes":
                self._log("[dim]README update cancelled.[/dim]")
                return

            with open(readme_path, "w", encoding="utf-8") as fh:
                fh.write(readme_text)
            self._log(f"[green]✓ README written → {os.path.relpath(readme_path, _REPO_ROOT)}[/green]")
        except Exception as e:
            self._log(f"[red]README generation failed: {e}[/red]")
        finally:
            self._set_busy(False)

    def _cmd_version(self) -> None:
        self._log("[dim]ChatUI version 0.2.0[/dim]")

    def _cmd_status(self) -> None:
        web = "[green]on[/green]" if self._web_on else "[red]off[/red]"
        n_chunks = self.db._collection.count() if self.db else 0
        db_size = 0
        if os.path.exists(DB_PATH):
            for dirpath, _, filenames in os.walk(DB_PATH):
                for fname in filenames:
                    try:
                        db_size += os.path.getsize(os.path.join(dirpath, fname))
                    except OSError:
                        pass
        db_mb   = db_size / (1024 * 1024)
        n_notes = len(glob.glob(os.path.join(VAULT_PATH, "*.md")))
        n_convs = len(glob.glob(os.path.join(CONVERSATIONS_DIR, "*.md")))
        lines = [
            "[bold]Status[/bold]",
            f"  model:         {self._chat_model}",
            f"  web search:    {web}",
            f"  open file:     {self._open_file.rel if self._open_file else '[dim]none[/dim]'}",
            f"  history:       {len(self._history) // 2} exchange{'s' if len(self._history) // 2 != 1 else ''}",
            f"  pending notes: {len(self._pending)}",
            f"  patch pending: {'yes' if self._pending_source else 'no'}",
            "",
            "[bold]Vault[/bold]",
            f"  path:          {VAULT_PATH}",
            f"  notes:         {n_notes}",
            f"  chunks:        {n_chunks}",
            f"  DB size:       {db_mb:.1f} MB",
            f"  sessions:      {n_convs}",
        ]
        self._log("\n".join(lines))

    @work
    async def _cmd_edit(self, args: str = "") -> None:
        if args:
            candidates = glob.glob(os.path.join(VAULT_PATH, "**", args), recursive=True)
            if not candidates:
                candidates = glob.glob(os.path.join(VAULT_PATH, f"**/*{args}*.md"), recursive=True)
            if not candidates:
                self._log(f"[red]No file matching '{args}' found in vault.[/red]")
                return
            target_path = candidates[0]
        elif self._open_file:
            target_path = self._open_file.path
        else:
            self._log("[yellow]Usage: /edit <filename>  (or /browse a file first)[/yellow]")
            return

        rel = os.path.relpath(target_path, VAULT_PATH)
        try:
            with open(target_path, encoding="utf-8") as f:
                original = f.read()
        except OSError as e:
            self._log(f"[red]Could not read {rel}: {e}[/red]")
            return

        self._log(f"[dim]✏️   Proposing edits for [bold]{rel}[/bold]…[/dim]")
        history_ctx = _format_history(self._history) if self._history else ""
        prompt = "\n".join([
            "You are editing a personal knowledge vault note. Improve the content by:",
            "- Fixing any factual errors",
            "- Adding missing information revealed in the conversation history",
            "- Improving clarity and structure",
            "- Preserving existing YAML frontmatter exactly",
            "",
            *(["--- CONVERSATION HISTORY ---", history_ctx, "--- END ---", ""] if history_ctx else []),
            "--- FILE ---",
            original,
            "--- END FILE ---",
            "",
            "Return ONLY the complete updated file content. No explanation, no fences.",
        ])
        self._set_status("✏️ Generating edits…")
        proposed = await self._stream_llm(prompt, model=coding_llm, log_result=False)

        diff_lines = list(difflib.unified_diff(
            original.splitlines(keepends=True),
            proposed.splitlines(keepends=True),
            fromfile=f"{rel} (current)",
            tofile=f"{rel} (proposed)",
            n=3,
        ))
        if not diff_lines:
            self._log("[dim]No changes proposed.[/dim]")
            return

        self._log_md("```diff\n" + "".join(diff_lines) + "\n```")
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

        try:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(proposed)
            self._log(f"[green]✓  Saved edits to {rel}[/green]")
            if self._open_file and self._open_file.path == target_path:
                self._open_file = OpenFile(path=target_path, rel=rel, content=proposed)
                self._update_subtitle()
        except OSError as e:
            self._log(f"[red]Write failed: {e}[/red]")

    @work
    async def _cmd_daily(self, _args: str = "") -> None:
        today      = datetime.now().strftime("%Y-%m-%d")
        log_path   = os.path.join(CONVERSATIONS_DIR, f"{today}.md")
        if not os.path.exists(log_path):
            self._log(f"[dim]No conversation log for today ({today}).[/dim]")
            return
        try:
            with open(log_path, encoding="utf-8") as f:
                combined = f.read()
        except OSError:
            self._log("[red]Could not read today's conversation log.[/red]")
            return

        n_sessions = len(re.findall(r'^## Session —', combined, re.MULTILINE))
        self._log(f"[dim]📅  Summarising {n_sessions} session(s) from {today}…[/dim]")
        summary_prompt = (
            f"Summarise what was discussed across these {n_sessions} chat sessions "
            f"from {today}. Be concise. Cover: key topics, questions answered, notes saved.\n\n"
            f"{combined[:4000]}\n\nSummary:"
        )
        self._log(f"[bold]📅  Daily summary — {today}[/bold]")
        self._set_status("📅 Summarising sessions…")
        summary = await self._stream_llm(summary_prompt, model=coding_llm)

        daily_path = os.path.join(CONVERSATIONS_DIR, f"{today}_daily.md")
        if os.path.exists(daily_path):
            self._log(f"[dim]Daily note already saved for {today}. Run again tomorrow or delete {os.path.basename(daily_path)} to regenerate.[/dim]")
            return
        if not os.path.exists(daily_path):
            self._log("[dim]Save as daily note? Type [bold]yes[/bold] or anything else to skip.[/dim]")
            inp = self.query_one(Input)
            inp.placeholder = "yes / no…"
            self._apply_queue = asyncio.Queue()
            try:
                resp = (await self._apply_queue.get()).strip().lower()
            finally:
                self._apply_queue = None
                inp.placeholder = "Ask anything, or type /help for commands..."
            if resp == "yes":
                with open(daily_path, "w", encoding="utf-8") as f:
                    f.write(f"# Daily Summary — {today}\n\n{summary}\n")
                self._log(f"[dim]📅  Saved to {os.path.relpath(daily_path, VAULT_PATH)}[/dim]")

    @work
    async def _cmd_export(self, args: str = "") -> None:
        import json as _json
        fmt = args.strip().lower() or "jsonl"
        if fmt not in ("jsonl", "alpaca", "csv"):
            self._log(f"[yellow]Unknown format '{fmt}'. Use: jsonl (default), alpaca, csv[/yellow]")
            return

        pairs: list[dict] = []

        # Q&A blocks saved by /savefile
        for path in glob.glob(os.path.join(VAULT_PATH, "*.md")):
            try:
                with open(path, encoding="utf-8") as f:
                    content = f.read()
            except OSError:
                continue
            for q, a in re.findall(
                r'## Q: (.+?)\n(?:.*?\n)?\n(.*?)(?=\n## Q:|\Z)', content, re.DOTALL
            ):
                if q.strip() and a.strip():
                    pairs.append({"instruction": q.strip(), "response": a.strip()})

        # High-quality exchanges from recent session logs
        conv_files = sorted(glob.glob(os.path.join(CONVERSATIONS_DIR, "*.md")))[-20:]
        for path in conv_files:
            try:
                with open(path, encoding="utf-8") as f:
                    content = f.read()
            except OSError:
                continue
            sections = re.split(r'^## \[\d+:\d+\] (User|Assistant)\s*$', content, flags=re.MULTILINE)
            role, last_q = None, ""
            for part in sections:
                part = part.strip()
                if part in ("User", "Assistant"):
                    role = part
                elif role == "User" and part and not part.startswith("/"):
                    last_q = part
                elif role == "Assistant" and last_q and len(part) > 80:
                    pairs.append({"instruction": last_q, "response": part})
                    last_q = ""

        if not pairs:
            self._log("[dim]No Q&A pairs found to export.[/dim]")
            return

        ext      = "jsonl" if fmt == "jsonl" else fmt
        out_path = os.path.join(VAULT_PATH, f"training_data.{ext}")
        with open(out_path, "w", encoding="utf-8") as f:
            if fmt == "jsonl":
                for p in pairs:
                    f.write(_json.dumps({"instruction": p["instruction"], "output": p["response"]}) + "\n")
            elif fmt == "alpaca":
                _json.dump(
                    [{"instruction": p["instruction"], "input": "", "output": p["response"]} for p in pairs],
                    f, indent=2, ensure_ascii=False,
                )
            elif fmt == "csv":
                f.write("instruction,response\n")
                for p in pairs:
                    q = p["instruction"].replace('"', '""')
                    a = p["response"].replace('"', '""')
                    f.write(f'"{q}","{a}"\n')

        rel = os.path.relpath(out_path, VAULT_PATH)
        self._log(f"[green]✓  Exported {len(pairs)} Q&A pairs → {rel}[/green]  [dim]({fmt.upper()} — unsloth / axolotl / llama.cpp)[/dim]")

    def _cmd_stats(self) -> None:
        self._cmd_status()

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
        for m in re.finditer(r'\b(_\w+)\b', instruction):
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
        result = await asyncio.to_thread(lambda: coding_llm.invoke(prompt).content.strip())
        
        review_prompt = "\n".join([
            f"Review the following proposed method code:",
            result,
            "",
            "Check for the following issues:",
            "- Wrong variable names (VAULT_PATH/CONVERSATIONS_DIR/llm/coding_llm are module-level, not self.xxx)",
            "- Missing @work decorator for async ops",
            "- Logic errors",
            "- Off-by-one errors",
            "- Incorrect regex escapes",
            "",
            "Return the reviewed method code if it differs from the original. Otherwise, return an empty string.",
        ])
        
        reviewed = await asyncio.to_thread(lambda: coding_llm.invoke(review_prompt).content.strip())
        
        return reviewed or result

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
        force = _args.strip().lower() in ("--force", "force", "-f")
        self._set_busy(True, "Ingesting vault…")
        self._log(f"[dim]📚 {'Rebuilding' if force else 'Updating'} vault…[/dim]", save=False)
        old_db = self.db
        if self.db:
            self.db._client.close()
        self.db = None
        try:
            new_db, stats = await asyncio.to_thread(ingest_vault, force)
            self.db = new_db
            n       = new_db._collection.count()
            if stats["updated"] == 0 and stats["removed"] == 0 and stats["unchanged"] == 0:
                msg = f"✅ Ingested {n} chunks."
            else:
                parts = []
                if stats["new"]:       parts.append(f"{stats['new']} new")
                if stats["updated"]:   parts.append(f"{stats['updated']} updated")
                if stats["removed"]:   parts.append(f"{stats['removed']} removed")
                if stats["unchanged"]: parts.append(f"{stats['unchanged']} unchanged")
                msg = f"✅ {n} chunks — {', '.join(parts)}."
            self._log(f"[dim]{msg}[/dim]")
            self._note_event(f"ingested:{n} chunks")
        except Exception as e:
            self._log(f"[red]Ingest failed: {e}[/red]")
            self.db = old_db
        finally:
            self._set_busy(False)
            self.query_one(Input).focus()

    # ── /organize command ─────────────────────────────────────────────────────

    @work
    async def _cmd_organize(self, _args: str = "") -> None:
        self._organize_queue = asyncio.Queue()
        inp = self.query_one(Input)
        inp.placeholder = "Enter=accept · skip · edit · all · none"

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

    # ── Review panel (left dock) ────────────────────────────────────────────────

    _REVIEW_ICONS = {"pending": "○", "accepted": "✓", "skipped": "⏭", "edited": "✎"}

    def _review_row_text(self, proposal: Proposal, status: str) -> str:
        icon = self._REVIEW_ICONS[status]
        return f"{icon}  [{proposal.kind}] {proposal.label}"

    def _review_panel_show(self, proposals: list[Proposal]) -> None:
        panel  = self.query_one("#review-panel")
        header = self.query_one("#review-panel-header", Label)
        lv     = self.query_one("#review-list", ListView)
        header.update(f"[bold]Reviewing {len(proposals)} item(s)[/bold]")
        lv.clear()
        for i, proposal in enumerate(proposals):
            # markup=False: proposal.kind/label are arbitrary strings (e.g. a bare
            # "[tags]" or "[[wikilink]]" substring reads as an invalid Rich style
            # tag to the markup parser and crashes Static.update on paint).
            row = Label(self._review_row_text(proposal, "pending"), id=f"ri-label-{i}", markup=False)
            lv.append(ListItem(row, id=f"ri-{i}"))
        panel.display = True

    def _review_panel_set_status(self, index: int, proposal: Proposal, status: str) -> None:
        try:
            self.query_one(f"#ri-label-{index}", Label).update(self._review_row_text(proposal, status))
        except Exception:
            pass

    def _review_panel_set_detail(self, proposal: Proposal) -> None:
        try:
            self.query_one("#review-list", ListView).index = self._review_active_index
        except Exception:
            pass
        # Built with Text.append(), never Text.from_markup(): proposal.label/detail/
        # proposed are arbitrary file/LLM-generated content (wikilink targets, full
        # article bodies for /distill, ...) and must never be parsed as Rich markup.
        text = Text()
        text.append(proposal.label, style="bold #5f87af")
        text.append(f"  ({proposal.kind})", style="dim")
        text.append("\n\n")
        if proposal.detail:
            text.append(proposal.detail)
            text.append("\n\n")
        text.append("Proposed:\n", style="dim")
        text.append(proposal.proposed)
        self.query_one("#review-detail", Static).update(text)

    def _review_panel_hide(self) -> None:
        self.query_one("#review-panel").display = False
        self.query_one("#review-list", ListView).clear()
        self.query_one("#review-detail", Static).update("")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if self._review_proposals is None or self._review_active_index is None:
            return
        idx = event.list_view.index
        if idx != self._review_active_index or self._organize_queue is None:
            return
        if isinstance(self.screen, (ProposalEditScreen, FileBrowserScreen)):
            return
        self._organize_queue.put_nowait("edit")

    async def _review(self, proposals: list[Proposal]) -> None:
        """Walk the user through a batch of Proposals one at a time.

        Enter=accept as proposed · skip=leave unchanged · edit=open an editor
        pre-filled with the proposed value (or click the active row in the
        review panel) · all=accept this and every remaining proposal ·
        none=skip this and every remaining proposal. An edit that changes
        the substance of the proposed value is logged to organize_feedback.md
        (with an optional one-line reason) so future suggestions can learn
        from it; edits that just restore the proposed value are applied
        silently. The left-hand review panel mirrors the whole batch —
        status icons update live as each item is decided.
        """
        if not proposals:
            return

        created_queue = self._organize_queue is None
        if created_queue:
            self._organize_queue = asyncio.Queue()
        inp = self.query_one(Input)
        prior_placeholder = inp.placeholder
        inp.placeholder = "Enter=accept · skip · edit · all · none"

        self._review_proposals = proposals
        self._review_panel_show(proposals)

        try:
            accept_rest = False
            skip_rest   = False
            for index, proposal in enumerate(proposals):
                self._log(f"\n[bold #5f87af]{rich_escape(proposal.label)}[/bold #5f87af]  [dim]({proposal.kind})[/dim]")
                if proposal.detail:
                    # escape: detail may embed arbitrary file/LLM content (wikilink
                    # stems, article text); unescaped, a bare "[[word]]" reads as an
                    # (invalid) Rich style tag and silently eats its own contents.
                    self._log(f"  {rich_escape(proposal.detail)}")

                self._review_active_index = index
                self._review_panel_set_detail(proposal)

                if skip_rest:
                    self._review_panel_set_status(index, proposal, "skipped")
                    continue
                if accept_rest:
                    proposal.apply(proposal.proposed)
                    self._review_panel_set_status(index, proposal, "accepted")
                    self._log("  [green]✓ Applied.[/green]")
                    continue

                raw = await self._org_prompt(
                    "  Enter=accept  ·  skip  ·  edit  ·  all=accept rest  ·  none=skip rest:"
                )
                cmd = raw.strip().lower()

                if cmd == "none":
                    skip_rest = True
                    self._review_panel_set_status(index, proposal, "skipped")
                    continue
                if cmd == "skip":
                    self._review_panel_set_status(index, proposal, "skipped")
                    continue
                if cmd == "all":
                    proposal.apply(proposal.proposed)
                    accept_rest = True
                    self._review_panel_set_status(index, proposal, "accepted")
                    self._log("  [green]✓ Applied.[/green]")
                    continue
                if cmd == "edit":
                    final = await self.push_screen_wait(ProposalEditScreen(proposal.label, proposal.proposed))
                    self.query_one(Input).focus()
                    if final is None:
                        self._review_panel_set_status(index, proposal, "skipped")
                        continue
                    if final.strip() != proposal.proposed.strip():
                        reason = await self._org_prompt("  Why the change? (optional, Enter to skip):")
                        _log_organize_feedback(proposal.kind, proposal.path, proposal.proposed, final, reason)
                    proposal.apply(final)
                    self._review_panel_set_status(index, proposal, "edited")
                    self._log("  [green]✓ Applied (edited).[/green]")
                    continue

                # Enter (empty input) → accept as proposed
                proposal.apply(proposal.proposed)
                self._review_panel_set_status(index, proposal, "accepted")
                self._log("  [green]✓ Applied.[/green]")
        finally:
            if created_queue:
                self._organize_queue = None
            inp.placeholder = prior_placeholder
            self._review_active_index = None
            self._review_proposals = None
            self._review_panel_hide()

    async def _run_organize(self) -> None:
        # ── Pass 0: Rebuild conversation index ────────────────────────────────
        self._log("[dim]Finalising open sessions and rebuilding conversation index…[/dim]")
        n_idx = await asyncio.to_thread(_rebuild_conversation_index, CONVERSATIONS_DIR)
        self._log(f"[dim]📋  Index rebuilt — {n_idx} session(s).[/dim]")

        md_files = _discover_vault_files()
        if not md_files:
            self._log("[red]No .md files found in vault.[/red]")
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
        tag_feedback = _load_organize_feedback("tags")
        tag_prompt = (
            (f"{tag_feedback}\n\n" if tag_feedback else "") +
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

        def _make_tag_apply(stem: str, path: str):
            def _apply(final_tags_str: str) -> None:
                final       = [t.strip() for t in final_tags_str.split(",") if t.strip()]
                frontmatter = "---\ntags:\n" + "".join(f"  - {t}\n" for t in final) + "---\n"
                new_content = frontmatter + notes[stem]["content"]
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                notes[stem]["content"] = new_content
            return _apply

        tag_proposals: list[Proposal] = []
        for stem, data in notes.items():
            if data["content"].lstrip().startswith("---"):
                self._log(f"[dim]⏭  {stem}.md — already has frontmatter[/dim]")
                continue
            suggested = tag_map.get(stem)
            if not suggested:
                continue
            tag_proposals.append(Proposal(
                kind="tags", path=data["path"], label=f"{stem}.md",
                detail=f"Suggested tags: {', '.join(suggested)}",
                proposed=", ".join(suggested),
                apply=_make_tag_apply(stem, data["path"]),
            ))

        await self._review(tag_proposals)

        # ── Pass 2: Wikilinks ─────────────────────────────────────────────────

        self._log("\n[bold]Scanning for wikilink opportunities…[/bold]")

        def _parse_link_subs(raw: str, content: str) -> list[tuple[str, str]]:
            subs: list[tuple[str, str]] = []
            for line in raw.splitlines():
                if "->" not in line:
                    continue
                phrase_part, target_part = line.split("->", 1)
                phrase = phrase_part.strip().strip('"').strip("'")
                target = target_part.strip().strip('"').strip("'")
                if target in notes and phrase and phrase in content:
                    subs.append((phrase, target))
            return subs

        def _make_link_apply(stem: str, path: str, content_at_prompt: str):
            def _apply(final_text: str) -> None:
                subs = _parse_link_subs(final_text, content_at_prompt)
                if not subs:
                    return
                content  = notes[stem]["content"]
                fm_end   = (content.find("---", content.index("---") + 3) + 3) if content.lstrip().startswith("---") else 0
                fm_block = content[:fm_end]
                body     = content[fm_end:]
                for phrase, target in subs:
                    title_t = notes[target]["title"]
                    link    = f"[[{target}]]" if phrase.lower() in (target.lower(), title_t.lower()) else f"[[{target}|{phrase}]]"
                    body    = body.replace(phrase, link, 1)
                new_content = fm_block + body
                if new_content != content:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    notes[stem]["content"] = new_content
            return _apply

        link_feedback  = _load_organize_feedback("wikilink")
        link_proposals: list[Proposal] = []
        for stem, data in notes.items():
            content     = data["content"]
            other_notes = {s: d["title"] for s, d in notes.items() if s != stem}
            if not other_notes:
                continue

            link_prompt = (
                (f"{link_feedback}\n\n" if link_feedback else "") +
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

            subs = _parse_link_subs(raw, content)
            if not subs:
                continue

            link_proposals.append(Proposal(
                kind="wikilink", path=data["path"], label=f"{stem}.md",
                detail="\n".join(f"  '{phrase}'  →  [[{target}]]" for phrase, target in subs),
                proposed="\n".join(f'"{phrase}" -> {target}' for phrase, target in subs),
                apply=_make_link_apply(stem, data["path"], content),
            ))

        await self._review(link_proposals)

        # ── Pass 3: Condense short conversation sessions ──────────────────────────
        self._log("\n[bold]Checking conversation logs for short/command-only sessions…[/bold]")
        conv_files = sorted(glob.glob(os.path.join(CONVERSATIONS_DIR, "*.md")))
        to_condense: list[tuple[str, str]] = []
        for conv_path in conv_files:
            if os.path.basename(conv_path) == "INDEX.md":
                continue
            try:
                with open(conv_path, encoding="utf-8") as fh:
                    conv_content = fh.read()
            except OSError:
                continue
            user_msgs = re.findall(r'^## \[\d+:\d+\] User\s*$', conv_content, re.MULTILINE)
            cmd_msgs  = re.findall(r'^/\w+', conv_content, re.MULTILINE)
            if len(user_msgs) <= 3 and len(conv_content) < 3000:
                to_condense.append((conv_path, conv_content))

        if not to_condense:
            self._log("[dim]No short sessions found.[/dim]")
        else:
            self._log(f"[dim]Found {len(to_condense)} short session(s).[/dim]")
            for conv_path, conv_content in to_condense:
                basename = os.path.basename(conv_path)
                preview  = conv_content.replace("\n", " ")[:120]
                self._log(f"\n[bold #5f87af]{basename}[/bold #5f87af]")
                self._log(f"  [dim]{preview}…[/dim]")
                raw = await self._org_prompt("  Enter=condense  ·  skip=keep:")
                if raw.lower() == "skip":
                    continue
                summary_prompt = (
                    "Summarise this chat session in 1-2 lines. "
                    "Focus on what was accomplished.\n\n"
                    f"{conv_content[:1500]}\n\nSummary:"
                )
                summary = await asyncio.to_thread(
                    lambda p=summary_prompt: coding_llm.invoke(p).content.strip()
                )
                ts_m = re.search(r'# Chat Session — (.+)', conv_content)
                ts   = ts_m.group(1).strip() if ts_m else basename
                with open(conv_path, "w", encoding="utf-8") as fh:
                    fh.write(f"# Chat Session — {ts}\n\n*[condensed by /organize]*\n\n{summary}\n")
                self._log("  [green]✓ Condensed.[/green]")

        # ── Pass 4: File placement ────────────────────────────────────────────
        self._log("\n[bold]Analysing file placements…[/bold]")
        to_place = [
            (path, data["content"], _extract_frontmatter_tags(data["content"]))
            for path, data in [(p, notes[os.path.splitext(os.path.basename(p))[0]])
                               for p in md_files if _needs_placement(p)
                               and os.path.splitext(os.path.basename(p))[0] in notes]
        ]

        def _is_ref(fname: str) -> bool:
            return fname.lower().startswith("_ref")

        moved = [0]  # mutable cell so the closure can report back after _review

        def _make_placement_apply(path: str, fname: str):
            def _apply(final_folder: str) -> None:
                folder     = final_folder.strip() or "misc"
                subdir     = "_ref" if _is_ref(fname) else ""
                target_dir = os.path.join(VAULT_PATH, folder, subdir) if subdir else os.path.join(VAULT_PATH, folder)
                os.makedirs(target_dir, exist_ok=True)
                target_path = os.path.join(target_dir, fname)
                if os.path.abspath(path) != os.path.abspath(target_path):
                    shutil.move(path, target_path)
                    moved[0] += 1
            return _apply

        if not to_place:
            self._log("[dim]All files already placed.[/dim]")
        else:
            self._log(f"[dim]Classifying {len(to_place)} unplaced file(s)…[/dim]")
            placement_proposals: list[Proposal] = []
            for path, content, tags in to_place:
                fname  = os.path.basename(path)
                folder = await asyncio.to_thread(_classify_for_placement, tags, content, coding_llm)
                subdir = "_ref/" if _is_ref(fname) else ""
                placement_proposals.append(Proposal(
                    kind="placement", path=path, label=fname,
                    detail=f"→  {folder}/{subdir}",
                    proposed=folder,
                    apply=_make_placement_apply(path, fname),
                ))

            await self._review(placement_proposals)
            if moved[0]:
                self._log(f"  [dim]{moved[0]} file(s) moved. Rebuilding vault index…[/dim]")
                new_db, stats = await asyncio.to_thread(ingest_vault, True)
                self.db = new_db
                n       = new_db._collection.count()
                self._log(f"[dim]✅ {n} chunks re-indexed.[/dim]")

        # ── Pass 5: Wikilink validation ────────────────────────────────────────
        self._log("\n[bold]Checking existing wikilinks for stale targets…[/bold]")
        proposed_fixes = await asyncio.to_thread(_validate_wikilinks, True)

        def _make_wikilink_fix_apply(path: str):
            def _apply(_final: str) -> None:
                _validate_wikilinks(dry_run=False, only_path=path)
            return _apply

        if not proposed_fixes:
            self._log("[dim]No stale wikilinks found.[/dim]")
        else:
            total = sum(len(v) for v in proposed_fixes.values())
            self._log(f"[dim]Found {total} stale wikilink(s) across {len(proposed_fixes)} file(s).[/dim]")
            wf_proposals = [
                Proposal(
                    kind="wikilink_fix", path=path, label=os.path.relpath(path, VAULT_PATH),
                    detail="\n".join(f"  [[{old}]]  →  [[{new}]]" for old, new in file_fixes),
                    proposed=", ".join(f"{old}->{new}" for old, new in file_fixes),
                    apply=_make_wikilink_fix_apply(path),
                )
                for path, file_fixes in proposed_fixes.items()
            ]
            await self._review(wf_proposals)

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

        is_class_q, topic = _detect_class_question(question)
        depth = _depth_hint(topic) if is_class_q else ""

        file_ctx = ""
        if self._open_file:
            file_ctx = f"File: {self._open_file.rel}\n\n{self._open_file.content}"
            self._log(f"[dim]📄  Context: {self._open_file.rel}[/dim]")

        try:
            if self.db is None:
                self._log("[red]No database — run /ingest first.[/red]")
                return

            # ── Vault retrieval with tag-aware second pass ─────────────────────
            self._set_status("🔍 Searching vault…")
            results   = await asyncio.to_thread(
                lambda: self.db.similarity_search_with_relevance_scores(question, k=TOP_K)
            )
            chunks    = [doc for doc, _ in results]
            top_score = max((s for _, s in results), default=0.0)

            if results:
                active_tags = _get_chunk_tags(results[0][0])
                if active_tags:
                    # Tag filter already narrows to one topic, so widen k here —
                    # otherwise a 12+ file topic cluster still only surfaces 5 of them.
                    filtered = await asyncio.to_thread(
                        lambda: self.db.similarity_search_with_relevance_scores(
                            question, k=TOP_K * 2, filter=_make_tag_filter(active_tags)
                        )
                    )
                    filtered_top = max((s for _, s in filtered), default=0.0)
                    if filtered_top >= top_score * 0.9:
                        chunks    = [doc for doc, _ in filtered]
                        top_score = filtered_top
                        self._log(f"[dim]🏷  Scoped to: {', '.join(active_tags)}[/dim]", save=False)
                        self._note_event(f"tags:{','.join(active_tags)}")

            self._log(f"[dim]🔍  Best vault match: {top_score:.2f}[/dim]", save=False)
            self._note_event(f"score:{top_score:.2f}")

            if top_score >= SIMILARITY_THRESHOLD:
                sources = sorted({
                    os.path.relpath(d.metadata["source"], VAULT_PATH)
                    for d in chunks if d.metadata.get("source")
                })
                self._log(f"[dim]📓  Source: {', '.join(sources[:3]) if sources else 'vault notes'}[/dim]", save=False)
                self._note_event(f"src:{sources[0] if sources else 'vault'}")
                if is_class_q:
                    self._log("[dim]📖  Class question — deep mode[/dim]", save=False)
                self._set_status("✍ Generating from vault…")
                answer = await self._stream_llm(build_vault_prompt(question, chunks, self._history[:-1], file_ctx, depth))
                self._history.append({"role": "assistant", "content": answer})
                self._append_to_session("assistant", answer)
                # Auto-supplement with web if vault source doesn't directly cover the topic
                if is_class_q and self._web_on and not _source_covers_topic(sources, topic):
                    self._log("[dim]🌐  Vault coverage indirect — supplementing with web…[/dim]", save=False)
                    try:
                        web_ctx = await asyncio.wait_for(asyncio.to_thread(lambda: web_search(question)), timeout=20)
                    except asyncio.CancelledError:
                        self._log("[dim]🌐  Web search timed out[/dim]", save=False)
                        raise
                    except Exception as e:
                        web_ctx = f"Web search failed: {e}"
                        self._log(f"[dim]🌐  Web search failed: {e}[/dim]", save=False)
                    if not web_ctx.startswith(("No results", "Web search failed", "duckduckgo")):
                        self._note_event("web:supplement")
                        self._set_status("✍ Generating from web…")
                        web_answer = await self._stream_llm(build_web_prompt(question, web_ctx, self._history))
                        self._queue_note(question, web_answer, "web supplement", topic)
                return

            # ── Vault-grounded response (below threshold but chunks exist) ────────
            if chunks:
                sources = sorted({
                    os.path.relpath(d.metadata["source"], VAULT_PATH)
                    for d in chunks if d.metadata.get("source")
                })
                self._log(f"[dim]🧠  Low vault match ({top_score:.2f}) — using as context: {', '.join(sources[:3])}[/dim]", save=False)
                self._note_event("src:grounded")
                if is_class_q:
                    self._log("[dim]📖  Class question — deep mode[/dim]", save=False)
                self._set_status("✍ Generating…")
                model_answer = await self._stream_llm(build_grounded_prompt(question, chunks, self._history[:-1], file_ctx, depth))
                self._history.append({"role": "assistant", "content": model_answer})
                self._append_to_session("assistant", model_answer)
                return

            # ── Pure model knowledge (no vault chunks at all) ──────────────────
            self._log("[dim]🧠  No vault context — asking model[/dim]", save=False)
            self._note_event("src:model")
            if is_class_q:
                self._log("[dim]📖  Class question — deep mode[/dim]", save=False)
            self._set_status("✍ Generating…")
            model_answer = await self._stream_llm(build_knowledge_prompt(question, self._history[:-1], file_ctx, depth))
            uncertain = model_answer.strip().lower().startswith(_UNCERTAIN_PREFIX)
            self._log(f"[dim]🧠  Model knowledge{'  (uncertain)' if uncertain else ''}[/dim]", save=False)
            if uncertain:
                self._note_event("uncertain")
            self._history.append({"role": "assistant", "content": model_answer})
            self._append_to_session("assistant", model_answer)

            suggestion = await asyncio.to_thread(lambda: get_concept_suggestion(question, model_answer))
            self._queue_note(question, model_answer, "model knowledge" + (" (uncertain)" if uncertain else ""), suggestion)

            # ── Web search supplement (model-knowledge path = vault didn't cover it) ──
            if self._web_on:
                self._set_status("🌐 Searching web…")
                self._log("[dim]🌐  Supplementing with web search…[/dim]", save=False)
                try:
                    web_ctx = await asyncio.wait_for(asyncio.to_thread(lambda: web_search(question)), timeout=20)
                except asyncio.CancelledError:
                    self._log("[dim]🌐  Web search timed out[/dim]", save=False)
                    raise
                except Exception as e:
                    web_ctx = f"Web search failed: {e}"
                    self._log(f"[dim]🌐  Web search failed: {e}[/dim]", save=False)

                if not web_ctx.startswith(("No results", "Web search failed", "duckduckgo")):
                    self._log("[dim]🌐  Web result:[/dim]", save=False)
                    self._note_event("web:yes")
                    self._set_status("✍ Generating from web…")
                    web_answer = await self._stream_llm(build_web_prompt(question, web_ctx, self._history))
                    web_suggestion = await asyncio.to_thread(lambda: get_concept_suggestion(question, web_answer))
                    self._queue_note(question, web_answer, "web search", web_suggestion)
                else:
                    self._log("[dim]🌐  No web results.[/dim]", save=False)
                    self._note_event("web:none")

        finally:
            self._set_busy(False)
            self.query_one(Input).focus()

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_clear_input(self) -> None:
        self.query_one(Input).value = ""

    def action_quit(self) -> None:
        self.exit()


# ── Entry point ───────────────────────────────────────────────────────────────

def _acquire_instance_lock() -> None:
    import atexit
    if os.path.exists(_PID_FILE):
        try:
            pid = int(open(_PID_FILE).read().strip())
            os.kill(pid, 0)
            print(f"ChatUI is already running (PID {pid}). Stop it first or remove {_PID_FILE}.")
            sys.exit(1)
        except (ProcessLookupError, ValueError, OSError):
            pass  # stale PID file — safe to overwrite
    with open(_PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    atexit.register(lambda: os.path.exists(_PID_FILE) and os.unlink(_PID_FILE))


if __name__ == "__main__":
    import argparse as _argparse
    _acquire_instance_lock()
    _parser = _argparse.ArgumentParser(description="ChatUI — local vault RAG assistant")
    _parser.add_argument("--vault", metavar="PATH", help="Vault path (overrides config/settings.md)")
    _args = _parser.parse_args()
    if _args.vault:
        VAULT_PATH = os.path.abspath(_args.vault)
    ChatApp(load_existing_db()).run()
