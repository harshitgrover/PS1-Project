# Constraint JSON — schema contract

**Producer:** Constraint Engine (+ Entity Constraint Engine)
**Consumers:** Site/Floor Plan **Generator** *and* Z3 **Verifier** — same JSON, one source of truth (no drift).

One JSON object **per jurisdiction**. Distances in **feet**, areas in **ft²**, ratios as
**fractions 0–1** (not percents). Coordinate origin = **plot SW corner**, same frame the
Site Plan Generator emits footprints in.

> Fields marked **🆕** are new vs. what the verifier consumes today — they come from your
> side, and I'm adding the matching checks. Everything else the verifier already enforces.

---

## Top level

| key | type | meaning |
|---|---|---|
| `jurisdiction` | string | e.g. `"Seattle Downtown NR"` |
| `schema_version` | string | bump on any shape change |
| `source` | string | code citations (for the Reviewer agent + audit log) |
| `status` | `"loaded"` \| `"no_data"` | **🆕** if `"no_data"`, verifier fails **loudly** — never defaults to a wrong ruleset (matches the Location Zoning acceptance criterion) |
| `tolerance_ft` | number | float tolerance, e.g. `1e-6` |
| `exterior` | object | site/zoning rules (below) |
| `interior` | object | room program + spatial rules (below) |
| `descriptions` | object | **🆕** mapping of constraint keys to their plain-language legal definitions |
| `constraint_levels` | object | **🆕** mapping of constraint keys to their enforcement level (`hard` or `soft`) |

## `exterior`

| key | type | meaning |
|---|---|---|
| `front_setback_ft` | number | min distance footprint→front lot line |
| `rear_setback_ft` | number | rear |
| `side_setback_ft` | number | each side |
| `min_house_width_ft` | number | min footprint width |
| `min_house_depth_ft` | number | min footprint depth |
| `door_corner_margin_ft` | number | door must be ≥ this from any corner |
| `max_lot_coverage_fraction` | number | **🆕** legal **max**: `footprint_area / lot_area ≤ this` (e.g. `0.35`) |
| `min_area_fraction_of_max` | number | efficiency **min**: `footprint_area / buildable_envelope ≥ this` (e.g. `0.90`) |
| `tree_protection_zone` | object | **🆕** `{ "type": "polygon", "coordinates": [[x,y],…] }` — footprint must not intersect it; `coordinates: []` if none. (Today I model a buffer-around-a-point; switching to your polygon.) |

> **Two different coverage numbers — don't conflate:** `max_lot_coverage_fraction` is the
> legal ceiling (zoning). `min_area_fraction_of_max` is the "don't under-build" floor
> (efficiency). The buildable envelope = what's left after setbacks **and** the coverage cap.

## `interior`

| key | type | meaning |
|---|---|---|
| `required_rooms` | object | `{ "living":1, "kitchen":1, "corridor":1, "bedroom":3, "bathroom":2 }` — exact program |
| `room_specs` | object | per kind → `{ min_area_ft2, min_side_ft, max_side_ft (null=uncapped), habitable }` |
| `adjacency_rules` | array | machine-readable (below) — **not** prose |
| `area_rules` | array | **🆕** includes `{"rule":"living_gt_each_bedroom"}` |
| `corridor_max_fraction_of_usable` | number | **🆕** total corridor area / usable area ≤ this (e.g. `0.15`) |
| `coverage_tol_fraction` | number | rooms must tile footprint within ± this (e.g. `0.05`) |

### `adjacency_rules` — each element
| field | values |
|---|---|
| `a`, `b` | room kinds, or `"entry"` |
| `relation` | `"ensuite_required"` \| `"must_touch"` \| `"must_not_touch"` \| `"near"` |
| `min_shared_wall_ft` | for touch/ensuite |
| `max_dist_ft` | for `near` |

---

## Full example (the shape to emit)

```json
{
  "jurisdiction": "Seattle Downtown NR",
  "schema_version": "1.0",
  "source": "SDCI Tip 320; SMC 25.11.090; IRC R304/R305",
  "status": "loaded",
  "tolerance_ft": 1e-6,
  "exterior": {
    "front_setback_ft": 15.0,
    "rear_setback_ft": 15.0,
    "side_setback_ft": 5.0,
    "min_house_width_ft": 20.0,
    "min_house_depth_ft": 20.0,
    "door_corner_margin_ft": 2.0,
    "max_lot_coverage_fraction": 0.35,
    "min_area_fraction_of_max": 0.90,
    "tree_protection_zone": { "type": "polygon", "coordinates": [] }
  },
  "interior": {
    "required_rooms": { "living": 1, "kitchen": 1, "corridor": 1, "bedroom": 3, "bathroom": 2 },
    "room_specs": {
      "living":   { "min_area_ft2": 70, "min_side_ft": 7, "max_side_ft": null, "habitable": true },
      "kitchen":  { "min_area_ft2": 70, "min_side_ft": 7, "max_side_ft": null, "habitable": true },
      "bedroom":  { "min_area_ft2": 70, "min_side_ft": 7, "max_side_ft": null, "habitable": true },
      "bathroom": { "min_area_ft2": 25, "min_side_ft": 5, "max_side_ft": 15,   "habitable": false },
      "corridor": { "min_area_ft2": 16, "min_side_ft": 4, "max_side_ft": null, "habitable": false }
    },
    "adjacency_rules": [
      { "a": "bathroom", "b": "bedroom",  "relation": "ensuite_required", "min_shared_wall_ft": 4.0 },
      { "a": "bathroom", "b": "kitchen",  "relation": "must_not_touch" },
      { "a": "bathroom", "b": "bathroom", "relation": "must_not_touch" },
      { "a": "kitchen",  "b": "living",   "relation": "must_touch", "min_shared_wall_ft": 2.5 },
      { "a": "living",   "b": "entry",    "relation": "near", "max_dist_ft": 2.0 }
    ],
    "area_rules": [
      { "rule": "living_gt_each_bedroom" },
      { "rule": "bathroom_lt_served_bedroom" }
    ],
    "corridor_max_fraction_of_usable": 0.15,
    "coverage_tol_fraction": 0.05
  },
  "descriptions": {
    "front_setback_ft": "Minimum front property line setback in feet.",
    "min_area_ft2": "Minimum area in square feet for the room."
  },
  "constraint_levels": {
    "front_setback_ft": "hard",
    "min_area_ft2": "hard",
    "requires_egress": "soft"
  }
}
```

---

## Forward-compatibility (please confirm)
Your spec says new constraint types must be addable *without touching agent code*. So:
**unknown keys = the verifier warns and ignores, never crashes.** That lets you grow the
list (fire egress, mechanical room sizing…) and I enforce them only once we've agreed the
check. I'll relax my loader to this rule.
