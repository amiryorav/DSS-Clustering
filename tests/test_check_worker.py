"""Keepalive probe decisions (no live Cloud calls)."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / ".github" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import check_worker  # noqa: E402


def test_parse_inspect_strips_cli_noise():
    raw = 'Info: hello\n{"backend_url": "https://x", "latest_deployment": {"status": "Running"}}\n'
    data = check_worker.parse_inspect_text(raw)
    assert data["backend_url"] == "https://x"
    assert data["latest_deployment"]["status"] == "Running"


def test_stopped_status_requests_restart():
    code, _, restart = check_worker.decide(
        {
            "backend_url": "https://example.fly.dev",
            "latest_deployment": {"status": "Stopped"},
        }
    )
    assert code == 10
    assert restart is True


def test_building_skips_restart():
    code, _, restart = check_worker.decide(
        {
            "backend_url": "https://example.fly.dev",
            "latest_deployment": {"status": "Building"},
        }
    )
    assert code == 0
    assert restart is False


def test_credit_pause_does_not_restart():
    code, _, restart = check_worker.decide(
        {
            "backend_url": "https://example.fly.dev",
            "any_environment_credit_paused": True,
            "latest_deployment": {"status": "Running"},
        }
    )
    assert code == 11
    assert restart is False


def test_missing_backend_url():
    code, _, restart = check_worker.decide({"latest_deployment": {"status": "Running"}})
    assert code == 2
    assert restart is False


def test_running_unhealthy_deps_no_restart(monkeypatch):
    monkeypatch.setattr(check_worker, "ping_ok", lambda url: True)
    monkeypatch.setattr(
        check_worker,
        "health_payload",
        lambda url: {"status": False, "db": False, "redis": True},
    )
    code, _, restart = check_worker.decide(
        {
            "backend_url": "https://example.fly.dev",
            "latest_deployment": {"status": "Running"},
        }
    )
    assert code == 11
    assert restart is False


def test_running_ping_fail_restarts(monkeypatch):
    monkeypatch.setattr(check_worker, "ping_ok", lambda url: False)
    code, _, restart = check_worker.decide(
        {
            "backend_url": "https://example.fly.dev",
            "latest_deployment": {"status": "Running"},
        }
    )
    assert code == 10
    assert restart is True
