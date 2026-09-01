"""
Load master_dataset.pkl into Postgres tables documents + lemma_rows.

Usage (from project root, venv active):

    python scripts/ingest_master_dataset.py --replace --create-tables

Without --replace, aborts if lemma_rows already has data.
Optional: --db-url ... --pkl path/to/master_dataset.pkl --chunk-size 50000
Prefer `reflex db migrate` for schema when possible; --create-tables is a fallback.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PKL = ROOT / "master_dataset.pkl"

EXPECTED_COLUMNS = [
    "text_id",
    "corpus",
    "book",
    "verse_id",
    "form",
    "lemma",
    "clean_lemma",
    "row_type",
    "pos",
    "person",
    "gender",
    "number",
    "tense",
    "binyan",
    "state",
    "mood",
    "subtype",
    "processing_timestamp",
    "data_version",
]

LEMMA_COPY_COLUMNS = [
    "document_id",
    "text_id",
    "verse_id",
    "form",
    "lemma",
    "clean_lemma",
    "row_type",
    "pos",
    "person",
    "gender",
    "number",
    "tense",
    "binyan",
    "state",
    "mood",
    "subtype",
]

VALID_CORPORA = {"mikra", "mishna", "dss"}
MISSING_STRINGS = {"", "nan", "None", "none", "NaN", "NULL", "<NA>"}


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    book VARCHAR NOT NULL UNIQUE,
    corpus VARCHAR NOT NULL,
    n_nnn INTEGER NOT NULL DEFAULT 0,
    n_lemma INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_documents_book ON documents (book);
CREATE INDEX IF NOT EXISTS ix_documents_corpus ON documents (corpus);

CREATE TABLE IF NOT EXISTS lemma_rows (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id),
    text_id VARCHAR,
    verse_id VARCHAR,
    form VARCHAR,
    lemma VARCHAR,
    clean_lemma VARCHAR NOT NULL,
    row_type VARCHAR NOT NULL,
    pos VARCHAR,
    person VARCHAR,
    gender VARCHAR,
    number VARCHAR,
    tense VARCHAR,
    binyan VARCHAR,
    state VARCHAR,
    mood VARCHAR,
    subtype VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_lemma_rows_document_id ON lemma_rows (document_id);
CREATE INDEX IF NOT EXISTS ix_lemma_rows_text_id ON lemma_rows (text_id);
CREATE INDEX IF NOT EXISTS ix_lemma_rows_row_type ON lemma_rows (row_type);
CREATE INDEX IF NOT EXISTS ix_lemma_rows_document_id_row_type
    ON lemma_rows (document_id, row_type);
"""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--pkl",
        type=Path,
        default=DEFAULT_PKL,
        help=f"Path to master_dataset.pkl (default: {DEFAULT_PKL})",
    )
    p.add_argument(
        "--db-url",
        default=None,
        help="Postgres URL override (default: DATABASE_URL from .env)",
    )
    p.add_argument(
        "--replace",
        action="store_true",
        help="TRUNCATE documents + lemma_rows, then reload",
    )
    p.add_argument(
        "--chunk-size",
        type=int,
        default=50_000,
        help="Rows per COPY chunk (default: 50000)",
    )
    p.add_argument(
        "--create-tables",
        action="store_true",
        help="CREATE TABLE IF NOT EXISTS for documents/lemma_rows before load",
    )
    return p.parse_args()


def resolve_db_url(cli_url: str | None) -> str:
    load_dotenv(ROOT / ".env", override=True)
    url = cli_url or os.getenv("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is not set (pass --db-url or put it in .env)")
    return url


def connect(db_url: str):
    """Open a Postgres connection.

    sslmode=allow: this Windows client hangs on the TLS handshake when the
    URL forces sslmode=require against the Supabase pooler. allow tries a
    non-SSL connection first and still upgrades if the server requires TLS.
    """
    return psycopg2.connect(
        db_url,
        sslmode="allow",
        gssencmode="disable",
        connect_timeout=30,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    )


def nullify(value) -> str | None:
    """Turn missing / sentinel values into None for CSV NULL."""
    if value is None:
        return None
    try:
        import pandas as pd

        if pd.isna(value):
            return None
    except Exception:
        pass
    text = str(value).strip()
    if text in MISSING_STRINGS:
        return None
    return text


