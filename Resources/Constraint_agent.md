Constraint Agent — Harshit (primary), Dhwani
What it does: This is the "rules manager" layer — the system-level rules engine, distinct from the Planner Agent. Planner Agent asks "how big do you want your house" (user preferences); Constraint Agent answers "what's the minimum bedroom size, does it need a bathroom, does it connect to a hallway" — the actual building-code-level rules for every entity in the design (rooms, walls, setbacks, tree zones), not just the outer envelope.
Job in one line: owns and serves the master ruleset that Generator and Verifier agents both pull from, so they never disagree.
Input: jurisdiction data from Location Zoning Agent:
json{ "jurisdiction": "Redmond, WA", "setbacks_ft": {...}, "max_lot_coverage_pct": 35, "tree_protection_zones": [...] }
Output:
json{
  "entity_rules": {
    "bedroom": { "min_area_sqft": 70, "must_connect_to": ["hallway"] },
    "bathroom": { "min_area_sqft": 35, "not_adjacent_to": ["bathroom", "kitchen"] },
    "kitchen": { "min_area_sqft": 80 },
    "living_room": { "min_area_relative": "> any bedroom" }
  },
  "jurisdiction_overrides": { "...only fields that differ for this location" }
}
Must also: support per-jurisdiction overrides, stay extensible (new rule types addable without touching agent code), and lock down an actual minimum bedroom size number with sir before sign-off (currently a placeholder).

no, you don't need to handle raw user input directly in either Constraint Agent or Entity Constraint Engine.
User input flows through the Planner/Customer Support Agent first, which turns the messy user prompt into a structured brief (square footage, BHK count, budget, location). That brief goes to the Agent Manager, which then triggers Location Zoning Agent to resolve the jurisdiction from the location data. That's what feeds into you — not the user's words at all.
So your actual input is:
json{ "jurisdiction": "Redmond, WA", "setbacks_ft": {...}, "max_lot_coverage_pct": 35, "tree_protection_zones": [...] }
This comes from Location Zoning Agent, already structured, already resolved — no free text, no parsing user intent. The only "user" concept that reaches you indirectly is which jurisdiction applies, and even that's been translated into clean fields before it gets to you.
The one place user input could indirectly touch your work: if a user later wants a custom rule (like "I want bigger bedrooms than the minimum"), that would come back through Planner → Agent Manager as a structured override request, not raw text — but that's not built yet and isn't in scope for your current rows. If it comes up, flag it and we'll figure out where that override gets injected.


Owns the deeper, system level rules engine the mentor distinguished from the Planning Agent: not “how big do you want your house” but “what is the minimum bedroom size, does it need a bathroom, does it connect to a hallway”, every entity in the design has its own constraint set here.
 

Must maintain a constraint definition for every entity type in the system (room, wall, setback, tree zone, etc.), not just the building envelope, this was the mentor's explicit distinction from the Planning Agent. Must be queryable by both the Generator and Verifier agents so both sides of the loop reference the exact same constraint source (avoiding the drift several Prob2 groups hit when adjacency rules weren't centrally defined). Must support per jurisdiction overrides fed in by the Location Zoning Agent. Must be extensible, new constraint types (fire safety, mechanical room sizing) must be addable without touching agent code, since the constraint list was explicitly called a living, growing list in the meeting.
 
 
☐ Maintains a constraint definition for every entity type: room, wall, setback, tree zone — not just the building envelope
 ☐ Queryable by both Generator and Verifier agents from the same single source — no drift between what each side checks
 ☐ Supports per-jurisdiction overrides fed in by Location Zoning Agent
 ☐ New constraint types (e.g. fire safety, mechanical room sizing) addable without touching agent code
 ☐ Minimum bedroom size enforced (specific number agreed with mentor before sprint sign-off)
 ☐ Every room type has at least one defined adjacency/connectivity rule (e.g. must connect to a hallway)
 

 we need to cover Bellevue, Redmond, and Kirkland, along with Seattle and Bothell (those two are slightly lower priority).
