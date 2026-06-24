"""
obsidian_brain.py
-----------------
A local RAG (Retrieval-Augmented Generation) tool that lets you query your
Obsidian vault using a locally-running LLM via Ollama, presented as a
full-screen terminal UI.

How it works:
  1. INGEST   — Reads files matching FILE_GLOB, splits them into chunks, and
                stores vector embeddings in a local ChromaDB database on disk.
  2. RETRIEVE — When you ask a question, it finds the most relevant chunks
                using semantic similarity search.
  3. JUDGE    — The LLM checks whether those chunks actually answer the question.
  4. GENERATE — Answers from the best available source, in order of preference:
                  a) Vault notes      (if the judge says context is sufficient)
                  b) Model knowledge  (if the vault comes up short)
                  c) DuckDuckGo web search  (if the model is also uncertain)
  5. LEARN    — If the answer came from model knowledge or web search, the
                response is saved to a concept note in the vault so future
                questions can be answered from the vault. The live ChromaDB
                is updated immediately so re-ingestion isn't needed.

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

# Where your Obsidian vault (or any folder of .md files) lives.
VAULT_PATH = "/home/tizz/dev/LLM-sandbox/"

# Where the vector database will be saved on disk.
# This persists between runs so you don't have to re-ingest every time.
DB_PATH = "/home/tizz/dev/LLM-sandbox/local_db"

# Ollama model names. Must match what you have pulled locally.
EMBED_MODEL = "nomic-embed-text"  # used to turn text into vectors
CHAT_MODEL  = "llama3.2:3b"       # used to generate answers

# Which files to ingest from the vault. Supports glob patterns.
# "**/*.md" = markdown only (default). Use "**/*.*" to ingest everything.
FILE_GLOB = "**/*.md"

# Retrieval settings
TOP_K = 3  # how many note chunks to pull in as context per query

# Web search settings
WEB_SEARCH_RESULTS = 3  # how many DuckDuckGo results to pull in as context

# Chunking settings (affects retrieval quality — tweak if answers feel off)
CHUNK_SIZE    = 500   # max characters per chunk
CHUNK_OVERLAP = 50    # overlap between chunks to preserve context at boundaries


# ── Model Setup ───────────────────────────────────────────────────────────────
# These are lazy — Ollama doesn't actually connect until you call them.

embeddings = OllamaEmbeddings(model=EMBED_MODEL)
llm        = ChatOllama(model=CHAT_MODEL)


# ── Ingestion ─────────────────────────────────────────────────────────────────

def ingest_vault() -> Chroma:
    """
    Load files matching FILE_GLOB from VAULT_PATH, split them into chunks, embed them,
    and store the result in a ChromaDB database at DB_PATH.

    This overwrites any existing database, so re-running it is safe — it just
    rebuilds from scratch. Call this whenever your notes change significantly.

    Returns the loaded Chroma vector store, ready for querying.
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
    Load an already-ingested ChromaDB database from disk without re-reading
    your vault. Much faster than ingest_vault() for day-to-day use.

    Raises FileNotFoundError if the database doesn't exist yet.
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"No database found at '{DB_PATH}'.\n"
            "Run the script with --ingest first to build it."
        )

    print(f"📂 Loading existing database from: {DB_PATH}\n")
    return Chroma(persist_directory=DB_PATH, embedding_function=embeddings)


# ── Fallback: Web Search ───────────────────────────────────────────────────────

def web_search(query: str) -> str:
    """
    Search DuckDuckGo for the query and return a plain-text summary of the
    top results. No API key required.

    Returns a formatted string of results, or an error message if the search
    fails (e.g. no network connection).
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=WEB_SEARCH_RESULTS))

        if not results:
            return "No results found."

        formatted = []
        for r in results:
            formatted.append(f"Source: {r['href']}\nTitle: {r['title']}\n{r['body']}")

        return "\n\n---\n\n".join(formatted)

    except Exception as e:
        return f"Web search failed: {e}"


# ── Learning: Save responses to vault ─────────────────────────────────────────

def get_concept_suggestion(question: str, answer: str) -> str:
    """
    Ask the LLM to identify the single core concept from a question/answer pair
    and return a sanitised filename stem (e.g. "cupcakes").
    """
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
    Save a question/answer pair to the appropriate concept note in the vault,
    then add it to the live ChromaDB so it's immediately searchable without
    needing a full re-ingest.

    Args:
        concept:  The sanitised filename stem chosen by the user (e.g. "cupcakes").
        question: The original user question.
        answer:   The generated answer.
        source:   Where the answer came from ("model knowledge" or "web search").
        db:       The live Chroma instance to update in place.
    """
    filename  = f"{concept}.md"
    filepath  = os.path.join(VAULT_PATH, filename)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    entry = f"""
## Q: {question}
*Source: {source} — {timestamp}*

{answer}
"""

    if os.path.exists(filepath):
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(entry)
    else:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {concept.replace('-', ' ').title()}\n")
            f.write(entry)

    new_doc = Document(
        page_content=f"Q: {question}\n\n{answer}",
        metadata={"source": filepath},
    )
    db.add_documents([new_doc])