def load_dataframe(pkl_path: Path):
    import pandas as pd

    if not pkl_path.is_file():
        sys.exit(f"Pickle not found: {pkl_path}")

    print(f"Loading {pkl_path} ...")
    df = pd.read_pickle(pkl_path)
    print(f"  shape={df.shape}")

    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    extra = [c for c in df.columns if c not in EXPECTED_COLUMNS]
    if missing:
        sys.exit(f"Pickle missing expected columns: {missing}")
    if extra:
        print(f"  note: ignoring unexpected columns: {extra}")

    if "data_version" in df.columns and len(df):
        versions = df["data_version"].dropna().astype(str).unique().tolist()
        print(f"  data_version={versions[:5]}")

    return df


def prepare_frame(df):
    import pandas as pd

    out = df[EXPECTED_COLUMNS].copy()
    out["corpus"] = out["corpus"].map(lambda v: nullify(v))
    out["book"] = out["book"].map(lambda v: nullify(v))

    bad_corpus = out["corpus"].isna() | ~out["corpus"].isin(VALID_CORPORA)
    if bad_corpus.any():
        bad = out.loc[bad_corpus, "corpus"].value_counts(dropna=False).head(10)
        sys.exit(f"Invalid corpus values (expected {sorted(VALID_CORPORA)}):\n{bad}")

    if out["book"].isna().any():
        sys.exit(f"Found {int(out['book'].isna().sum())} rows with empty book")

    # Normalize string columns used in lemma_rows
    for col in LEMMA_COPY_COLUMNS:
        if col == "document_id":
            continue
        if col in ("clean_lemma", "row_type"):
            out[col] = out[col].map(lambda v: nullify(v) or "")
        else:
            out[col] = out[col].map(nullify)

    print("Corpus counts:")
    print(out["corpus"].value_counts().to_string())
    print("row_type counts (top):")
    print(out["row_type"].value_counts().head(10).to_string())
    return out


def ensure_empty_or_replace(conn, replace: bool, create_tables: bool) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT to_regclass('public.documents') AS documents,
                   to_regclass('public.lemma_rows') AS lemma_rows
            """
        )
        docs, rows = cur.fetchone()
        if docs is None or rows is None:
            if not create_tables:
                sys.exit(
                    "Tables documents / lemma_rows not found. "
                    "Run: reflex db migrate   OR   re-run with --create-tables"
                )
            print("Creating documents / lemma_rows ...")
            cur.execute(CREATE_TABLES_SQL)

        cur.execute("SELECT COUNT(*) FROM lemma_rows")
        (n_rows,) = cur.fetchone()
        if n_rows and not replace:
            sys.exit(
                f"lemma_rows already has {n_rows} rows. "
                "Re-run with --replace to truncate and reload."
            )
        if replace:
            print("TRUNCATE lemma_rows, documents RESTART IDENTITY CASCADE ...")
            cur.execute(
                "TRUNCATE TABLE lemma_rows, documents RESTART IDENTITY CASCADE"
            )
    conn.commit()


def upsert_documents(conn, df) -> dict[str, int]:
    docs = (
        df[["book", "corpus"]]
        .drop_duplicates(subset=["book"])
        .sort_values(["corpus", "book"])
    )
    # If a book label appears under two corpora, keep first and warn
    dup_books = df.groupby("book")["corpus"].nunique()
    multi = dup_books[dup_books > 1]
    if len(multi):
        print(
            f"WARNING: {len(multi)} book labels span multiple corpora; "
            "documents.book is unique — using first corpus seen."
        )

    records = list(docs.itertuples(index=False, name=None))
    print(f"Upserting {len(records)} documents ...")
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO documents (book, corpus) VALUES %s
            ON CONFLICT (book) DO UPDATE SET corpus = EXCLUDED.corpus
            """,
            records,
            page_size=1000,
        )
        cur.execute("SELECT id, book FROM documents")
        mapping = {book: doc_id for doc_id, book in cur.fetchall()}
    conn.commit()
    print(f"  documents in DB: {len(mapping)}")
    return mapping


