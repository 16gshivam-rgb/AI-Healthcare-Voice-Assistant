import math

from app.core.config import settings
from app.services.embedding_provider import (
    EmbeddingProviderError,
    HashEmbeddingProvider,
    get_embedding_provider,
)


def test_hash_embedding_is_deterministic_normalized_and_unicode_aware(monkeypatch):
    monkeypatch.setattr(settings, "embedding_dimensions", 128)
    provider = HashEmbeddingProvider()
    first = provider.embed("मुझे seene mein dard hai")
    second = provider.embed("मुझे seene mein dard hai")
    assert first == second
    assert len(first) == 128
    assert math.isclose(math.sqrt(sum(value * value for value in first)), 1.0)


def test_embedding_provider_factory_does_not_silently_fallback(monkeypatch):
    monkeypatch.setattr(settings, "embedding_provider", "unconfigured")
    try:
        get_embedding_provider()
        raise AssertionError("Unknown embedding provider must be explicit.")
    except EmbeddingProviderError as error:
        assert "Unsupported configured embedding provider" in str(error)
