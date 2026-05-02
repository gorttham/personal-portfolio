import base64
import os
from cryptography.fernet import Fernet


def _make_fernet(key_str: str) -> Fernet:
    try:
        return Fernet(key_str.encode())
    except Exception:
        padded = key_str.encode().ljust(32)[:32]
        return Fernet(base64.urlsafe_b64encode(padded))


def encrypt(plaintext: str, key_str: str | None = None) -> str:
    key = key_str or os.environ["ENCRYPTION_KEY"]
    return _make_fernet(key).encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str, key_str: str | None = None) -> str:
    key = key_str or os.environ["ENCRYPTION_KEY"]
    return _make_fernet(key).decrypt(ciphertext.encode()).decode()