# ── Retrieval + Generation ─────────────────────────────────────────────────────

def build_vault_prompt(question: str, context_chunks: list) -> str:
    """Prompt for answering from vault context."""
    context_text = "\n\n---\n\n".join(chunk.page_content for chunk in context_chunks)

    return f"""You are a helpful assistant with access to the user's personal notes.
Use only the context provided below to answer the question.
If the answer isn't covered in the context, say so clearly — don't guess.

--- CONTEXT FROM NOTES ---
{context_text}
--- END CONTEXT ---

Question: {question}
Answer:"""


def build_knowledge_prompt(question: str) -> str:
    """Prompt for answering from the model's own training knowledge."""
    return f"""Answer the following question using your own knowledge.
If you are not confident in your answer or the information may be outdated,
start your response with the exact phrase: "I'm not certain, but"

Question: {question}
Answer:"""


def build_web_prompt(question: str, web_context: str) -> str:
    """Prompt for answering from web search results."""
    return f"""Answer the following question using the web search results below.
Summarise the relevant information clearly and cite the sources where helpful.

--- WEB SEARCH RESULTS ---
{web_context}
--- END RESULTS ---

Question: {question}
Answer:"""


def context_is_sufficient(question: str, context_chunks: list) -> bool:
    """
    Ask the LLM whether the retrieved vault chunks contain enough information
    to answer the question. Returns True if yes, False if not.
    """
    context_text = "\n\n---\n\n".join(chunk.page_content for chunk in context_chunks)

    judge_prompt = f"""You are evaluating whether a set of notes contains enough
information to answer a question. Reply with only YES or NO.

--- NOTES ---
{context_text}
--- END NOTES ---

Question: {question}
Do these notes contain enough information to answer this question? (YES or NO):"""

    response = llm.invoke(judge_prompt).content.strip().upper()
    return response.startswith("YES")


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


# ── Filename Modal ─────────────────────────────────────────────────────────────

class FilenameModal(ModalScreen[str]):
    """
    Overlay that shows the model's suggested note filename and lets the user
    confirm it or type their own before the note is written to disk.
    """

    CSS = """
    FilenameModal {
        align: center middle;
    }

    #modal-box {
        width: 64;
        height: auto;
        border: thick #5f87af;
        background: #252526;
        padding: 1 2;
    }

    #modal-box Label {
        color: #d4d4d4;
        margin-bottom: 1;
    }

    #modal-box Input {
        margin: 1 0 0 0;
        background: #1e1e1e;
        color: #d4d4d4;
        border: tall #454545;
    }

    #modal-box Input:focus {
        border: tall #5f87af;
    }
    """

    BINDINGS = [Binding("escape", "use_suggestion", "Use suggestion", show=True)]

    def __init__(self, suggestion: str) -> None:
        super().__init__()
        self.suggestion = suggestion

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-box"):
            yield Label("[bold]Save note as[/bold]")
            yield Label(
                f"Suggestion: [bold #5f87af]{self.suggestion}.md[/bold #5f87af]"
            )
            yield Input(placeholder=self.suggestion, id="filename-input")
            yield Label("[dim]Enter to confirm  ·  Esc to use suggestion[/dim]")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip().lower()
        sanitised = re.sub(r"[^a-z0-9\s-]", "", raw) if raw else ""
        sanitised = re.sub(r"\s+", "-", sanitised.strip()) or self.suggestion
        self.dismiss(sanitised)

    def action_use_suggestion(self) -> None:
        self.dismiss(self.suggestion)


