# Pipeline I/O reference — exact input/output format per agent

This is the companion reference to the pipeline flowchart. The flowchart shows *order*; this shows *exact data shape* — what every agent receives and what it must hand off.

All inter-agent messages use **JSON-RPC**, validated by **Pydantic** at the agent boundary. If an agent's output fails Pydantic validation, that agent's own LLM must reformat it before the output ever reaches the Agent Manager — invalid JSON should never leave an agent's own scope.

Tool calls (e.g. Site Plan Generator calling the Z3 Verifier tool directly) are **not** Agent Manager traffic — those stay inside the calling agent's own code and can use whatever format that agent's code needs internally.

---

## 1. Planner / Customer Support Agent — Prem (primary), Swara

**Input:** raw free-text user prompt (string)

**Output (to Agent Manager):**
```json
{
  "role": "planner",
  "status": "brief_ready" | "needs_clarification",
  "brief": {
    "square_footage": 2400,
    "bhk_count": 3,
    "budget_range": [400000, 550000],
    "location": {
      "city": "Redmond",
      "state": "WA",
      "zip": "98052"
    },
    "template_id": "3bhk_standard" | null
  },
  "clarification_question": "string, only present if status = needs_clarification"
}
```

**Rule:** never fills `location` with a guess. If a city name is ambiguous (e.g. "Redmond" — WA or CA), `status` must be `needs_clarification` until ZIP-level resolution is reached.

---

## 2. Agent Manager — Swara (primary), Prem

**Input:** every message from every other agent, in JSON-RPC envelope:
```json
{
  "jsonrpc": "2.0",
  "method": "agent.report_status" | "agent.request_input" | "agent.output_ready",
  "params": { "agent_id": "string", "payload": {} },
  "id": "request_id"
}
```

**Output:** routes the inner `payload` to the next agent in sequence, after Pydantic schema validation. Also emits a simplified status object to the Planner/Customer Support Agent on every state change:
```json
{
  "pipeline_stage": "verifying_footprint",
  "user_facing_message": "Checking your design against local building rules...",
  "percent_complete": 35
}
```

**Rule:** never forwards raw internal agent names, stack traces, or tool names to the user-facing message field.

---

## 3. Location Zoning Agent — Kavya (primary), Prem

**Input:**
```json
{ "city": "Redmond", "state": "WA", "zip": "98052" }
```

**Output:**
```json
{
  "jurisdiction": "Redmond, WA",
  "setbacks_ft": { "front": 20, "rear": 15, "side": 10 },
  "max_lot_coverage_pct": 35,
  "tree_protection_zones": [ { "polygon": [[x,y], [x,y], ...] } ]
}
```

**Rule:** if no constraint data exists for the resolved ZIP, return `"jurisdiction": null` with an explicit `"error": "no_constraint_data"` field — never silently substitute a default ruleset.

---

## 4. Constraint Agent + Entity Constraint Engine — Harshit (primary), Dhwani / Anshul

**Input:** jurisdiction data from Location Zoning Agent (above)

**Output:**
```json
{
  "entity_rules": {
    "bedroom": { "min_area_sqft": 70, "must_connect_to": ["hallway"] },
    "bathroom": { "min_area_sqft": 35, "not_adjacent_to": ["bathroom", "kitchen"] },
    "kitchen": { "min_area_sqft": 80 },
    "living_room": { "min_area_relative": "> any bedroom" }
  },
  "jurisdiction_overrides": { "...same shape as above, only differing fields" }
}
```

**Rule:** this is the single source of truth — both the Floor Plan Generator and the Verifier Agent must query this exact same object, never a locally cached copy.

---

## 5. Guardrail Tools — Swara

**Input:** the raw planner brief (before generation starts)

**Output:**
```json
{ "allowed": true | false, "reason": "string, only if allowed = false" }
```

**Rule:** runs before the Constraint Agent's geometric checks, not after. A blocked request never reaches the generator agents.

---

## 6. Topography (tool, conditional) — Devam (primary), Marjit

**Input:** lot coordinates from Location Toolkit

**Output:**
```json
{
  "elevation_data_available": true,
  "max_elevation_diff_ft": 14,
  "contours": [ { "elevation_ft": 120, "polygon": [[x,y], ...] } ]
}
```

**Rule:** if `elevation_data_available` is false, every downstream agent must treat the lot as flat explicitly — not by omission.

---

## 7. Site Plan Generator Agent — Devam (primary), Ayush

**Input:** combined ruleset (setbacks, coverage, tree zones) + topography data if present

**Output:**
```json
{
  "footprint_polygon": [[x,y], [x,y], [x,y], [x,y]],
  "lot_coverage_pct": 33.2,
  "buildable_area_sqft": 2640
}
```

**Tool call (internal, not Agent Manager traffic):** calls Z3 Verifier directly to check this output before returning it.

---

## 8. Verifier Agent + Z3 Verifier (tool) — Devam/Harshit (Verifier Agent); Ayush (Z3 Verifier)

**Input:** any generator's coordinate output (footprint or room layout) + the constraint ruleset

**Output, on pass:**
```json
{ "result": "pass", "verified_coordinates": { "...same shape as input" } }
```

**Output, on fail:**
```json
{
  "result": "fail",
  "violations": [
    { "constraint": "setback_rear", "current_value": 12, "required_value": 15,
      "fix_suggestion": "move house_top_y from 61 to 65" }
  ]
}
```

