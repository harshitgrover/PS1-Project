# Decision: constraint design = config-driven JSON (Option B)

**Open decision (from the acceptance checklist):** should building-code constraints
be (A) hardcoded per-city logic (a switch/case per supported city) or (B) a
config-driven JSON constraint file, modular and city-agnostic?

**Decision: B — config-driven JSON.**

## Why
1. **The product is explicitly multi-jurisdiction.** The architecture already has
   a Location Agent and a multi-city goal. With (A), every new city is a code
   change, a re-test, and a redeploy; with (B) it is a new JSON file — no code
   change to the verifier.
2. **Separation of policy from mechanism.** The Z3 solving logic (the *mechanism*)
   is stable and city-independent; only the *values* (setbacks, buffers,
   thresholds) change per city. JSON keeps policy editable by non-developers
   (e.g. a planner) and reviewable in version control.
3. **Zero per-city branching = fewer bugs.** No `if city == ...` ladder that can
   fall through or diverge; one code path verified once.
4. **Auditability.** Each city file carries a `source` field citing the code
   sections, which feeds the compliance report.

## How it is implemented
- `citycodes/<city>.json` holds the constraint values (and a per-city
  `tolerance_ft`). Two cities ship today — `seattle.json`, `bellevue.json` — with
  genuinely different setbacks, proving the verifier is city-agnostic.
- `codeloader.load_city(name)` validates the JSON keys against the constraint
  schema and returns an in-memory `SBCConstraints` the existing Z3 verifier
  already consumes — so no verifier code changed.
- `verifier_tool.py` is the single tool entry point; it loads the city, applies
  the configured tolerance, and runs verify / optimize.

## Scope note
Per-city JSON covers the **site / exterior** code (zoning setbacks, tree buffer,
coverage), which is where jurisdictions actually differ. The **interior** room
minimums follow the IRC, which is national, so they are kept shared (in
`rooms.py`); they can be moved to the same JSON schema if a city ever amends them.
