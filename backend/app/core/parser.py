import pdfplumber
from pathlib import Path


def extract_text_from_pdf(pdf_path: str | Path) -> dict:
    """Extract text and metadata from a PDF file."""
    pdf_path = Path(pdf_path)
    pages_text = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            pages_text.append({"page": i + 1, "text": text})

    full_text = "\n\n".join(
        f"[第{p['page']}页]\n{p['text']}" for p in pages_text if p["text"].strip()
    )

    return {
        "filename": pdf_path.name,
        "page_count": len(pages_text),
        "char_count": len(full_text),
        "full_text": full_text,
        "pages": pages_text,
    }


def extract_tables_from_pdf(pdf_path: str | Path) -> list[dict]:
    """Extract tables from a PDF file."""
    pdf_path = Path(pdf_path)
    tables = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_tables = page.extract_tables()
            for j, table in enumerate(page_tables):
                if table:
                    tables.append({
                        "page": i + 1,
                        "table_index": j,
                        "data": table,
                    })

    return tables
