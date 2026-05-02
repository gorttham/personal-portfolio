import time
import jwt
import pytest
from app.services.auth import decode_nextauth_token, AuthError

SECRET = "test-nextauth-secret"

def make_token(payload: dict, secret: str = SECRET) -> str:
    return jwt.encode(payload, secret, algorithm="HS256")


def test_valid_token_returns_email():
    token = make_token({"email": "user@example.com", "exp": int(time.time()) + 3600})
    result = decode_nextauth_token(token, SECRET)
    assert result["email"] == "user@example.com"


def test_expired_token_raises():
    token = make_token({"email": "user@example.com", "exp": int(time.time()) - 1})
    with pytest.raises(AuthError, match="expired"):
        decode_nextauth_token(token, SECRET)


def test_wrong_secret_raises():
    token = make_token({"email": "user@example.com", "exp": int(time.time()) + 3600})
    with pytest.raises(AuthError, match="invalid"):
        decode_nextauth_token(token, "wrong-secret")


def test_missing_email_raises():
    token = make_token({"sub": "123", "exp": int(time.time()) + 3600})
    with pytest.raises(AuthError, match="email"):
        decode_nextauth_token(token, SECRET)
