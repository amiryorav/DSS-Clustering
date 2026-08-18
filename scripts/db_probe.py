"""Quick connectivity probe for the configured database.

Reports how long a connect takes and what the schema currently looks like, so a
hanging ``reflex db migrate`` can be told apart from an application problem.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(".env")

import rxconfig  # noqa: E402  (must follow load_dotenv)


def main() -> None:
    engine = create_engine(
        rxconfig.config.db_url, connect_args={"connect_timeout": 15}
    )
    started = time.time()
    try:
        with engine.connect() as conn:
            print(f"connected in {time.time() - started:.1f}s", flush=True)
            tables = [
                row[0]
                for row in conn.execute(
                    text(
                        "select tablename from pg_tables "
                        "where schemaname = 'public' order by 1"
                    )
                )
            ]
            print("tables:", tables, flush=True)
            if "alembic_version" in tables:
                versions = [
                    row[0]
                    for row in conn.execute(text("select version_num from alembic_version"))
                ]
                print("alembic version:", versions, flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED after {time.time() - started:.1f}s: {type(exc).__name__}", flush=True)
        print(str(exc)[:400], flush=True)


if __name__ == "__main__":
    main()
