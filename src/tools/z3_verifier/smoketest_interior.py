"""Smoke test (self-contained): the interior verifier fires on the right rules.

Builds layouts by hand — no generator dependency. Run: python smoketest_interior.py
"""
from constraints import SBC
from interior_verifier_z3 import Room, InteriorLayout, check_interior

FOOT = (5.0, 20.0, 68.0, 78.0)
DOOR = (40.0, 20.0)

# A valid, fully-tiled 8-room plan (Living is the biggest room).
GOOD = [
    Room("Bedroom 1", "bedroom",   5, 20, 25, 50),
    Room("Living",    "living",   25, 20, 47, 50),
    Room("Kitchen",   "kitchen",  47, 20, 68, 50),
    Room("Corridor",  "corridor",  5, 50, 68, 54),
    Room("Bedroom 2", "bedroom",   5, 54, 30, 78),
    Room("Bath 1",    "bathroom", 30, 54, 43, 66),
    Room("Bath 2",    "bathroom", 30, 66, 43, 78),
    Room("Bedroom 3", "bedroom",  43, 54, 68, 78),
]


def lay(rooms):
    return InteriorLayout(footprint=FOOT, door=DOOR, rooms=tuple(rooms))


def has(viol, name):
    return name in {v.rule for v in viol}


def main():
    ok = True

    # 1) valid plan passes cleanly
    v = check_interior(lay(GOOD), SBC, mode="freeform", require_full_coverage=True)
    p = (len(v) == 0); ok &= p
    print(f"  {'PASS' if p else 'FAIL'}  valid 8-room plan (expect 0 violations)")
    for x in (v if not p else []):
        print("        ·", x.rule, "::", x.message)

    # 2) overlapping rooms -> no_overlap fires
    bad = list(GOOD); bad[0] = Room("Bedroom 1", "bedroom", 5, 20, 30, 50)  # overlaps Living
    v = check_interior(lay(bad), SBC, mode="freeform", require_full_coverage=False)
    p = has(v, "no_overlap"); ok &= p
    print(f"  {'PASS' if p else 'FAIL'}  overlapping rooms (expect no_overlap)")

    # 3) drop a bedroom -> room_count fires
    bad = [r for r in GOOD if r.name != "Bedroom 3"]
    v = check_interior(lay(bad), SBC, mode="freeform", require_full_coverage=False)
    p = has(v, "room_count"); ok &= p
    print(f"  {'PASS' if p else 'FAIL'}  missing a bedroom (expect room_count)")

    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
