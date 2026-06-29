"""Config-driven building-code loader (the team's Option B).

Constraint *values* live in JSON files under citycodes/, one per supported city,
so the Z3 verifier is city-agnostic: supporting a new jurisdiction is a new JSON
file, not a code change. This file turns a city's JSON into the in-memory
`SBCConstraints` object the verifier already consumes.

See DECISION_constraints.md for why we chose config-driven JSON over hardcoded
per-city logic.
"""
import json
from dataclasses import dataclass, fields
from pathlib import Path

from constraints import SBCConstraints

CODES_DIR = Path(__file__).parent / "citycodes"


@dataclass(frozen=True)
class CityCode:
    city: str
    source: str
    tolerance_ft: float
    sbc: SBCConstraints
    raw: dict


def available_cities() -> list[str]:
    return sorted(p.stem for p in CODES_DIR.glob("*.json"))


def load_city(name: str) -> CityCode:
    """Load citycodes/<name>.json into a CityCode (with an SBCConstraints)."""
    path = CODES_DIR / f"{name.lower()}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No code file for '{name}'. Available: {available_cities()}")
    data = json.loads(path.read_text())
    ext = data.get("exterior", {})
    valid = {f.name for f in fields(SBCConstraints)}
    unknown = set(ext) - valid
    if unknown:
        raise ValueError(f"{path.name}: unknown exterior keys {sorted(unknown)}; "
                         f"allowed {sorted(valid)}")
    sbc = SBCConstraints(**{k: float(v) for k, v in ext.items()})
    return CityCode(
        city=data.get("city", name),
        source=data.get("source", ""),
        tolerance_ft=float(data.get("tolerance_ft", 1e-6)),
        sbc=sbc,
        raw=data)


if __name__ == "__main__":
    for c in available_cities():
        cc = load_city(c)
        print(f"{cc.city:10s} front={cc.sbc.front_setback_ft:.0f} "
              f"side={cc.sbc.side_setback_ft:.1f} rear={cc.sbc.rear_setback_ft:.0f} "
              f"tree={cc.sbc.tree_buffer_ft:.0f} cover={cc.sbc.min_area_fraction_of_max:.2f} "
              f"tol={cc.tolerance_ft}")
