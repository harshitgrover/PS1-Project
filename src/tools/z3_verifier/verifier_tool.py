"""Z3 Verifier — the deterministic constraint-checking tool.

This is the single, stable entry point the product calls. It is a *direct tool
call*: generators (Site Plan Agent, etc.) import `verify_site` / `optimize_area`
and call them straight, with no Agent-Manager routing in between. It is also a
standalone CLI for local debugging:

    python verifier_tool.py cities
    python verifier_tool.py optimize  --city seattle
    python verifier_tool.py verify    --city seattle [--layout house.json] [--json]
    python verifier_tool.py interior  --city seattle  --layout interior.json [--json]

Guarantees (see DECISION_constraints.md and the acceptance checklist):
  * provable pass/fail per constraint (Z3), never a probabilistic guess;
  * an "optimize" mode that computes the provable maximum buildable area;
  * a configurable floating-point tolerance (loaded per city) so near-exact
    matches do not produce false failures;
  * city-agnostic, config-driven constraints (JSON under citycodes/);
  * reports solve time so the < 5 s budget is verifiable.
"""
import argparse
import json
import sys
from time import perf_counter

import verifier_z3
from verifier_z3 import HouseGeometry, check
from optimizer_z3 import compute_max_area
from interior_verifier_z3 import Room, InteriorLayout, check_interior
from plot import PLOT
from codeloader import load_city, available_cities

# Canonical exterior rule set, so a clean run reports every constraint as PASS
# (not just the failures). Matches the rule names emitted by verifier_z3.check.
EXTERIOR_RULES = [
    "front_setback_south", "rear_setback_north", "side_setback_west",
    "side_setback_east", "min_width_ew", "min_depth_ns", "tree_buffer",
    "door_on_south_wall", "door_corner_margin", "door_within_entry_segment",
    "corner_inside_plot", "min_area_coverage", "max_lot_coverage",
]


def _house(obj) -> HouseGeometry:
    if isinstance(obj, HouseGeometry):
        return obj
    return HouseGeometry(
        corners=tuple((float(x), float(y)) for x, y in obj["corners"]),
        door=(float(obj["door"][0]), float(obj["door"][1])))


def optimize_area(city: str, plot=PLOT) -> dict:
    """OPTIMIZE mode — provable maximum buildable area for this city/plot."""
    cc = load_city(city)
    t0 = perf_counter()
    area, corners = compute_max_area(plot, cc.sbc)
    dt = perf_counter() - t0
    return {
        "city": cc.city, "mode": "optimize",
        "max_buildable_area_sqft": round(area, 1),
        "optimal_corners": {k: round(v, 2) for k, v in corners.items()},
        "coverage_threshold_sqft": round(area * cc.sbc.min_area_fraction_of_max, 1),
        "solve_time_s": round(dt, 4),
    }


def verify_site(house, city: str | None = None, plot=PLOT, sbc=None, tolerance_ft=1e-6) -> dict:
    """Verify a site/exterior layout. Returns a provable pass/fail per constraint."""
    if city:
        cc = load_city(city)
        sbc = cc.sbc
        tolerance_ft = cc.tolerance_ft
    elif sbc is None:
        raise ValueError("Must provide either a city or an sbc object")

    verifier_z3.FLOAT_TOL = tolerance_ft           # apply the configured tolerance
    geom = _house(house)
    t0 = perf_counter()
    max_area, _ = compute_max_area(plot, sbc)
    violations = check(geom, plot, sbc, max_legal_area=max_area)
    dt = perf_counter() - t0

    vmap = {}
    for v in violations:
        vmap.setdefault(v.rule.split("[")[0], v)      # group corner_inside_plot[i]
    constraints = []
    for r in EXTERIOR_RULES:
        v = vmap.get(r)
        constraints.append({
            "rule": r, "pass": v is None,
            "measured": round(v.measured_ft, 3) if v else None,
            "required": round(v.required_ft, 3) if v else None,
            "message": v.message if v else "satisfied",
        })
    return {
        "city": city if city else "dynamic", "mode": "site/exterior", "ok": not violations,
        "n_constraints": len(EXTERIOR_RULES),
        "n_failed": sum(1 for c in constraints if not c["pass"]),
        "constraints": constraints,
        "max_buildable_area_sqft": round(max_area, 1),
        "tolerance_ft": tolerance_ft,
        "solve_time_s": round(dt, 4),
    }


