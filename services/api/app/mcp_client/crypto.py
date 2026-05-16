"""Fernet symmetric encryption for MCP connection env var secrets."""

from cryptography.fernet import Fernet

from app.config import settings


def _get_fernet() -> Fernet:
    key = settings.mcp_env_encryption_key
    if not key:
        raise ValueError(
            "MCP_ENV_ENCRYPTION_KEY is not set. "
            "Generate one with cryptography.fernet.Fernet.generate_key()."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_env_vars(env_vars: dict[str, str]) -> dict[str, str]:
    if not env_vars:
        return {}
    f = _get_fernet()
    return {k: f.encrypt(v.encode()).decode() for k, v in env_vars.items()}


def decrypt_env_vars(env_vars: dict[str, str]) -> dict[str, str]:
    if not env_vars:
        return {}
    f = _get_fernet()
    return {k: f.decrypt(v.encode()).decode() for k, v in env_vars.items()}
