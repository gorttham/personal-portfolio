import pytest
from app.services.encryption import encrypt, decrypt


def test_encrypt_returns_string():
    result = encrypt("secret", "test-key-32-chars-padded-to-fit!!")
    assert isinstance(result, str)
    assert result != "secret"


def test_decrypt_reverses_encrypt():
    key_str = "test-key-32-chars-padded-to-fit!!"
    ciphertext = encrypt("my api token", key_str)
    assert decrypt(ciphertext, key_str) == "my api token"


def test_different_encryptions_are_different():
    key_str = "test-key-32-chars-padded-to-fit!!"
    a = encrypt("same", key_str)
    b = encrypt("same", key_str)
    assert a != b  # Fernet uses random IV


def test_decrypt_wrong_key_raises():
    key_str = "test-key-32-chars-padded-to-fit!!"
    from cryptography.fernet import Fernet
    other_key = Fernet.generate_key().decode()
    ciphertext = encrypt("secret", key_str)
    with pytest.raises(Exception):
        decrypt(ciphertext, other_key)
