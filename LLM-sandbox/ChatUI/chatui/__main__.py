"""Entrypoint: python -m chatui --vault ../Knowledge"""

from __future__ import annotations

import argparse
from pathlib import Path

from chatui.app import ChatApp
from chatui.config import load_settings
from chatui.llm import ModelClient
from chatui.retrieval import Retriever
from chatui.vault import Vault


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", type=Path, required=True)
    args = parser.parse_args()

    settings = load_settings(config_dir=Path(__file__).parent.parent / "config")
    vault = Vault(root=args.vault)
    retriever = Retriever(db_path=Path(__file__).parent.parent / "local_db", embed_model=settings.embed_model)
    model = ModelClient(chat_model=settings.chat_model, coding_model=settings.coding_model)

    ChatApp(vault=vault, retriever=retriever, model=model, settings=settings).run()


if __name__ == "__main__":
    main()
