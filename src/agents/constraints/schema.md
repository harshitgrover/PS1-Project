<!-- NOTE: This file ONLY mentions the specific required inputs and outputs for this agent's `Properties` payload. For the generic envelope structure (session_id, file_refs, status), see input_output.txt. -->

# Constraint Agent Schema

## Expected Input
The Constraint Agent fetches dynamic zoning details from the Location Zoning Agent and merges them with user preferences from the Planner Agent.

```json
"Properties": {
  // Provided by Location Zoning Agent
  "location_zoning_output": {
    "jurisdiction": "string (e.g. 'Seattle_WA')",
    "zone_code": "string (e.g. 'LR3')",
    "offsets": {
      "front": "number (feet)",
      "rear": "number (feet)",
      "side": "number (feet)"
    },
    "max_coverage": "number (percentage or decimal fraction)",
    "tree_preservation": "GeoJSON (optional, boundaries of protected trees)"
  },
  
  // Provided by Planner Agent / User Input
  "planner_output": {
    "user_constraints": "string (Natural language describing room preferences, e.g. 'I want a large master bedroom and 2 bathrooms, kitchen must be near living room')",
    "requested_styles": [ "string" ] // e.g. ["vastu", "feng_shui"]
  }
}
```

## Output Provided
The Agent generates a single, exhaustive unified ruleset that the DXF Generator and Z3 Verifier rely on.

```json
"Properties": {
  "schema": {
    "jurisdiction": "string",
    "version": "string (e.g. 'v1')",
    "source": "string (e.g. 'IRC R304/R305')",
    "status": "string (e.g. 'loaded')",
    "tolerance_ft": "number (e.g. 1e-6)",
    
    // Global constraints for the building shell and lot
    "exterior": {
      "front_setback_ft": "number (Minimum front property line setback)",
      "rear_setback_ft": "number (Minimum rear property line setback)",
      "side_setback_ft": "number (Minimum side property line setback)",
      "max_height_ft": "number (Maximum allowed building height)",
      "max_impervious_surface_pct": "number (Maximum impervious surface)",
      "max_lot_coverage_fraction": "number (Max fraction of lot covered by building)",
      "min_house_width_ft": "number",
      "min_house_depth_ft": "number",
      "parcel_area_sqft": "number",
      "building_area_sqft": "number",
      "door_corner_margin_ft": "number",
      "min_area_fraction_of_max": "number (Min built percentage of max allowed footprint)",
      "tree_protection_zone": "array/object (GeoJSON for protected trees)"
    },
    
    // Detailed rules for rooms and layout topology
    "interior": {
      // Counts of each required base entity
      "required_rooms": {
        "bedroom": 3,
        "bathroom": 2,
        "kitchen": 1,
        "living": 1,
        "corridor": 1
      },
      
      // Individual specifications for EVERY instantiated room.
      // Every room (e.g. bedroom_1, bedroom_2) will have a complete spec object.
      "room_specs": {
        "bedroom_1": {
          "entity_type": "string (e.g. 'bedroom')",
          "min_area_ft2": "number",
          "min_side_ft": "number",
          "max_side_ft": "number",
          "min_aspect_ratio": "number",
          "max_aspect_ratio": "number",
          "habitable": "boolean",
          "requires_exterior_window": "boolean",
          "requires_egress": "boolean",
          "ventilation_type": "string (e.g. 'natural' or 'mechanical')",
          "requires_door": "boolean",
          "requires_closet": "boolean"
        },
        "bathroom_1": {
          "entity_type": "bathroom",
          "min_area_ft2": 35.0,
          "requires_exterior_window": false
          // ... all other rules
        }
      },
      
      // Topological layout rules (how rooms connect/relate)
      // Supported relations: "must_touch", "near", "away", "connected_by_door", "visible_from"
      "adjacency_rules": [
        {
          "a": "bedroom_1",
          "b": "corridor_1",
          "relation": "must_touch",
          "min_shared_wall_ft": 2.5,
          "level": "hard",
          "description": "Bedrooms must touch a corridor."
        },
        {
          "a": "kitchen_1",
          "b": "living_1",
          "relation": "near",
          "max_dist_ft": 5.0,
          "level": "soft"
        }
      ],
      
      // Area distribution rules (global sizing logic)
      // Examples: "living_gt_each_bedroom", "bathroom_lt_served_bedroom", "master_larger_than_others"
      "area_rules": [
        {
          "rule": "living_gt_each_bedroom",
          "level": "hard",
          "description": "Living room must be larger than any individual bedroom."
        }
      ],
      "corridor_max_fraction_of_usable": 0.15,
      "coverage_tol_fraction": "number (Coverage tolerance fraction, e.g. 0.05 means rooms must tile the footprint within ±5%)",
      
      // Note: If "requested_styles" like "vastu" were provided, dynamic stylistic rules will be appended here.
      // Example dynamically injected Vastu rules:
      "kitchen_placement_quadrant": "southeast",
      "master_bedroom_placement_quadrant": "southwest"
    },
    
    // Human-readable descriptions for EVERY applied rule, to give verifier (and users) context
    "descriptions": {
      "front_setback_ft": "Minimum front property line setback in feet.",
      "min_area_ft2": "Minimum allowed floor area for the room in square feet.",
      "requires_egress": "Whether the room requires emergency escape and rescue openings (egress).",
      // Includes auto-generated descriptions for dynamic rules
      "bedroom_1_must_touch_corridor_1": "Bedrooms must touch a corridor."
    },
    
    // Explicit severities for downstream error reporting (Verifier checks this to know if it's a code violation vs bad design)
    // Supports: 'hard' (must satisfy), 'soft' (preference), 'legal' (building code violation)
    "constraint_levels": {
      "front_setback_ft": "legal",
      "min_area_ft2": "legal",
      "requires_egress": "legal",
      "bedroom_1_must_touch_corridor_1": "hard",
      "kitchen_1_near_living_1": "soft"
    }
  }
}
```
