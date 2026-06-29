# Z3 Verifier — usage

The deterministic constraint checker for the house-design pipeline. A generator
proposes a layout; this tool **proves** it legal or rejects it with exact,
per-rule reasons. Same input → same verdict, every time.

---

## Install

```bash
pip install z3-solver          # the only dependency
python --version               # needs 3.10+
```

Then from this folder:

```bash
python smoketest_verifier.py   # should print "6/6 cases passed"
python smoketest_interior.py   # should print "ALL PASS"
```

If those pass, you're good.

---

## The three things it does

| Function | Takes | Returns | One-liner |
|---|---|---|---|
| `optimize_area(city)` | **just the city** (no house) | max buildable area + optimal corners | "What's the most I can legally build here?" |
| `verify_site(house, city)` | exterior shell `{corners, door}` | per-constraint pass/fail | "Is *this* footprint legal? if not, which rules and by how much?" |
| `verify_interior(layout, city)` | rooms `{footprint, door, rooms}` | per-rule violations | "Is *this* room layout legal?" |

### ⚠️ Important: what OPTIMIZE mode is (and isn't)

`optimize_area` does **not** take a house and "fix its errors." It takes **only
the plot + city**, declares the four house corners as symbolic Z3 variables, adds
every setback / size / coverage rule, and asks Z3 to **maximise the footprint
area**. The output is the *largest legal house* — a target, an upper bound.

- It does **not** read your vertices.
- It does **not** find or fix errors.

**Finding errors is `verify_site`'s job** — you pass it the vertices and it returns
exactly which constraints fail, with `measured` vs `required` numbers.

**Fixing errors is the *generator's* job**, not the verifier's. The loop is:
`generator proposes → verify_site finds the violations → generator regenerates
using those messages → verify again`, capped. The verifier is the **judge**; it
never mutates your layout (that's deliberate — it stays a trustworthy oracle).
`optimize_area` helps the generator by giving it the area target to aim for
(it must reach ≥ 90 % of the max).

---

## CLI

```bash
python verifier_tool.py cities                       # list supported cities
python verifier_tool.py optimize --city seattle      # max buildable area
python verifier_tool.py verify   --city seattle                  # demo: the optimal house, passes
python verifier_tool.py verify   --city seattle --layout house.json
python verifier_tool.py interior --city seattle --layout rooms.json --json
```

`house.json`:
```json
{ "corners": [[5,20],[75,20],[75,78],[5,78]], "door": [40,20] }
```

`rooms.json`:
```json
{ "footprint": [0,0,65,58], "door": [32,0],
  "rooms": [["Living","living",0,0,30,30], ["Bedroom 1","bedroom",30,0,50,18]] }
```

---

## Python API (call it from your code)

This is a **direct tool call** — import and call, no server needed (~0.01 s/check):

```python
import verifier_tool as vz

# 1) max buildable area for a city
vz.optimize_area("seattle")
# -> {"max_buildable_area_sqft": 2247.0, "optimal_corners": {...}, "coverage_threshold_sqft": 2022.3}

# 2) verify an exterior footprint
res = vz.verify_site({"corners": [[5,20],[75,20],[75,78],[5,78]], "door": [40,20]}, "seattle")
# -> {"ok": bool, "n_failed": int,
#     "constraints": [{"rule","pass","measured","required","message"}, ...],
#     "max_buildable_area_sqft": 2247.0, "tolerance_ft": 1e-6, "solve_time_s": 0.01}

# 3) react to failures (this is what your generator feeds back into its prompt)
if not res["ok"]:
    reasons = [c["message"] for c in res["constraints"] if not c["pass"]]

# 4) verify an interior layout (with optional dynamic ruleset)
vz.verify_interior({"footprint":[0,0,65,58], "door":[32,0], "rooms":[...]}, "seattle", interior_rules={"room_specs": {...}})
# -> {"ok": bool, "violations": [{"rule","measured","required","message"}, ...]}
```

---

## What it checks

**Exterior (13 rules):** front/rear/side setbacks · min width & depth · tree-buffer
keep-out · door egress & placement · corners inside plot · min utilization ≥ 90 % ·
**max lot coverage ≤ 35 %**.

**Interior (~25 rules):** room min areas & sides · full room program · no overlap /
no gaps · ensuite bath↔bedroom · bath not adjacent to kitchen or other bath ·
living near entry · **living > each bedroom** · **corridor ≤ 15 % of usable area** ·
every room connected.

---

## Cities / config

Constraints live in `citycodes/<city>.json` — a new jurisdiction is a new file,
**no code change**. `seattle.json` and `bellevue.json` ship as examples (they give
different max areas: Seattle 2247 vs Bellevue 2568 sq ft). The full JSON schema is
in `CONSTRAINT_SCHEMA.md`.

---

## Current scope (so you're not surprised)

- The tool currently verifies against **one built-in plot** (the standard L-shaped
  demo lot). The Python API accepts a `plot=` argument, but the CLI and the
  optimizer's lot bounds are tuned for that plot. **If you need to verify against
  your own lot vertices, tell me — that's a small extension** (plumb the plot
  geometry through as input).
- No auto-repair mode (by design). If you actually want a "nudge this failing house
  to the nearest legal one" helper, that can be added as a separate function —
  ask.
```
