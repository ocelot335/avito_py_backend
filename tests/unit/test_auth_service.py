import pytest
import jwt
from datetime import datetime, timedelta, timezone
from services.auth import AuthService


@pytest.fixture
def auth_service():
    service = AuthService()
    service.secret_key = "test_super_secret_key_676767676767"
    service.algorithm = "HS256"
    service.expire_minutes = 15
    return service


def test_create_and_verify_token_success(auth_service):
    account_id = 42

    token = auth_service.create_access_token(account_id)
    assert isinstance(token, str)
    assert len(token) > 0

    decoded_id = auth_service.verify_access_token(token)
    assert decoded_id == account_id


def test_verify_expired_token(auth_service):
    expired_payload = {
        "sub": "99",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
    }
    expired_token = jwt.encode(
        expired_payload,
        auth_service.secret_key,
        algorithm=auth_service.algorithm,
    )

    result = auth_service.verify_access_token(expired_token)
    assert result is None


def test_verify_invalid_signature_token(auth_service):
    account_id = 77
    token = auth_service.create_access_token(account_id)

    tampered_token = token[:-5] + "abcde"

    result = auth_service.verify_access_token(tampered_token)
    assert result is None


def test_verify_token_missing_sub(auth_service):
    payload = {"exp": datetime.now(timezone.utc) + timedelta(minutes=15)}
    bad_token = jwt.encode(
        payload, auth_service.secret_key, algorithm=auth_service.algorithm
    )

    result = auth_service.verify_access_token(bad_token)
    assert result is None


def test_verify_completely_garbage_token(auth_service):
    result = auth_service.verify_access_token("not.a.jwt.token")
    assert result is None
