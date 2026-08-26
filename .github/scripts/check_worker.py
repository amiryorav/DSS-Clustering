"""Probe the Reflex Cloud worker (not the static frontend).

Reads ``reflex cloud apps inspect --json`` output, then hits the backend
``/ping/`` and ``/_health`` URLs. Exit codes:

  0  worker healthy (or Cloud Running and public /ping/ unreachable)
  10 worker down (restart or start)
  11 worker up but DB/Redis unhealthy (alert, do not restart)
  2  inspect payload unusable
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

PING_TIMEOUT_SEC = 12
PING_ATTEMPTS = 1
PING_RETRY_SEC = 8
SKIP_RESTART_STATUSES = {"building", "deploying", "updating"}
DOWN_STATUSES = {"stopped", "paused", "dead", "failed", "error"}


def _github_output(key: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"{key}={value}\n")


def load_inspect(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    return parse_inspect_text(raw)


def parse_inspect_text(raw: str) -> dict:
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < start:
        raise ValueError("inspect output has no JSON object")
    # Reflex CLI --json can emit literal newlines inside string fields.
    return json.loads(raw[start : end + 1], strict=False)


def http_get(url: str, timeout: int = PING_TIMEOUT_SEC) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "dss-keepalive"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return int(resp.status), body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return int(exc.code), body
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


def ping_result(backend_url: str) -> tuple[int, str]:
    """Return the last (http_status, body). Status 0 means no HTTP response."""
    url = backend_url.rstrip("/") + "/ping/"
    last_status, last_body = 0, ""
    for attempt in range(1, PING_ATTEMPTS + 1):
        last_status, last_body = http_get(url)
        if last_status == 200 and "pong" in last_body.lower():
            return last_status, last_body
        print(
            f"ping attempt {attempt}/{PING_ATTEMPTS}: "
            f"HTTP {last_status} {last_body[:200]!r}"
        )
        if attempt < PING_ATTEMPTS:
            time.sleep(PING_RETRY_SEC)
    return last_status, last_body


def ping_ok(backend_url: str) -> bool:
    status, body = ping_result(backend_url)
    return status == 200 and "pong" in body.lower()


def health_payload(backend_url: str) -> dict | None:
    url = backend_url.rstrip("/") + "/_health"
    status, body = http_get(url)
    if status != 200:
        print(f"_health HTTP {status} {body[:200]!r}")
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        print(f"_health not JSON: {body[:200]!r}")
        return None


def decide(inspect_data: dict, *, force_restart: bool = False) -> tuple[int, str, bool]:
    """Return (exit_code, reason, should_restart)."""
    if inspect_data.get("any_environment_credit_paused"):
        return 11, "Cloud credits paused; not restarting", False

    deployment = inspect_data.get("latest_deployment") or {}
    status = str(deployment.get("status") or "").strip()
    backend_url = str(inspect_data.get("backend_url") or "").strip()
    if not backend_url:
        return 2, "inspect JSON has no backend_url", False

    status_l = status.lower()
    if status_l in SKIP_RESTART_STATUSES:
        return 0, f"deployment is {status}; skipping probe", False

    if force_restart:
        return 10, "force_restart requested", True

    if status_l in DOWN_STATUSES:
        return 10, f"Cloud status is {status or 'unknown'}", True

    ping_status, ping_body = ping_result(backend_url)
    if ping_status == 200 and "pong" in ping_body.lower():
        health = health_payload(backend_url)
        if health is None:
            return 10, "backend /_health failed after a successful ping", True
        if not health.get("status", True):
            db_ok = health.get("db", True)
            redis_ok = health.get("redis", True)
            if db_ok and redis_ok:
                return 10, f"_health status false: {health}", True
            return 11, f"worker up but dependencies unhealthy: {health}", False
        return 0, f"healthy (Cloud status={status or 'unknown'})", False

    # Fly's public backend URL often fails TLS from GitHub runners (and
    # other networks) even while Cloud inspect says Running. Stopping the
    # app on that signal takes the site down. Only bounce on HTTP 5xx.
    if 500 <= ping_status < 600:
        return 10, f"backend HTTP {ping_status} while Cloud status={status}", True

    return (
        0,
        f"Cloud status={status or 'unknown'}; /ping/ unreachable from this "
        f"runner (HTTP {ping_status}) — not restarting",
        False,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inspect_json",
        nargs="?",
        help="Path to inspect JSON (or CLI stdout that contains JSON)",
    )
    parser.add_argument(
        "--extract-inspect",
        nargs=2,
        metavar=("RAW", "OUT"),
        help="Copy the JSON object from RAW CLI output into OUT.",
    )
    parser.add_argument("--force-restart", action="store_true")
    parser.add_argument(
        "--require-healthy",
        action="store_true",
        help="Exit 1 unless the worker is healthy (used after a restart).",
    )
    args = parser.parse_args(argv)

    if args.extract_inspect:
        src, dest = args.extract_inspect
        try:
            data = load_inspect(src)
        except Exception as exc:  # noqa: BLE001
            print(f"cannot parse inspect JSON: {exc}")
            _github_output("restart", "false")
            _github_output("start_only", "false")
            _github_output("reason", "inspect-parse-failed")
            return 2
        with open(dest, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        dep = data.get("latest_deployment") or {}
        print("status", dep.get("status"))
        print("backend", data.get("backend_url"))
        return 0

    if not args.inspect_json:
        parser.error("inspect_json is required unless --extract-inspect is set")

    try:
        data = load_inspect(args.inspect_json)
    except Exception as exc:  # noqa: BLE001
        print(f"cannot parse inspect JSON: {exc}")
        _github_output("restart", "false")
        _github_output("start_only", "false")
        _github_output("reason", "inspect-parse-failed")
        return 2

    code, reason, restart = decide(data, force_restart=args.force_restart)
    print(reason)
    status_l = str(
        (data.get("latest_deployment") or {}).get("status") or ""
    ).lower()
    start_only = restart and status_l in DOWN_STATUSES and not args.force_restart
    _github_output("restart", "true" if restart else "false")
    _github_output("start_only", "true" if start_only else "false")
    _github_output("reason", reason.replace("\n", " ")[:200])

    if args.require_healthy and code != 0:
        return 1
    return code


if __name__ == "__main__":
    sys.exit(main())
