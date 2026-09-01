"""Download the official World Bank FY23 climate-finance PDF and extract text."""
from __future__ import annotations

from pathlib import Path

import requests
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://thedocs.worldbank.org/en/doc/d4a3fae669d0274d249ef9331dffe73b-0020012024/original/FY23-Project-level-CCB-data.pdf"
SOURCE_DIR = ROOT / "data" / "source"
PDF_PATH = SOURCE_DIR / "FY23-Project-level-CCB-data.pdf"
TEXT_PATH = ROOT / "data" / "raw_fy23_pdf_text.txt"


def main() -> None:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    print("Downloading official World Bank FY23 project-level climate co-benefits PDF...")
    response = requests.get(SOURCE_URL, timeout=60, headers={"User-Agent": "world-bank-climate-finance-tracker/1.0"})
    response.raise_for_status()
    if not response.content.startswith(b"%PDF"):
        raise ValueError("Downloaded World Bank source does not look like a PDF")
    PDF_PATH.write_bytes(response.content)

    print("Extracting PDF text...")
    reader = PdfReader(str(PDF_PATH))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if not text.strip():
        raise ValueError("PDF text extraction returned no text")
    TEXT_PATH.write_text(text, encoding="utf-8")
    print(f"Saved {PDF_PATH}")
    print(f"Saved {TEXT_PATH}")
    print(f"Pages extracted: {len(reader.pages)}")


if __name__ == "__main__":
    main()
