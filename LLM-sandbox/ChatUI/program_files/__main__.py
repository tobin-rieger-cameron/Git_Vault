"""Entrypoint: python -m program_files --vault ../Knowledge"""

from __future__ import annotations

import argparse
from pathlib import Path

from program_files.app import ChatApp
from program_files.config import load_settings
from program_files.debug_log import configure as configure_debug_log
from program_files.llm import ModelClient
from program_files.retrieval import Retriever
from program_files.vault import Vault


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", type=Path, required=True)
    args = parser.parse_args()

    configure_debug_log(Path(__file__).parent.parent / "chatui_debug.log")
    settings = load_settings(config_dir=Path(__file__).parent.parent / "config")
    vault = Vault(root=args.vault)
    retriever = Retriever(
        db_path=Path(__file__).parent.parent / "local_db",
        embed_model=settings.embed_model,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    model = ModelClient(chat_model=settings.chat_model, coding_model=settings.coding_model)

    ChatApp(vault=vault, retriever=retriever, model=model, settings=settings).run()


if __name__ == "__main__":
    main()
