"""Embedding provider interface."""

from abc import ABC, abstractmethod


class BaseEmbedder(ABC):
    """Turns text into fixed-dimension vectors.

    Implementations must produce vectors of length `dim`. `encode` takes a batch
    so callers can amortize model/API overhead.
    """

    @property
    @abstractmethod
    def dim(self) -> int: ...

    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, returning one vector per input."""
        ...

    def encode_one(self, text: str) -> list[float]:
        return self.encode([text])[0]
