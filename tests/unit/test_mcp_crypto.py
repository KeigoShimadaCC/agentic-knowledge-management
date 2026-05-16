import pytest
from app.config import settings
from app.mcp_client.crypto import decrypt_env_vars, encrypt_env_vars
from cryptography.fernet import Fernet


@pytest.fixture
def encryption_key(monkeypatch: pytest.MonkeyPatch) -> str:
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "mcp_env_encryption_key", key)
    return key


def test_roundtrip(encryption_key: str) -> None:
    env_vars = {"OPENAI_API_KEY": "sk-test", "MODEL": "gpt-4o-mini"}

    encrypted = encrypt_env_vars(env_vars)

    assert decrypt_env_vars(encrypted) == env_vars


def test_missing_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "mcp_env_encryption_key", "")

    with pytest.raises(ValueError):
        encrypt_env_vars({"OPENAI_API_KEY": "sk-test"})


def test_empty_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "mcp_env_encryption_key", "")

    assert encrypt_env_vars({}) == {}
    assert decrypt_env_vars({}) == {}


def test_values_only_encrypted(encryption_key: str) -> None:
    env_vars = {"OPENAI_API_KEY": "sk-test", "MODEL": "gpt-4o-mini"}

    encrypted = encrypt_env_vars(env_vars)

    assert encrypted.keys() == env_vars.keys()
    assert encrypted != env_vars
    for key, value in env_vars.items():
        assert encrypted[key] != value
