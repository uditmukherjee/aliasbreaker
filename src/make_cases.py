"""Generate case fixtures to disk.

Usage:
  python src/make_cases.py dev     -> data/cases/dev/*.json (12 shakedown cases,
                                      same seeds/knobs as the feasibility run)

The final evaluation set is generated separately at freeze time per
docs/evaluation-charter.md §5 (predeclared strata, fresh seeds).
"""

import json
import sys
from pathlib import Path

from aliasbreaker.world import make_case, case_to_dict

DEV_KNOBS = [{"sigma": 2.0}, {"sigma": 3.0}, {"sigma": 4.0}, {"sigma": 5.0}]


def gen_dev(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    cases, seed = [], 100
    while len(cases) < 12 and seed < 400:
        seed += 1
        case = make_case(seed, **DEV_KNOBS[len(cases) % len(DEV_KNOBS)])
        if case is not None:
            cases.append(case)
    for case in cases:
        path = out_dir / f"{case.case_id}.json"
        path.write_text(json.dumps(case_to_dict(case), indent=1))
        print(f"wrote {path}  (candidates={len(case.candidates)}, "
              f"slots={len(case.slot_t)})")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "dev"
    root = Path(__file__).resolve().parents[1]
    if which == "dev":
        gen_dev(root / "data" / "cases" / "dev")
    else:
        raise SystemExit(f"unknown set: {which}")
