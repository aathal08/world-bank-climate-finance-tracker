"""Parse text extracted from the official World Bank FY23 climate-finance PDF.

Usage:
    python scripts/parse_projects.py data/raw_fy23_pdf_text.txt
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROJECT_RE = re.compile(r"^(P\d{6})\s+(\d+)\s+(.*?)\s+([A-Z]{3})\s+(.+?)\s+([A-Za-z].*)$")
NUMBER_RE = re.compile(r"^(\d+\.\d+)%\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)$")
HEADER_PREFIXES = (
    "PROJECTID", "CLIMATEFINANCE", "(%)", "ADAPTATION", "TOTAL", "COMMITMENT", "($M)"
)


def parse(raw_text_path: Path):
    if not raw_text_path.exists():
        raise FileNotFoundError(
            f"Missing {raw_text_path}. Download the official World Bank PDF listed in "
            "data/source_urls.txt and extract its text before running this parser."
        )

    lines = [line.rstrip("\n") for line in raw_text_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    projects, numbers = [], []

    for line in lines:
        if line.startswith(HEADER_PREFIXES):
            continue
        pm = PROJECT_RE.match(line)
        nm = NUMBER_RE.match(line)
        if pm:
            pid, idx, name, region, country, gp = pm.groups()
            projects.append({
                "project_id": pid,
                "index": int(idx),
                "project_name": name,
                "region_code": region,
                "country": country.strip(),
                "global_practice": gp.strip(),
            })
        elif nm:
            pct, adapt, mitig, total = nm.groups()
            numbers.append({
                "climate_finance_pct": float(pct),
                "adaptation_musd": float(adapt.replace(",", "")),
                "mitigation_musd": float(mitig.replace(",", "")),
                "total_commitment_musd": float(total.replace(",", "")),
            })

    if len(projects) != len(numbers):
        raise ValueError(f"Parser mismatch: {len(projects)} project rows vs {len(numbers)} numeric rows")
    if len(projects) != 322:
        raise ValueError(f"Expected 322 FY23 project rows, found {len(projects)}")

    indices = [p["index"] for p in projects]
    if indices != list(range(1, 323)):
        raise ValueError("Project indices are not the expected sequential 1..322; refusing to silently pair rows.")
    ids = [p["project_id"] for p in projects]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate project IDs detected during parsing.")

    rows = [{**project, **number} for project, number in zip(projects, numbers)]
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_text", type=Path, nargs="?", default=ROOT / "data" / "raw_fy23_pdf_text.txt")
    args = parser.parse_args()

    rows = parse(args.raw_text)
    out_path = ROOT / "data" / "fy23_climate_projects.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Parsed {len(rows)} projects -> {out_path}")


if __name__ == "__main__":
    main()
