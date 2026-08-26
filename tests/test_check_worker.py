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


def test_parse_inspect_allows_control_characters_in_strings():
    raw = '{"backend_url": "https://x", "description": "line1\nline2"}'
    data = check_worker.parse_inspect_text(raw)
    assert "line1" in data["description"]


def test_stopped_status_needs_deploy():
    code, _, needs = check_worker.decide(
        {
            "backend_url": "https://example.fly.dev",
            "latest_deployment": {"status": "Stopped"},
        }
    )
    assert code == 10
    assert needs is True


def test_building_skips_deploy():
    code, _, needs = check_worker.decide(
        {
            "backend_url": "https://example.fly.dev",
            "latest_deployment": {"status": "Building"},
        }
    )
    assert code == 0
    assert needs is False


def test_credit_pause_does_not_deploy():
    code, _, needs = check_worker.decide(
        {
            "backend_url": "https://example.fly.dev",
            "any_environment_credit_paused": True,
            "latest_deployment": {"status": "Running"},
        }
    )
    assert code == 11
    assert needs is False


def test_missing_backend_url():
    code, _, needs = check_worker.decide({"latest_deployment": {"status": "Running"}})
    assert code == 2
    assert needs is False


def test_frontend_404_needs_deploy(monkeypatch):
    monkeypatch.setattr(check_worker, "frontend_result", lambda url: (404, "not found"))
    code, reason, needs = check_worker.decide(
        {
            "backend_url": "https://example.fly.dev",
            "latest_deployment": {
                "status": "Running",
                "url": "https://dss-clustering.reflex.run",
            },
        }
    )
    assert code == 10
    assert needs is True
    assert "frontend HTTP 404" in reason


def test_frontend_502_needs_deploy(monkeypatch):
    monkeypatch.setattr(check_worker, "frontend_result", lambda url: (502, "bad"))
    code, _, needs = check_worker.decide(
        {
            "backend_url": "https://example.fly.dev",
            "latest_deployment": {"status": "Running"},
        }
    )
    assert code == 10
    assert needs is True


def test_frontend_unreachable_does_not_deploy(monkeypatch):
    monkeypatch.setattr(check_worker, "frontend_result", lambda url: (0, "timeout"))
    monkeypatch.setattr(check_worker, "ping_result", lambda url: (0, "SSL EOF"))
    code, reason, needs = check_worker.decide(
        {
            "backend_url": "https://example.fly.dev",
            "latest_deployment": {"status": "Running"},
        }
    )
    assert code == 0
    assert needs is False
    assert "not deploying" in reason


def test_running_unhealthy_deps_no_deploy(monkeypatch):
    monkeypatch.setattr(check_worker, "frontend_result", lambda url: (200, "ok"))
    monkeypatch.setattr(check_worker, "ping_result", lambda url: (200, '"pong"'))
    monkeypatch.setattr(
        check_worker,
        "health_payload",
        lambda url: {"status": False, "db": False, "redis": True},
    )
    code, _, needs = check_worker.decide(
        {
            "backend_url": "https://example.fly.dev",
            "latest_deployment": {"status": "Running"},
        }
    )
    assert code == 11
    assert needs is False


def test_running_unreachable_ping_does_not_deploy(monkeypatch):
    monkeypatch.setattr(check_worker, "frontend_result", lambda url: (200, "ok"))
    monkeypatch.setattr(check_worker, "ping_result", lambda url: (0, "SSL EOF"))
    code, reason, needs = check_worker.decide(
        {
            "backend_url": "https://example.fly.dev",
            "latest_deployment": {"status": "Running"},
        }
    )
    assert code == 0
    assert needs is False
    assert "not deploying" in reason


def test_running_http_502_needs_deploy(monkeypatch):
    monkeypatch.setattr(check_worker, "frontend_result", lambda url: (200, "ok"))
    monkeypatch.setattr(check_worker, "ping_result", lambda url: (502, "bad gateway"))
    code, _, needs = check_worker.decide(
        {
            "backend_url": "https://example.fly.dev",
            "latest_deployment": {"status": "Running"},
        }
    )
    assert code == 10
    assert needs is True


def test_frontend_status_kwarg_skips_http(monkeypatch):
    def boom(url):
        raise AssertionError("should not fetch")

    monkeypatch.setattr(check_worker, "frontend_result", boom)
    monkeypatch.setattr(check_worker, "ping_result", lambda url: (0, "SSL EOF"))
    code, _, needs = check_worker.decide(
        {
            "backend_url": "https://example.fly.dev",
            "latest_deployment": {"status": "Running"},
        },
        frontend_status=200,
    )
    assert code == 0
    assert needs is False