**Rule:** `fix_suggestion` is diagnostic only — the Verifier never returns corrected coordinates directly, or the Generator↔Verifier loop collapses into one step.

---

## 9. Floor Plan Generator Agent — Prasad (primary), Devank

**Input:** `verified_coordinates` (the footprint) + entity rules from Constraint Agent

**Output:**
```json
{
  "rooms": [
    { "id": "bed_1", "type": "bedroom", "polygon": [[x,y],...], "area_sqft": 140 },
    { "id": "bath_1", "type": "bathroom", "polygon": [[x,y],...], "area_sqft": 45 }
  ],
  "corridor_area_sqft": 180,
  "total_area_sqft": 2400
}
```

**Tool call (internal):** hands this to Json Extractor before it goes to the Verifier Agent.

---

## 10. Json Extractor (tool) — Devank (primary), Prasad

**Input:** raw generator output (any shape, possibly malformed)

**Output (clean JSON, passed to Verifier):**
```json
{ "rooms": [ "...same shape as Floor Plan Generator output above, validated and re-typed" ] }
```

**Output (on malformed input):**
```json
{ "error": "malformed_generator_output", "raw_input_excerpt": "string" }
```

**Open question (unresolved as of latest meeting):** scope vs. Pydantic-level validation needs clarifying with Chandra — may overlap.

---

## 11. Multi-floor Generator Agent (conditional) — Nitesh

**Input:** verified floor 1 layout + Elevation Agent's foundation height data

**Output:**
```json
{
  "floors": [
    { "floor_number": 1, "rooms": ["...same room shape as Floor Plan Generator"] },
    { "floor_number": 2, "rooms": ["..."], "wall_alignment_check": "pass" | "fail" }
  ],
  "converged": true | false
}
```

**Rule:** if `converged` is false after the retry cap, the Agent Manager must surface this to the user — never silently return a mismatched-floor design.

---

## 12. Elevation Agent — Ayush (primary), Devam

**Input:** topography data + footprint

**Output:**
```json
{
  "foundation_strategy": "dig_down" | "elevate_fill",
  "foundation_height_ft": 3.5,
  "reasoning": "string"
}
```

---

## 13. Livability Agent (parallel, non-blocking) — Aadi (primary), Shreyas

**Input:** verified room layout

**Output:**
```json
{
  "room_scores": [
    { "room_id": "bed_1", "daylight_score": 0.82, "airflow_score": 0.71 }
  ]
}
```

**Rule:** never blocks the pipeline — this is informational, attached to the final report, not a pass/fail gate.

---

## 14. Side Views Agent — Dhwani

**Input:** verified floor + elevation data

**Output:** DXF-layer-ready coordinate set for front/rear/side facades (same coordinate format as floor plan, tagged `"view_type": "elevation"`)

## 15. Roof Plan Agent — Ojas

**Input:** top-floor footprint + elevation data

**Output:** roof polygon set tagged `"view_type": "roof"`, must exactly match top-floor boundary

## 16. DXF Generator (tool) — Harshit (primary), Devam

**Input:** any verified coordinate set tagged with a `view_type` (floor / elevation / roof)

**Output:** `.dxf` binary file + manifest:
```json
{ "file_path": "string", "layers": ["floor_1", "elevation_front", "roof"] }
```

**Rule:** only ever called on already-verified (post Z3 pass) coordinates.

## 17. DXF file reader (tool) — Sidak (primary), Saksham

**Input:** `.dxf` file path

**Output:** same coordinate JSON shape that produced it (round-trip, zero data loss)

## 18. CAD file reader (tool) — Siddh (primary), Devam

**Input:** external CAD file (for "similar to known layout" requests)

**Output:** ingested polygon/room data in the standard coordinate format, fed back into Site Plan / Floor Plan Generators as a reference seed

## 19. PDF generation (report) — Ayush (primary), Anirudh

**Input:** all verified outputs (floor plan, elevations, roof, Reviewer's sign-off record)

**Output:** `.pdf` file meeting: min 300 DPI, every door/window labeled, N/S/E/W directional labels present, formatted per CommonFloor/MagicBricks-style detailing conventions

---

## 20. Reviewer (City) Agent — Siddh (primary), Rohan

**Input:** complete output package (floor plan + elevations + roof + PDF draft)

**Output:**
```json
{
  "element_signoffs": [
    { "element_id": "wall_north_1", "approved": true },
    { "element_id": "setback_rear", "approved": false, "reason": "string" }
  ],
  "overall_status": "approved" | "rejected"
}
```

**Rule:** any environmental/zoning violation results in automatic `"approved": false` — no override path.

---

## 21. UI + Notification Service

**Input:** Agent Manager's simplified status stream + Reviewer's sign-off result

**Output:** persona-scoped notifications — client, architect/HITL, and city reviewer each receive only the events relevant to their role; never cross-leaked.

---

## Always-on background services (queried on demand, not pipeline steps)

| Service | Input | Output |
|---|---|---|
| Database (Supabase + Qdrant) | read/write keyed by user_id + session_id | persisted records; vector search returns ranked matches with similarity score |
| Optimizations/Keys/Auth | agent_id + request | valid API key + usage counter increment |
| Deployment Engine | n/a (infra layer) | health/status endpoint consumed by Agent Manager |
| End-End Validation | full scenario definition | pass/fail report per scenario, with which agent/step failed |

---

*Reference this alongside the pipeline flowchart image. If any agent's actual output ever needs a field not listed here, update this doc and the Sprint plan 186 tab's checklist column together so they don't drift apart.*
