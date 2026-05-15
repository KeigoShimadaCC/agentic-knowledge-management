from __future__ import annotations

import abc
import random

from app.config import settings


class EmbeddingProvider(abc.ABC):
    @abc.abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    @property
    def is_enabled(self) -> bool:
        return True


class DisabledEmbeddingProvider(EmbeddingProvider):
    @property
    def is_enabled(self) -> bool:
        return False

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingDisabledError("Embeddings are disabled: no OPENAI_API_KEY set")


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic zero vectors for tests. Activated when OPENAI_API_KEY='test-mock'."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        rng = random.Random(42)
        return [[rng.uniform(-1, 1) for _ in range(settings.embedding_dimension)] for _ in texts]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        import openai

        self._client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        batch_size = 100
        results: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = await self._client.embeddings.create(
                model=settings.embedding_model,
                input=batch,
            )
            results.extend(item.embedding for item in sorted(resp.data, key=lambda x: x.index))
        return results


class EmbeddingDisabledError(Exception):
    pass


def get_embedding_provider() -> EmbeddingProvider:
    key = settings.openai_api_key
    if not key:
        return DisabledEmbeddingProvider()
    if key in {"test-mock", "sk-test-placeholder"}:
        return MockEmbeddingProvider()
    return OpenAIEmbeddingProvider()
