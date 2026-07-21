"""Entrypoint: python -m program_files (vault defaults to the repo working directory; pass --vault to override)"""

from __future__ import annotations

import argparse
from pathlib import Path

from program_files.app import ChatApp
from program_files.utils.config import load_settings
from program_files.utils.debug_log import configure as configure_debug_log
from program_files.utils.llm import ModelClient
from program_files.utils.retrieval import Retriever
from program_files.utils.transcript import TranscriptWriter
from program_files.utils.vault import Vault


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", type=Path, default=None)
    args = parser.parse_args()

    configure_debug_log(Path(__file__).parent.parent / "chatui_debug.log")
    settings = load_settings(config_dir=Path(__file__).parent.parent / "config")
    vault = Vault(root=args.vault or settings.vault_path)
    retriever = Retriever(
        db_path=Path(__file__).parent.parent / "local_db",
        embed_model=settings.embed_model,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    model = ModelClient(chat_model=settings.chat_model, coding_model=settings.coding_model)
    transcript = TranscriptWriter(
        log_dir=Path(__file__).parent.parent.parent / "conversations" / "transcripts", vault_name=vault.root.name
    )

    ChatApp(vault=vault, retriever=retriever, model=model, settings=settings, transcript=transcript).run()


if __name__ == "__main__":
    main()
