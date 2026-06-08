"""Administrator password hashing and encrypted credential storage."""

from __future__ import annotations

import os
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

_PASSWORD_HASHER = PasswordHasher()


def generate_secret_key(path: Path) -> None:
    if path.exists():
        raise ValueError(f"secret key already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as target:
        target.write(Fernet.generate_key())
    path.chmod(0o600)


def load_cipher(path: Path) -> Fernet:
    try:
        return Fernet(path.read_bytes())
    except FileNotFoundError as exc:
        raise ValueError(f"secret key does not exist: {path}") from exc
    except (ValueError, InvalidToken) as exc:
        raise ValueError(f"secret key is invalid: {path}") from exc


def encrypt_secret(path: Path, value: str) -> bytes:
    return load_cipher(path).encrypt(value.encode("utf-8"))


def decrypt_secret(path: Path, value: bytes) -> str:
    try:
        return load_cipher(path).decrypt(value).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("encrypted credential cannot be decrypted") from exc


def hash_password(password: str) -> str:
    _validate_password(password)
    return _PASSWORD_HASHER.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _PASSWORD_HASHER.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def _validate_password(password: str) -> None:
    if len(password) < 12:
        raise ValueError("administrator password must contain at least 12 characters")
