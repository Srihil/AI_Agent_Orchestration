import pytest
from app.services.auth_service import hash_password, verify_password, create_access_token
from jose import jwt
from app.config.settings import settings


def test_password_hashing():
    password = "securepassword123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)


def test_wrong_password_fails():
    hashed = hash_password("correctpassword")
    assert not verify_password("wrongpassword", hashed)


def test_create_access_token():
    data = {"sub": "user123"}
    token = create_access_token(data)
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert decoded["sub"] == "user123"
    assert "exp" in decoded


def test_token_contains_user_id():
    user_id = "abc-def-123"
    token = create_access_token({"sub": user_id})
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert decoded["sub"] == user_id