def verify_interior(layout: dict, city: str | None = None, mode: str = "freeform", sbc=None, tolerance_ft=1e-6, interior_rules: dict | None = None) -> dict:
    """Verify an interior layout (IRC room rules, shared across cities)."""
    if city:
        cc = load_city(city)
        sbc = cc.sbc
        tolerance_ft = cc.tolerance_ft
    elif sbc is None:
        raise ValueError("Must provide either a city or an sbc object")

    verifier_z3.FLOAT_TOL = tolerance_ft
    lay = InteriorLayout(
        footprint=tuple(layout["footprint"]), door=tuple(layout["door"]),
        rooms=tuple(Room(*r) for r in layout["rooms"]))
    t0 = perf_counter()
    viol = check_interior(lay, sbc, mode=mode, require_full_coverage=False, interior_rules=interior_rules)
    dt = perf_counter() - t0
    return {
        "city": city if city else "dynamic", "mode": f"interior/{mode}", "ok": not viol,
        "n_failed": len({v.rule for v in viol}),
        "violations": [{"rule": v.rule, "measured": round(v.measured_ft, 3),
                        "required": round(v.required_ft, 3), "message": v.message}
                       for v in viol],
        "tolerance_ft": tolerance_ft,
        "solve_time_s": round(dt, 4),
    }


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #
def _print_site(res):
    print(f"\n  Z3 VERIFIER — {res['city']} — site/exterior")
    print(f"  tolerance = {res['tolerance_ft']} ft   "
          f"max buildable = {res['max_buildable_area_sqft']} sq ft")
    print(f"  {'constraint':27s}{'result':8s}{'measured':>11s}{'required':>11s}")
    print("  " + "-" * 57)
    for c in res["constraints"]:
        m = "" if c["measured"] is None else f"{c['measured']}"
        rq = "" if c["required"] is None else f"{c['required']}"
        print(f"  {c['rule']:27s}{'PASS' if c['pass'] else 'FAIL':8s}{m:>11s}{rq:>11s}")
    verdict = "ALL CONSTRAINTS SATISFIED" if res["ok"] else f"{res['n_failed']} CONSTRAINT(S) FAILED"
    print(f"  " + "-" * 57)
    print(f"  => {verdict}   ({res['solve_time_s']}s, "
          f"{'OK' if res['solve_time_s'] < 5 else 'SLOW'} vs 5s budget)\n")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Z3 deterministic layout verifier")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("cities", help="list supported cities")
    po = sub.add_parser("optimize", help="provable maximum buildable area")
    po.add_argument("--city", required=True)
    pv = sub.add_parser("verify", help="verify a site/exterior layout")
    pv.add_argument("--city", required=True)
    pv.add_argument("--layout", help="house JSON {corners:[[x,y]x4], door:[x,y]}")
    pv.add_argument("--json", action="store_true", help="print raw JSON")
    pi = sub.add_parser("interior", help="verify an interior layout")
    pi.add_argument("--city", required=True)
    pi.add_argument("--layout", required=True)
    pi.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    if a.cmd == "cities":
        print("Supported cities:", ", ".join(available_cities()))
        return 0

    if a.cmd == "optimize":
        res = optimize_area(a.city)
        print(json.dumps(res, indent=2))
        return 0

    if a.cmd == "verify":
        if a.layout:
            house = json.loads(open(a.layout).read())
        else:                                    # demo: the Z3-optimal house (should pass)
            opt = optimize_area(a.city)["optimal_corners"]
            house = {"corners": [[opt["x_min"], opt["y_min"]], [opt["x_max"], opt["y_min"]],
                                 [opt["x_max"], opt["y_max"]], [opt["x_min"], opt["y_max"]]],
                     "door": [(opt["x_min"] + opt["x_max"]) / 2, opt["y_min"]]}
        res = verify_site(house, a.city)
        print(json.dumps(res, indent=2) if a.json else "", end="")
        if not a.json:
            _print_site(res)
        return 0 if res["ok"] else 1

    if a.cmd == "interior":
        res = verify_interior(json.loads(open(a.layout).read()), a.city)
        print(json.dumps(res, indent=2))
        return 0 if res["ok"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
