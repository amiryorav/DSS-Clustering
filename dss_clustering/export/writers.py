"""Table and plot export writers (spec §8.11)."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Iterable

from plotly.graph_objects import Figure


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _safe_stem(stem: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem.strip())
    return cleaned.strip("_") or "export"


def write_csv(rows: Iterable[dict[str, Any]], stem: str) -> tuple[bytes, str, str]:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["rank", "signature", "score"])
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "rank": row.get("rank", ""),
                "signature": row.get("signature", ""),
                "score": row.get("score", ""),
            }
        )
    data = buffer.getvalue().encode("utf-8-sig")
    return data, f"{_safe_stem(stem)}_{_stamp()}.csv", "text/csv"


def write_count_matrix_csv(
    matrix: Any,
    document_ids: Iterable[int],
    signatures: Iterable[str],
    stem: str,
    *,
    document_labels: dict[int, str] | None = None,
) -> tuple[bytes, str, str]:
    """Write the unscaled book × signature count matrix without densifying it."""
    ids = [int(document_id) for document_id in document_ids]
    columns = [str(signature) for signature in signatures]
    if tuple(matrix.shape) != (len(ids), len(columns)):
        raise ValueError("Count matrix dimensions do not match its metadata.")

    labels = document_labels or {}
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["document_id", "book", *columns])
    for row_index, document_id in enumerate(ids):
        row = matrix.getrow(row_index).toarray().ravel() if hasattr(matrix, "getrow") else matrix[row_index]
        writer.writerow(
            [
                document_id,
                labels.get(document_id, ""),
                *(int(value) for value in row),
            ]
        )
    data = buffer.getvalue().encode("utf-8-sig")
    return data, f"{_safe_stem(stem)}_{_stamp()}.csv", "text/csv"


def write_excel(rows: Iterable[dict[str, Any]], stem: str) -> tuple[bytes, str, str]:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "features"
    ws.append(["rank", "signature", "score"])
    for row in rows:
        ws.append([row.get("rank", ""), row.get("signature", ""), row.get("score", "")])
    buffer = io.BytesIO()
    wb.save(buffer)
    return (
        buffer.getvalue(),
        f"{_safe_stem(stem)}_{_stamp()}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def write_pdf_table(
    rows: Iterable[dict[str, Any]],
    stem: str,
    *,
    title: str = "Feature table",
) -> tuple[bytes, str, str]:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(title, styles["Heading2"]),
        Spacer(1, 12),
    ]
    data = [["#", "Signature", "Score"]]
    for row in rows:
        data.append(
            [
                str(row.get("rank", "")),
                str(row.get("signature", "")),
                f"{float(row.get('score', 0.0)):.6g}",
            ]
        )
    table = Table(data, colWidths=[40, 340, 100])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    return buffer.getvalue(), f"{_safe_stem(stem)}_{_stamp()}.pdf", "application/pdf"


def write_plot_image(
    fig: Figure,
    stem: str,
    fmt: str,
    *,
    width: int = 1200,
    height: int = 800,
) -> tuple[bytes, str, str]:
    fmt = fmt.lower()
    if fmt not in ("png", "pdf"):
        raise ValueError(f"Unsupported plot format: {fmt}")
    data = fig.to_image(format=fmt, width=width, height=height, scale=2)
    mime = "image/png" if fmt == "png" else "application/pdf"
    return data, f"{_safe_stem(stem)}_{_stamp()}.{fmt}", mime


def write_table(
    rows: Iterable[dict[str, Any]],
    fmt: str,
    stem: str,
    *,
    title: str = "Feature table",
) -> tuple[bytes, str, str]:
    fmt = fmt.lower()
    if fmt == "csv":
        return write_csv(rows, stem)
    if fmt == "excel":
        return write_excel(rows, stem)
    if fmt == "pdf":
        return write_pdf_table(rows, stem, title=title)
    raise ValueError(f"Unsupported table format: {fmt}")
