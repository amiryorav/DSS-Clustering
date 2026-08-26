"""Probe Reflex Cloud status, the public frontend, and optional Fly /ping/.

Exit codes:

  0  healthy (Cloud Running; Fly /ping/ may be unreachable)
  10 dead — caller should notify and deploy
  11 Cloud credits paused or DB/Redis unhealthy — notify, do not deploy
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
DEFAULT_FRONTEND = "https://dss-clustering.reflex.run"
SKIP_DEPLOY_STATUSES = {"building", "deploying", "updating"}
DOWN_STATUSES = {"stopped", "paused", "dead", "failed", "error"}


def _github_output(key: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"{key}={value}\n")


def _emit(needs_deploy: bool, reason: str) -> None:
    _github_output("needs_deploy", "true" if needs_deploy else "false")
    _github_output("reason", reason.replace("\n", " ")[:240])


def load_inspect(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    return parse_inspect_text(raw)


def parse_inspect_text(raw: str) -> dict:
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < start:
        raise ValueError("inspect output has no JSON object")
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


def frontend_result(url: str) -> tuple[int, str]:
    status, body = http_get(url)
    print(f"frontend {url}: HTTP {status} {body[:120]!r}")
    return status, body


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


def resolve_frontend_url(inspect_data: dict, override: str | None = None) -> str:
    if override:
        return override.rstrip("/")
    deployment = inspect_data.get("latest_deployment") or {}
    url = str(deployment.get("url") or "").strip()
    return (url or DEFAULT_FRONTEND).rstrip("/")


def decide(
    inspect_data: dict,
    *,
    force_deploy: bool = False,
    frontend_url: str | None = None,
    frontend_status: int | None = None,
) -> tuple[int, str, bool]:
    """Return (exit_code, reason, needs_deploy)."""
    if inspect_data.get("any_environment_credit_paused"):
        return 11, "Cloud credits paused; not deploying", False

    deployment = inspect_data.get("latest_deployment") or {}
    status = str(deployment.get("status") or "").strip()
    backend_url = str(inspect_data.get("backend_url") or "").strip()
    if not backend_url:
        return 2, "inspect JSON has no backend_url", False

    status_l = status.lower()
    if status_l in SKIP_DEPLOY_STATUSES:
        return 0, f"deployment is {status}; skipping probe", False

    if force_deploy:
        return 10, "force_deploy requested", True

    if status_l in DOWN_STATUSES:
        return 10, f"Cloud status is {status or 'unknown'}", True

    fe_url = resolve_frontend_url(inspect_data, frontend_url)
    if frontend_status is None:
        frontend_status, _ = frontend_result(fe_url)
    if frontend_status == 404 or 500 <= frontend_status < 600:
        return 10, f"frontend HTTP {frontend_status} ({fe_url})", True

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

    if 500 <= ping_status < 600:
        return 10, f"backend HTTP {ping_status} while Cloud status={status}", True

    return (
        0,
        f"Cloud status={status or 'unknown'}; /ping/ unreachable from this "
        f"runner (HTTP {ping_status}) — not deploying",
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
    parser.add_argument("--force-deploy", action="store_true")
    parser.add_argument(
        "--frontend-url",
        default=os.environ.get("FRONTEND_URL", ""),
        help="Public frontend URL (default: inspect url or dss-clustering.reflex.run)",
    )
    parser.add_argument(
        "--require-healthy",
        action="store_true",
        help="Exit 1 unless decide() reports healthy (used after a deploy).",
    )
    args = parser.parse_args(argv)

    if args.extract_inspect:
        src, dest = args.extract_inspect
        try:
            data = load_inspect(src)
        except Exception as exc:  # noqa: BLE001
            print(f"cannot parse inspect JSON: {exc}")
            _emit(False, "inspect-parse-failed")
            return 2
        with open(dest, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        dep = data.get("latest_deployment") or {}
        print("status", dep.get("status"))
        print("backend", data.get("backend_url"))
        print("frontend", dep.get("url"))
        return 0

    if not args.inspect_json:
        parser.error("inspect_json is required unless --extract-inspect is set")

    try:
        data = load_inspect(args.inspect_json)
    except Exception as exc:  # noqa: BLE001
        print(f"cannot parse inspect JSON: {exc}")
        _emit(False, "inspect-parse-failed")
        return 2

    fe = args.frontend_url.strip() or None
    code, reason, needs_deploy = decide(
        data, force_deploy=args.force_deploy, frontend_url=fe
    )
    print(reason)
    _emit(needs_deploy, reason)

    if args.require_healthy and code != 0:
        return 1
    return code


if __name__ == "__main__":
    sys.exit(main())
