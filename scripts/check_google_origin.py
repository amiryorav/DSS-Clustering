"""Ask Google whether an origin is registered on the OAuth client.

Google's sign-in button is an iframe that 403s when the page origin is not an
Authorized JavaScript origin, and the browser console only says "the given origin
is not allowed" without saying what Google actually has on file. The button
endpoint validates the ``Origin`` header, so a plain request answers the question
directly and takes the Cloud Console form out of the loop.

    python scripts/check_google_origin.py
    python scripts/check_google_origin.py http://localhost:3000 https://example.com

Exit status is non-zero when any checked origin is rejected.
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request

BUTTON_URL = "https://accounts.google.com/gsi/button"
CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)
DEFAULT_ORIGINS = ("http://localhost:3000",)
# Google never registers this, so a 403 here proves the probe can still tell
# allowed from rejected rather than being blocked wholesale.
CONTROL_ORIGIN = "https://origin-that-is-never-registered.example"


def probe(client_id: str, origin: str) -> int:
    """HTTP status Google returns for the button when served to ``origin``."""
    query = (
        f"?type=standard&theme=outline&size=large&shape=pill"
        f"&is_fedcm_supported=true&client_id={client_id}&iframe_id=gsi_probe"
    )
    request = urllib.request.Request(
        BUTTON_URL + query,
        headers={
            "Origin": origin,
            "Referer": origin + "/",
            "User-Agent": CHROME_UA,
            "Sec-Fetch-Dest": "iframe",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def main(argv: list[str]) -> int:
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        print("GOOGLE_CLIENT_ID is not set in this shell.", file=sys.stderr)
        return 2

    origins = tuple(argv) or DEFAULT_ORIGINS
    print(f"client id: {client_id}\n")

    rejected = []
    for origin in origins:
        status = probe(client_id, origin)
        allowed = status == 200
        print(f"{origin:<44} {status}  {'allowed' if allowed else 'REJECTED'}")
        if not allowed:
            rejected.append(origin)

    if rejected and probe(client_id, CONTROL_ORIGIN) == 200:
        print("\nControl origin was also accepted, so this probe is unreliable.")
        return 3

    if rejected:
        print(
            "\nAdd the rejected origin(s) under Authorized JavaScript origins on "
            "this client, press Save, then re-run. Changes are usually live within "
            "minutes."
        )
    return 1 if rejected else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
