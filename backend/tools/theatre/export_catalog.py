"""One-off dev tool: write app/modules/theatre/data/catalog.json from the POC's processed German CSVs, using the
POC's own simulate.load_catalog() so the pools and cleaning times match it exactly. Needs pandas (dev only).

    python tools/theatre/export_catalog.py [--poc C:/Users/haris/work/OperationTheater/poc]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
OUT = BACKEND / "app" / "modules" / "theatre" / "data" / "catalog.json"
DEFAULT_POC = Path("C:/Users/haris/work/OperationTheater/poc")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--poc", type=Path, default=DEFAULT_POC, help="the POC folder that holds simulate.py")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    sys.path.insert(0, str(args.poc.resolve()))
    from simulate import load_catalog  # the POC module, reads ../data/processed/*.csv

    pools, cleaning = load_catalog()
    args.out.write_text(json.dumps({"pools": pools, "cleaning": cleaning}, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}: {sum(len(p) for p in pools.values())} procedures across {len(pools)} specialties")


if __name__ == "__main__":
    main()