# ── Chat App ──────────────────────────────────────────────────────────────────

class ChatApp(App[None]):
    """Main interactive chat TUI."""

    TITLE     = "Obsidian Brain"
    SUB_TITLE = CHAT_MODEL

    CSS = _CSS

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("escape", "clear_input", "Clear input", show=False),
    ]

    def __init__(self, db: Chroma) -> None:
        super().__init__()
        self.db    = db
        self._busy = False

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
            "[dim]Ctrl+Q to quit  ·  run with --organize to tag & link notes[/dim]\n"
        ))
        self.query_one(Input).focus()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _log(self, markup: str) -> None:
        self.query_one(RichLog).write(Text.from_markup(markup))

    # ── Input ─────────────────────────────────────────────────────────────────

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

        try:
            chunks = await asyncio.to_thread(
                lambda: self.db.as_retriever(search_kwargs={"k": TOP_K}).invoke(question)
            )
            sufficient = await asyncio.to_thread(
                lambda: context_is_sufficient(question, chunks)
            )

            if sufficient:
                self._log("[dim]📓  Source: vault notes[/dim]")
                answer = await asyncio.to_thread(
                    lambda: llm.invoke(build_vault_prompt(question, chunks)).content
                )
                log.write(Markdown(answer))
                return

            self._log("[dim]🧠  Vault insufficient — trying model knowledge[/dim]")
            model_answer = await asyncio.to_thread(
                lambda: llm.invoke(build_knowledge_prompt(question)).content
            )

            if not model_answer.strip().lower().startswith("i'm not certain"):
                self._log("[dim]🧠  Source: model knowledge[/dim]")
                suggestion = await asyncio.to_thread(
                    lambda: get_concept_suggestion(question, model_answer)
                )
                concept = await self.push_screen_wait(FilenameModal(suggestion))
                await asyncio.to_thread(
                    lambda: save_to_vault(concept, question, model_answer, "model knowledge", self.db)
                )
                self._log(f"[dim]📝  Saved to {concept}.md[/dim]")
                log.write(Markdown(model_answer))
                return

            self._log("[dim]🌐  Model uncertain — searching the web[/dim]")
            web_ctx = await asyncio.to_thread(lambda: web_search(question))
            web_answer = await asyncio.to_thread(
                lambda: llm.invoke(build_web_prompt(question, web_ctx)).content
            )
            self._log("[dim]🌐  Source: web search[/dim]")
            suggestion = await asyncio.to_thread(
                lambda: get_concept_suggestion(question, web_answer)
            )
            concept = await self.push_screen_wait(FilenameModal(suggestion))
            await asyncio.to_thread(
                lambda: save_to_vault(concept, question, web_answer, "web search", self.db)
            )
            self._log(f"[dim]📝  Saved to {concept}.md[/dim]")
            log.write(Markdown(web_answer))

        finally:
            self._busy = False
            self.query_one(Input).focus()

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
      custom text    — override (comma-separated tags, or a free-text answer)
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

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _log(self, markup: str) -> None:
        self.query_one(RichLog).write(Text.from_markup(markup))

    async def _prompt(self, hint: str = "") -> str:
        """Display a hint line then wait for the user to submit input."""
        if hint:
            self._log(f"[dim]{hint}[/dim]")
        return await self._queue.get()

    # ── Organise worker ───────────────────────────────────────────────────────

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

            final = [t.strip() for t in raw.split(",")] if raw else suggested
            frontmatter = "---\ntags:\n" + "".join(f"  - {t}\n" for t in final) + "---\n"
            new_content = frontmatter + content

            with open(data["path"], "w", encoding="utf-8") as f:
                f.write(new_content)
            notes[stem]["content"] = new_content
            self._log("  [green]✓ Tags written.[/green]")

        # ── Pass 2: Wikilinks ──────────────────────────────────────────────────

        self._log("\n[bold]Scanning for wikilink opportunities…[/bold]")

        for stem, data in notes.items():
            content      = data["content"]
            other_notes  = {s: d["title"] for s, d in notes.items() if s != stem}
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
                fm_end      = content.find("---", content.index("---") + 3) + 3
                fm_block    = content[:fm_end]
                body        = content[fm_end:]
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
