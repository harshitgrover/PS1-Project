"""Smoke test: verify Z3 verifier fires on the right rules.

Not a full unit-test suite — just confirms each rule can fire and a known-good
house passes cleanly. Run:  python smoketest_verifier.py
"""

from plot import PLOT
from constraints import SBC
from verifier_z3 import HouseGeometry, check
from optimizer_z3 import compute_max_area

MAX_AREA, _ = compute_max_area(PLOT, SBC)


def case(name: str, house: HouseGeometry, expect_rules: set[str]) -> bool:
    vs = check(house, PLOT, SBC, max_legal_area=MAX_AREA)
    got = {v.rule for v in vs}
    ok = got == expect_rules
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"       expected: {sorted(expect_rules)}")
        print(f"       got     : {sorted(got)}")
        for v in vs:
            print(f"         · {v.rule}: {v.message}")
    return ok


def main() -> int:
    print("=== verifier_z3 smoke tests ===\n")
    passes = 0
    total = 0

    # Plot bbox is x [0,80], y [0,88]. Main body x [0,80], y [8,84]. Lot area
    # 6420 sq ft, so the 35% lot-coverage cap = 2247 sq ft and the 90%
    # utilization floor = 2022 sq ft. Known-good: 52 x 42 = 2184 sits between.
    good = HouseGeometry(
        corners=((12, 20), (64, 20), (64, 62), (12, 62)),
        door=(45, 20),  # south wall, within entry segment [35, 75]
    )
    total += 1; passes += case("known-good house", good, set())

    # Small-but-SBC-legal house: passes setbacks, FAILS area-coverage rule.
    # 40 x 45 = 1800 sq ft < 0.9 * 2247 = 2022 (and under the 2247 cap).
    small_legal = HouseGeometry(
        corners=((10, 25), (50, 25), (50, 70), (10, 70)),
        door=(40, 25),
    )
    total += 1; passes += case("small but SBC-legal (fails area)", small_legal,
                               {"min_area_coverage"})

    # Tree-buffer violation: push NE corner up into the notch zone.
    # Tree at (77.5, 86), trunk 1 + buffer 3 = 4 ft min distance.
    near_tree = HouseGeometry(
        corners=((10, 25), (76, 25), (76, 84), (10, 84)),
        door=(40, 25),
    )
    # x_max=76: east setback = 80-76 = 4 < 5 ✗
    # rear setback = 88 - 84 = 4 < 10 ✗
    # tree dist: nearest house pt (76, 84), tree at (77.5, 86):
    #   dx=1.5, dy=2  →  dist=2.5 < 4 ✗
    # NE corner (76, 84) sits on the boundary y=84 → point-in-polygon ambiguous.
    total += 1
    # (76,84) is inside the polygon (right strip extends to y=88), only the NW
    # corner (10,84) sits on the top edge → boundary ambiguity, that's the only
    # corner_inside_plot[i] that fires.
    passes += case("near tree (multi-violation)", near_tree,
                   {"rear_setback_north", "side_setback_east", "tree_buffer",
                    "corner_inside_plot[3]", "max_lot_coverage"})

    # Door on wrong wall (north instead of south)
    door_wrong = HouseGeometry(
        corners=((10, 25), (50, 25), (50, 70), (10, 70)),
        door=(40, 70),
    )
    total += 1
    # This house is also small (40x45=1800), so area-coverage fires too.
    passes += case("door on wrong wall", door_wrong,
                   {"door_on_south_wall", "min_area_coverage"})

    # House too small in both dimensions
    tiny = HouseGeometry(
        corners=((20, 25), (35, 25), (35, 38), (20, 38)),  # 15×13
        door=(27, 25),
    )
    total += 1
    # Tiny house also fails area-coverage.
    passes += case("house too small", tiny,
                   {"min_width_ew", "min_depth_ns",
                    "door_within_entry_segment", "min_area_coverage"})

    # Door outside entry segment (x=20 is in main body but outside [35, 75])
    # This house also fails area-coverage (40x45=1800 < 3654).
    door_outside = HouseGeometry(
        corners=((10, 25), (50, 25), (50, 70), (10, 70)),
        door=(20, 25),
    )
    total += 1
    passes += case("door outside entry segment", door_outside,
                   {"door_within_entry_segment", "min_area_coverage"})

    print(f"\n{passes}/{total} cases passed")
    return 0 if passes == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
