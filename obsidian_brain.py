"""
obsidian_brain.py
-----------------
A local RAG (Retrieval-Augmented Generation) tool that lets you query your
Obsidian vault using a locally-running LLM via Ollama.

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
                response is saved to a concept note in the vault (e.g.
                cupcakes.md) so future questions can be answered from the vault.
                The live ChromaDB is updated immediately so re-ingestion isn't
                needed between sessions.

Dependencies (install into your venv):
  pip install langchain langchain-ollama langchain-community chromadb duckduckgo-search

Ollama models needed (pull once):
  ollama pull nomic-embed-text   # embedding model
  ollama pull llama3.2           # chat/generation model
"""

# ── Imports ───────────────────────────────────────────────────────────────────

import os
import re
import sys
from datetime import datetime

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
CHAT_MODEL  = "llama3.2:3b"          # used to generate answers

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

        # Format each result as a readable block the LLM can work with
        formatted = []
        for r in results:
            formatted.append(f"Source: {r['href']}\nTitle: {r['title']}\n{r['body']}")

        return "\n\n---\n\n".join(formatted)

    except Exception as e:
        return f"Web search failed: {e}"


# ── Learning: Save responses to vault ─────────────────────────────────────────

def save_to_vault(question: str, answer: str, source: str, db: Chroma) -> None:
    """
    Save a question/answer pair to a concept note in the vault, then add it to
    the live ChromaDB so it's immediately searchable without needing a full
    re-ingest.

    The filename is chosen by the user at runtime: the model suggests a short
    concept name (e.g. "cupcakes") and the user can confirm it or type their own.
    If the file already exists, the new entry is appended. If not, it's created
    with a header.

    Args:
        question: The original user question.
        answer:   The generated answer.
        source:   Where the answer came from ("model knowledge" or "web search").
        db:       The live Chroma instance to update in place.
    """
    suggestion_prompt = f"""Identify the single core concept or subject that this question and answer are about.
Reply with only 1-3 words, lowercase, no punctuation. This will be used as a filename.

Examples:
  Q: What are cupcakes? → cupcakes
  Q: How does photosynthesis work? → photosynthesis
  Q: Who invented the telephone? → telephone

Question: {question}
Answer: {answer}
Core concept:"""

    raw_suggestion = llm.invoke(suggestion_prompt).content.strip().lower()
    suggestion = re.sub(r"[^a-z0-9\s-]", "", raw_suggestion)
    suggestion = re.sub(r"\s+", "-", suggestion.strip()) or "general"

    user_input = input(f"Filename (default: {suggestion}): ").strip()
    raw_choice = user_input if user_input else suggestion
    concept = re.sub(r"[^a-z0-9\s-]", "", raw_choice.lower())
    concept = re.sub(r"\s+", "-", concept.strip()) or "general"
    filename  = f"{concept}.md"
    filepath  = os.path.join(VAULT_PATH, filename)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Build the new entry block to append
    entry = f"""
## Q: {question}
*Source: {source} — {timestamp}*

{answer}
"""

    if os.path.exists(filepath):
        # File exists — append to it
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(entry)
        print(f"📝 [Learned: appended to {filename}]")
    else:
        # New concept — create the file with a title header
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {concept.replace('-', ' ').title()}\n")
            f.write(entry)
        print(f"📝 [Learned: created {filename}]")

    # Add the new content to the live ChromaDB so it's searchable immediately.
    # This avoids needing to run --ingest again after every session.
    new_doc = Document(
        page_content=f"Q: {question}\n\n{answer}",
        metadata={"source": filepath},
    )
    db.add_documents([new_doc])


# ── Retrieval + Generation ─────────────────────────────────────────────────────

def build_vault_prompt(question: str, context_chunks: list) -> str:
    """
    Prompt for answering from vault context.
    The LLM is instructed to only use the provided notes.
    """
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
    """
    Prompt for answering from the model's own training knowledge.
    The LLM is asked to flag uncertainty so the fallback chain can continue.
    """
    return f"""Answer the following question using your own knowledge.
If you are not confident in your answer or the information may be outdated,
start your response with the exact phrase: "I'm not certain, but"

Question: {question}
Answer:"""


def build_web_prompt(question: str, web_context: str) -> str:
    """
    Prompt for answering from web search results.
    """
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

    This is the 'judge' step — it runs before generating a full answer so we
    don't waste a generation on context that won't help.
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

    # Accept any response that starts with YES to handle "YES." / "YES," etc.
    return response.startswith("YES")


def ask(question: str, db: Chroma) -> str:
    """
    Answer a question using the fallback chain, then save anything learned
    back to the vault.

      1. Retrieve vault chunks and judge whether they're sufficient.
      2. If yes  → answer from vault (nothing new to save).
      3. If no   → try the model's own knowledge → save if confident.
      4. If model uncertain → web search → answer and save from results.

    Args:
        question: The user's natural language question.
        db:       The loaded Chroma vector store to search and update.

    Returns:
        The LLM's answer as a string.
    """
    # ── Step 1: Vault retrieval + judgement ───────────────────────────────────
    retriever = db.as_retriever(search_kwargs={"k": TOP_K})
    chunks    = retriever.invoke(question)

    if context_is_sufficient(question, chunks):
        print("📓 [Source: vault notes]")
        return llm.invoke(build_vault_prompt(question, chunks)).content

    # ── Step 2: Model's own knowledge ─────────────────────────────────────────
    print("🧠 [Vault context insufficient — trying model knowledge]")
    model_answer = llm.invoke(build_knowledge_prompt(question)).content

    if not model_answer.strip().lower().startswith("i'm not certain"):
        print("🧠 [Source: model knowledge]")
        save_to_vault(question, model_answer, "model knowledge", db)
        return model_answer

    # ── Step 3: Web search fallback ───────────────────────────────────────────
    print("🌐 [Model uncertain — searching the web]")
    web_context  = web_search(question)
    web_answer   = llm.invoke(build_web_prompt(question, web_context)).content
    print("🌐 [Source: web search]")
    save_to_vault(question, web_answer, "web search", db)
    return web_answer


# ── Interactive Loop ───────────────────────────────────────────────────────────

def run_interactive(db: Chroma) -> None:
    """
    Start a simple REPL (read-eval-print loop) for chatting with your vault.
    Type 'quit' or press Ctrl+C to exit.
    """
    print("🧠 Obsidian Brain ready. Ask anything about your notes.")
    print("   Type 'quit' to exit.\n")

    while True:
        try:
            question = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break

        if not question:
            continue

        if question.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break

        answer = ask(question, db)
        print(f"\nAI: {answer}\n")


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Pass --ingest as a command-line argument to rebuild the database.
    # Otherwise, it loads the existing one.
    #
    # Usage:
    #   python obsidian_brain.py           # use existing DB
    #   python obsidian_brain.py --ingest  # rebuild DB from vault, then start

    if "--ingest" in sys.argv:
        db = ingest_vault()
    else:
        try:
            db = load_existing_db()
        except FileNotFoundError as e:
            print(f"❌ {e}")
            sys.exit(1)

    run_interactive(db)
