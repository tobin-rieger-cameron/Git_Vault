"""ChatApp — thin Textual shell. Holds one Vault/Retriever/ModelClient/Settings; no business logic here."""

from __future__ import annotations

from textual.app import App

from chatui.config import Settings
from chatui.llm import ModelClient
from chatui.retrieval import Retriever
from chatui.vault import Vault


class ChatApp(App):
    def __init__(self, vault: Vault, retriever: Retriever, model: ModelClient, settings: Settings) -> None:
        super().__init__()
        self.vault = vault
        self.retriever = retriever
        self.model = model
        self.settings = settings

    async def action_ask(self, question: str) -> None:
        raise NotImplementedError

    async def action_draft(self, subject: str) -> None:
        raise NotImplementedError

    async def action_classify(self) -> None:
        raise NotImplementedError

    async def action_review(self, subject: str | None = None) -> None:
        raise NotImplementedError
