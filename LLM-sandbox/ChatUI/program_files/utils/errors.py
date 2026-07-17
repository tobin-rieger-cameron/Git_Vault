"""Exception hierarchy, defined by how callers catch each one, not by source."""


class ChatUIError(Exception):
    pass


class VaultFileNotFoundError(ChatUIError):
    pass


class VaultWriteError(ChatUIError):
    pass


class IngestError(ChatUIError):
    pass


class RetrievalError(ChatUIError):
    pass


class ModelUnavailableError(ChatUIError):
    pass
