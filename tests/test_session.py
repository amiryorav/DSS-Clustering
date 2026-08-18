"""Signed session tokens must survive restarts without being forgeable."""

from __future__ import annotations

import pytest

from dss_clustering import session


@pytest.fixture(autouse=True)
def _secret(monkeypatch):
    monkeypatch.setenv("DSS_SESSION_SECRET", "unit-test-secret")


def test_round_trip_returns_the_same_user():
    token = session.issue_session(42)
    assert session.read_session(token) == 42


def test_editing_the_user_id_is_rejected():
    """A bare id in the browser could be swapped to read another account."""
    token = session.issue_session(42)
    _, expiry, signature = token.split(".")
    assert session.read_session(f"99.{expiry}.{signature}") == 0


def test_expired_token_is_rejected():
    assert session.read_session(session.issue_session(42, max_age=-1)) == 0


def test_garbage_is_rejected():
    for value in ("", "abc", "1.2", "1.2.3.4", "x.y.z"):
        assert session.read_session(value) == 0


def test_a_different_secret_cannot_mint_sessions(monkeypatch):
    token = session.issue_session(42)
    monkeypatch.setenv("DSS_SESSION_SECRET", "another-secret")
    assert session.read_session(token) == 0


def test_signing_is_disabled_without_a_secret(monkeypatch):
    monkeypatch.delenv("DSS_SESSION_SECRET", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    assert session.issue_session(42) == ""


def test_client_secret_is_the_fallback_key(monkeypatch):
    monkeypatch.delenv("DSS_SESSION_SECRET", raising=False)
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "oauth-secret")
    assert session.read_session(session.issue_session(7)) == 7
