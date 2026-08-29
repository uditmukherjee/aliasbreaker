"""Shared test helpers: sys.path wiring and cached case generation.

Stdlib + numpy only. Every test module performs the same sys.path prepend
independently so that individual files stay runnable on their own; this module
also does it so that `import helpers` is enough.
"""

import sys
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_SRC = Path(__file__).resolve().parents[1] / "src"

for _p in (str(_SRC), str(_TESTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402

from aliasbreaker.world import make_case  # noqa: E402

# Case generation is the dominant cost in this suite; cache aggressively so the
# whole run stays well under the runtime budget.
_CASE_CACHE = {}
_DEV_CACHE = []
_DEV_NEXT_SEED = [None]


def get_case(seed=1, **kwargs):
    """First admissible case at or after `seed` (cached by args)."""
    key = (seed, tuple(sorted(kwargs.items())))
    if key not in _CASE_CACHE:
        s = seed
        case = None
        while case is None and s < seed + 200:
            case = make_case(s, **kwargs)
            s += 1
        if case is None:
            raise RuntimeError(f"no admissible case from seed {seed}")
        _CASE_CACHE[key] = case
    return _CASE_CACHE[key]


def dev_cases(n=10, start_seed=101):
    """A cached list of `n` admissible dev cases with mixed sigma."""
    sigmas = [2.0, 3.0, 4.0, 5.0]
    if _DEV_NEXT_SEED[0] is None:
        _DEV_NEXT_SEED[0] = start_seed
    while len(_DEV_CACHE) < n and _DEV_NEXT_SEED[0] < start_seed + 400:
        case = make_case(_DEV_NEXT_SEED[0],
                         sigma=sigmas[len(_DEV_CACHE) % len(sigmas)])
        _DEV_NEXT_SEED[0] += 1
        if case is not None:
            _DEV_CACHE.append(case)
    if len(_DEV_CACHE) < n:
        raise RuntimeError(f"only generated {len(_DEV_CACHE)}/{n} dev cases")
    return _DEV_CACHE[:n]


def wrap_angle(a):
    """Wrap an angle to [0, 2*pi)."""
    return float(np.mod(a, 2.0 * np.pi))


def angle_diff(a, b):
    """Smallest absolute difference between two angles (radians)."""
    d = np.mod(a - b, 2.0 * np.pi)
    return float(min(d, 2.0 * np.pi - d))
