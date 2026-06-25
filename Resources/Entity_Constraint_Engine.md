Entity Constraint Engine — Harshit (primary), Anshul
What it does: This is the execution layer underneath Constraint Agent — where the actual rules get encoded and enforced per entity. If Constraint Agent is "the rulebook," Entity Constraint Engine is "the code that reads the rulebook." It specifically handles relational rules between entities (adjacency, connectivity), not just single-entity size checks — that was the exact gap the mentor called out ("what are the adjacent things you can have in a bedroom").
Job in one line: encodes per-entity AND per-relationship rules, versioned, so both Floor Plan Generator and Verifier/Z3 can query the same source.
Input: a request from Constraint Agent to encode/retrieve rules for a given entity type:
json{ "entity_type": "bedroom", "rule_request": "size_and_adjacency" }
Output (back to Constraint Agent, which folds it into the combined ruleset above):
json{
  "entity_type": "bedroom",
  "size_rules": { "min_area_sqft": 70 },
  "relational_rules": { "must_connect_to": ["hallway"], "should_be_near": ["bathroom"] },
  "version": "v3"
}
Must also: let each entity type carry its own independent rule set (adding a new entity type shouldn't touch existing ones), and version every change so the rule set's history is tracked as it grows.
The simplest way to explain the split to Harshit if he's confused: Constraint Agent is the interface other agents talk to; Entity Constraint Engine is the storage + relational logic underneath it that actually answers "what connects to what."

no, you don't need to handle raw user input directly in either Constraint Agent or Entity Constraint Engine.
User input flows through the Planner/Customer Support Agent first, which turns the messy user prompt into a structured brief (square footage, BHK count, budget, location). That brief goes to the Agent Manager, which then triggers Location Zoning Agent to resolve the jurisdiction from the location data. That's what feeds into you — not the user's words at all.
So your actual input is:
json{ "jurisdiction": "Redmond, WA", "setbacks_ft": {...}, "max_lot_coverage_pct": 35, "tree_protection_zones": [...] }
This comes from Location Zoning Agent, already structured, already resolved — no free text, no parsing user intent. The only "user" concept that reaches you indirectly is which jurisdiction applies, and even that's been translated into clean fields before it gets to you.
The one place user input could indirectly touch your work: if a user later wants a custom rule (like "I want bigger bedrooms than the minimum"), that would come back through Planner → Agent Manager as a structured override request, not raw text — but that's not built yet and isn't in scope for your current rows. If it comes up, flag it and we'll figure out where that override gets injected.


The execution layer behind the Constraint Agent: this is literally where per entity rules (bedroom minimum size, adjacent room rules, hallway connection requirements) get encoded and checked for every entity in the design.

 	
Must encode constraints at the entity level (per room, per wall, per fixture) so a new entity type can have its own rule set without touching unrelated entities' rules. Must support relational constraints between entities (adjacency, connectivity to hallway, “must have a bathroom nearby”), not just single entity size/shape rules, since this was the specific gap the mentor called out (“what are the adjacent things you can have in a bedroom”). Must be the single source of truth consumed by both the Floor Plan Generator and the Verifier Agent's Z3 checks. Must be versionable so constraint changes can be tracked as the rule set grows over the project.

☐ Constraints encoded at entity level (per room, per wall, per fixture) independently
 ☐ New entity type can get its own rule set without touching unrelated entities' rules
 ☐ Supports relational constraints between entities (adjacency, connectivity to hallway, “must have nearby bathroom”)
 ☐ Acts as single source of truth consumed by both Floor Plan Generator and Verifier Agent's Z3 checks
 ☐ Constraint set is versioned — changes are tracked over time, not silently overwritten


We need to cover Bellevue, Redmond, and Kirkland, along with Seattle and Bothell (those two are slightly lower priority).
