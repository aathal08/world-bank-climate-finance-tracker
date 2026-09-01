"""Parse text extracted from the official World Bank FY23 climate-finance PDF."""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROJECT_START_RE = re.compile(r"P\d{6}\s+\d+\b")
PROJECT_ID_INDEX_RE = re.compile(r"^(P\d{6})\s+(\d+)\s+(.*)$", re.DOTALL)
NUMBER_RE = re.compile(r"(\d+\.\d+)%\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)")
REGION_RE = re.compile(r"\b(AFE|AFW|EAP|ECA|LCR|MNA|SAR)\b")
GLOBAL_PRACTICES = (
    "AgricultureandFood",
    "DigitalDevelopment",
    "Education",
    "EnergyandExtractives",
    "EnvironmentNaturalResourcesandtheBlueEconomy",
    "FinanceCompetitivenessandInnovation",
    "Governance",
    "HealthNutritionandPopulation",
    "MacroeconomicsTradeandInvestment",
    "PovertyandEquity",
    "SocialProtectionandJobs",
    "SocialSustainabilityandInclusion",
    "Transport",
    "UrbanResilienceandLand",
    "Water",
)
GP_RE = re.compile("(?:" + "|".join(re.escape(x) for x in GLOBAL_PRACTICES) + ")")


def _normalize(text: str) -> str:
    """Normalize PDF whitespace so extraction layout does not affect parsing."""
    return re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip()


def _parse_project_block(block: str) -> dict:
    block = _normalize(block)
    match = PROJECT_ID_INDEX_RE.match(block)
    if not match:
        raise ValueError(f"Could not parse project block: {block[:120]!r}")

    pid, idx_text, remainder = match.groups()
    idx = int(idx_text)

    region_match = REGION_RE.search(remainder)
    if not region_match:
        raise ValueError(f"Could not find region code for {pid}")
    region = region_match.group(1)

    tail = remainder[region_match.end():].strip()
    gp_match = GP_RE.search(tail)
    if not gp_match:
        raise ValueError(f"Could not find global-practice label for {pid}")

    project_name = remainder[:region_match.start()].strip()
    country = tail[:gp_match.start()].strip()
    global_practice = gp_match.group(0)

    if not project_name or not country:
        raise ValueError(f"Incomplete metadata for {pid}: project={project_name!r}, country={country!r}")

    return {
        "project_id": pid,
        "index": idx,
        "project_name": project_name,
        "region_code": region,
        "country": country,
        "global_practice": global_practice,
    }


def parse(raw_text_path: Path):
    if not raw_text_path.exists():
        raise FileNotFoundError(
            f"Missing {raw_text_path}. Download the official World Bank PDF listed in "
            "data/source_urls.txt and extract its text before running this parser."
        )

    raw = raw_text_path.read_text(encoding="utf-8")

    # Do not depend on line boundaries. Different pypdf/runner versions can
    # place a whole PDF page on one line or wrap project fields differently.
    starts = list(PROJECT_START_RE.finditer(raw))
    projects = []
    for pos, start_match in enumerate(starts):
        end = starts[pos + 1].start() if pos + 1 < len(starts) else len(raw)
        projects.append(_parse_project_block(raw[start_match.start():end]))

    numbers = []
    for match in NUMBER_RE.finditer(raw):
        pct, adapt, mitig, total = match.groups()
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
