"""Apply alembic migrations against the configured database.

``reflex db migrate`` boots the whole app first, which is slow and hides errors
behind a silent hang when the database is briefly unreachable; this runs the
same migrations directly and prints the revision before and after.
"""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(".env")

import rxconfig  # noqa: E402  (must follow load_dotenv)


def main() -> None:
    config = Config("alembic.ini")
    # configparser reads % as interpolation, and the URL carries percent-encoded
    # password characters.
    config.set_main_option("sqlalchemy.url", rxconfig.config.db_url.replace("%", "%%"))
    print("current:", flush=True)
    command.current(config)
    print("upgrading to head…", flush=True)
    command.upgrade(config, "head")
    print("now:", flush=True)
    command.current(config)


if __name__ == "__main__":
    main()