def copy_lemma_rows(conn, df, book_to_id: dict[str, int], chunk_size: int) -> None:
    work = df.copy()
    work["document_id"] = work["book"].map(book_to_id)
    if work["document_id"].isna().any():
        missing = work.loc[work["document_id"].isna(), "book"].unique()[:20]
        sys.exit(f"Unmapped books (no document_id): {list(missing)}")

    work["document_id"] = work["document_id"].astype(int)
    total = len(work)
    print(f"COPY {total} lemma_rows in chunks of {chunk_size} ...")

    cols_sql = ", ".join(LEMMA_COPY_COLUMNS)
    # Use \N as NULL marker so empty strings (e.g. clean_lemma="") stay non-null.
    copy_sql = (
        f"COPY lemma_rows ({cols_sql}) FROM STDIN WITH (FORMAT CSV, NULL '\\N')"
    )

    for start in range(0, total, chunk_size):
        chunk = work.iloc[start : start + chunk_size]
        buf = io.StringIO()
        chunk[LEMMA_COPY_COLUMNS].to_csv(
            buf,
            index=False,
            header=False,
            na_rep=r"\N",
        )
        buf.seek(0)
        with conn.cursor() as cur:
            cur.copy_expert(copy_sql, buf)
        conn.commit()
        end = min(start + chunk_size, total)
        print(f"  {end}/{total} rows")

    print("COPY done.")


def refresh_document_counts(conn) -> None:
    """Store NNN / lexical-lemma totals on documents so the app catalog is cheap."""
    print("Refreshing documents.n_nnn / n_lemma ...")
    with conn.cursor() as cur:
        cur.execute("UPDATE documents SET n_nnn = 0, n_lemma = 0")
        cur.execute(
            """
            UPDATE documents AS d
            SET n_nnn = sub.n
            FROM (
                SELECT document_id, COUNT(*) AS n
                FROM lemma_rows
                WHERE row_type = 'NNN'
                GROUP BY document_id
            ) AS sub
            WHERE d.id = sub.document_id
            """
        )
        cur.execute(
            """
            UPDATE documents AS d
            SET n_lemma = sub.n
            FROM (
                SELECT document_id, COUNT(*) AS n
                FROM lemma_rows
                WHERE row_type = 'NNN'
                  AND clean_lemma IS NOT NULL
                  AND BTRIM(clean_lemma) <> ''
                  AND LOWER(BTRIM(clean_lemma)) <> 'nan'
                GROUP BY document_id
            ) AS sub
            WHERE d.id = sub.document_id
            """
        )
    conn.commit()


def verify(conn, df) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM documents")
        (n_docs,) = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM lemma_rows")
        (n_rows,) = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM lemma_rows WHERE row_type = 'NNN'")
        (n_nnn,) = cur.fetchone()
        cur.execute(
            """
            SELECT d.corpus, COUNT(*)
            FROM lemma_rows lr
            JOIN documents d ON d.id = lr.document_id
            GROUP BY d.corpus
            ORDER BY d.corpus
            """
        )
        by_corpus = cur.fetchall()
        cur.execute(
            """
            SELECT d.book, COUNT(*)
            FROM lemma_rows lr
            JOIN documents d ON d.id = lr.document_id
            WHERE d.book LIKE '4Q394%%'
            GROUP BY d.book
            ORDER BY d.book
            """
        )
        mmt = cur.fetchall()

    print("\nVerification")
    print(f"  documents: {n_docs}")
    print(f"  lemma_rows: {n_rows} (pkl had {len(df)})")
    print(f"  row_type=NNN: {n_nnn}")
    print("  by corpus:")
    for corpus, count in by_corpus:
        print(f"    {corpus}: {count}")
    print("  MMT-like books (4Q394%):")
    if mmt:
        for book, count in mmt:
            print(f"    {book}: {count}")
    else:
        print("    (none found — check book labels in pkl)")

    if n_rows != len(df):
        sys.exit(f"Row count mismatch: DB={n_rows} pkl={len(df)}")


def main() -> None:
    args = parse_args()
    db_url = resolve_db_url(args.db_url)

    try:
        import pandas as pd  # noqa: F401
    except ImportError:
        sys.exit("pandas is required. Install with: pip install pandas numpy")

    df = load_dataframe(args.pkl)
    df = prepare_frame(df)

    print("Connecting to database ...")
    conn = connect(db_url)
    try:
        ensure_empty_or_replace(
            conn, replace=args.replace, create_tables=args.create_tables
        )
        book_to_id = upsert_documents(conn, df)
        copy_lemma_rows(conn, df, book_to_id, chunk_size=args.chunk_size)
        refresh_document_counts(conn)
        verify(conn, df)
    finally:
        conn.close()

    print("\nIngest finished successfully.")


if __name__ == "__main__":
    main()
