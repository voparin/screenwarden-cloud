import pytest
from datetime import timedelta
from cloud.api.auth import (
    hash_password, verify_password,
    create_access_token, decode_access_token,
    generate_device_token, generate_pairing_code,
)

def test_hash_and_verify_password():
    h = hash_password("secret123")
    assert verify_password("secret123", h) is True
    assert verify_password("wrong", h) is False

def test_create_and_decode_token():
    token = create_access_token({"sub": "family-123"}, expires_delta=timedelta(minutes=5))
    payload = decode_access_token(token)
    assert payload["sub"] == "family-123"

def test_expired_token_returns_none():
    token = create_access_token({"sub": "family-123"}, expires_delta=timedelta(seconds=-1))
    assert decode_access_token(token) is None

def test_generate_device_token_is_64_chars():
    token = generate_device_token()
    assert len(token) == 64

def test_generate_pairing_code_format():
    code = generate_pairing_code()
    assert len(code) == 9  # "SW-XXXXXX"
    assert code.startswith("SW-")
    assert code[3:].isalnum()
