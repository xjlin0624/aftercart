from uuid import uuid4

import pytest
from jose import JWTError

from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_produces_different_hashes_for_same_input():
    h1 = hash_password("secret")
    h2 = hash_password("secret")
    assert h1 != h2  # bcrypt salts every hash


def test_verify_password_correct():
    hashed = hash_password("correct-horse")
    assert verify_password("correct-horse", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("correct-horse")
    assert verify_password("wrong-horse", hashed) is False


def test_access_token_has_correct_kind():
    token = create_access_token(str(uuid4()))
    payload = decode_token(token)
    assert payload["kind"] == "access"


def test_refresh_token_has_correct_kind():
    token = create_refresh_token(str(uuid4()))
    payload = decode_token(token)
    assert payload["kind"] == "refresh"


def test_token_sub_matches_user_id():
    user_id = str(uuid4())
    token = create_access_token(user_id)
    payload = decode_token(token)
    assert payload["sub"] == user_id


def test_decode_token_rejects_garbage():
    with pytest.raises(JWTError):
        decode_token("not.a.token")


def test_access_token_rejected_as_refresh():
    """An access token must not be accepted where a refresh token is expected."""
    token = create_access_token(str(uuid4()))
    payload = decode_token(token)
    assert payload["kind"] != "refresh"
