<!-- NOTE: This file ONLY mentions the specific required inputs and outputs for this service. -->

# Entity Constraint Engine Schema

## Expected Input
The Entity Constraint Engine is a synchronous internal API usually called by the Constraint Agent, rather than through the asynchronous Agent Manager. It expects a standard JSON payload rather than the nested `Properties` envelope used by agents.

```json
{
  "entities": [ "string" ],         // Array of base entity types to fetch rules for (e.g., ["bedroom", "bathroom"])
  "include_relations": "boolean"    // Whether to fetch topological relation rules (defaults to true)
}
```

## Output Provided
Returns a mapping of the requested entities to their respective constraints.

```json
{
  "entities": {
    "bedroom": {
      "size_rules": {
        "min_area_ft2": "number",
        "min_side_ft": "number",
        "max_aspect_ratio": "number"
      },
      "feature_rules": {
        "requires_exterior_window": "boolean",
        "requires_egress": "boolean",
        "ventilation_type": "string"
      },
      "area_rules": [
        {
          "rule": "string",
          "description": "string"
        }
      ],
      "relational_rules": [
        {
          "a": "string",
          "b": "string",
          "relation": "string",
          "description": "string"
        }
      ]
    }
  }
}
```
