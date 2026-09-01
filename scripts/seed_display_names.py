"""
Load human-readable book labels from data/book_display_names.csv into
documents.display_name.

Usage (from project root, venv active):

    python scripts/seed_display_names.py

The CSV is the editable source of truth: fix a name there and re-run.
Books present in the DB but missing from the CSV keep display_name = NULL,
and the UI falls back to the raw `book` siglum.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "book_display_names.csv"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    p.add_argument("--db-url", default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    load_dotenv(ROOT / ".env", override=True)
    db_url = args.db_url or os.getenv("DATABASE_URL")
    if not db_url:
        sys.exit("DATABASE_URL is not set")

    if not args.csv.is_file():
        sys.exit(f"CSV not found: {args.csv}")

    with args.csv.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != ["book", "display_name"]:
            sys.exit(
                f"Expected header 'book,display_name', got: {reader.fieldnames}"
            )
        pairs = [
            (row["book"].strip(), row["display_name"].strip())
            for row in reader
            if row.get("book", "").strip()
        ]

    print(f"Loaded {len(pairs)} display names from {args.csv}")

    conn = psycopg2.connect(
        db_url,
        sslmode="allow",
        gssencmode="disable",
        connect_timeout=30,
    )
    try:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                UPDATE documents AS d
                SET display_name = v.display_name
                FROM (VALUES %s) AS v(book, display_name)
                WHERE d.book = v.book
                """,
                pairs,
                page_size=500,
            )
            updated = cur.rowcount
            cur.execute(
                "SELECT COUNT(*) FROM documents WHERE display_name IS NULL"
            )
            (missing,) = cur.fetchone()
            cur.execute(
                """
                SELECT book, display_name FROM documents
                WHERE display_name IS NOT NULL
                ORDER BY corpus, book LIMIT 5
                """
            )
            sample = cur.fetchall()
        conn.commit()
    finally:
        conn.close()

    print(f"Rows updated: {updated}")
    print(f"Documents still without a display name: {missing}")
    print("Sample:")
    for book, name in sample:
        print(f"  {book} -> {name}")


if __name__ == "__main__":
    main()
