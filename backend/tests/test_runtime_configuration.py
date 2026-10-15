import pytest

from app.core.config import Settings
from app.models import Appointment, Doctor, Hospital, KnowledgeChunk, KnowledgeDocument


def test_model_registry_contains_provider_and_knowledge_models():
    assert {
        "appointments",
        "doctors",
        "hospitals",
        "knowledge_chunks",
        "knowledge_documents",
    }.issubset(Appointment.metadata.tables)
    assert Appointment.metadata is Doctor.metadata is Hospital.metadata
    assert KnowledgeChunk.metadata is KnowledgeDocument.metadata


def test_cors_origins_are_normalized_and_wildcards_rejected():
    settings = Settings(
        _env_file=None,
        backend_cors_origins=" https://portal.example/,http://localhost:3000 ",
    )
    assert settings.cors_origins == ["https://portal.example", "http://localhost:3000"]

    wildcard = Settings(_env_file=None, backend_cors_origins="*")
    with pytest.raises(ValueError, match="must not contain"):
        _ = wildcard.cors_origins


def test_production_configuration_rejects_weak_database_password():
    with pytest.raises(ValueError, match="strong database password"):
        Settings(
            _env_file=None,
            app_env="production",
            jwt_secret_key="x" * 64,
            database_url="postgresql+psycopg://service:weak@db/healthcare",
        )
