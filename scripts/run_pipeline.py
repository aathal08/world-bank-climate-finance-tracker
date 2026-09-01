"""Run the complete World Bank -> ND-GAIN pipeline with validation."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RAW_TEXT = ROOT / "data" / "raw_fy23_pdf_text.txt"


def run_command(command: list[str]) -> None:
    print("$", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-download", action="store_true", help="Use an existing extracted World Bank text file.")
    args = parser.parse_args()

    if not args.skip_download:
        run_command([sys.executable, str(ROOT / "scripts" / "download_and_extract.py")])
    elif not RAW_TEXT.exists():
        raise FileNotFoundError(f"Missing {RAW_TEXT}; remove --skip-download to fetch the official source.")

    run_command([sys.executable, str(ROOT / "scripts" / "parse_projects.py")])
    run_command([sys.executable, str(ROOT / "scripts" / "merge_and_analyze.py")])
    run_command([sys.executable, str(ROOT / "scripts" / "validate_data.py")])


if __name__ == "__main__":
    main()
