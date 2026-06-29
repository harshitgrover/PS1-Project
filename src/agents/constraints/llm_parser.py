import os
import json
import warnings

# Suppress the google.generativeai deprecation warning
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import google.generativeai as genai

def parse_user_constraints(text: str) -> dict:
    """
    Parses unstructured natural language text from the user and outputs
    a structured JSON dictionary with required_rooms and room_overrides.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Please set it to use the LLM parser.")
        
    genai.configure(api_key=api_key)
    
    # We use the requested model
    model = genai.GenerativeModel('gemini-3.1-flash-lite')
    
    system_prompt = """
    You are an AI constraint parser for a home generation engine.
    The user will provide simple text describing what rooms they want and any specific dimension constraints.
    
    Your job is to output a strictly formatted JSON object with seven keys:
    1. "required_rooms": A dictionary mapping the entity type (e.g. "bedroom", "kitchen", "living", "bathroom", "balcony", "corridor", "dining", "garage", "laundry", "entry") to the integer count requested. If the user explicitly says they do NOT want a room (e.g. "no need of living room"), you MUST set its count to 0 in this dictionary.
    2. "room_overrides": A dictionary mapping the entity type to another dictionary of rule overrides.
    3. "global_exterior_overrides": A dictionary of novel or flat constraints that apply to the whole property exterior, architecture, lot, or outer shape (e.g. max_height_ft, max_lot_coverage, building_shape). Do NOT include non-layout things like budget or style.
    4. "global_interior_overrides": A dictionary of novel or flat constraints that apply globally to the inside of the house (e.g. global_ceiling_height, corridor_max_fraction_of_usable).
    5. "user_constraint_levels": A dictionary mapping EVERY overridden property key (from room_overrides and both global override dicts) to either "hard" or "soft".
    6. "user_descriptions": A dictionary mapping any NOVEL keys you invent to a human-readable description string explaining the rule.
    7. "adjacency_overrides": A list of relationship overrides. E.g., `[{"a": "bedroom", "b": "kitchen", "relation": "must_touch", "description": "User requested bedroom and kitchen to be adjacent"}]`. You must use valid relation types like `must_touch`, `must_not_touch`, `ensuite_required`, etc.
    
    Rules for Overrides:
    - ALIGNMENT: You must map common spatial concepts to these EXACT keys: 'min_area_ft2', 'max_area_ft2', 'min_side_ft', 'max_side_ft', 'max_aspect_ratio', 'min_aspect_ratio', 'max_height_ft', 'front_setback_ft', 'rear_setback_ft', 'side_setback_ft'. Do NOT invent your own keys for these concepts (e.g. do not use "bedroom_size", use "min_area_ft2").
    - TOLERANCES: If the user specifies a single target area (e.g., 100 sq ft), apply a ±10% buffer. Set 'min_area_ft2' = (value * 0.9) and 'max_area_ft2' = (value * 1.1).
    - TOLERANCES: If they specify a single length/breadth, apply a ±10% buffer. Set 'min_side_ft' = (value * 0.9) and 'max_side_ft' = (value * 1.1).
    - DIMENSIONS TO AREA: If the user provides explicit dimensions (e.g. 15x10 ft), you MUST calculate the area (150 sq ft) and apply the ±10% buffer to output `min_area_ft2` and `max_area_ft2` alongside the side limits.
    - RANGES: If they provide an explicit range (e.g. 100 to 120 sq ft), use exactly those bounds.
    - NOVEL RULES: If the user requests a constraint that does not fit the standard layout keys (e.g. "no stairs", "south facing"), invent a clear, concise snake_case key for it (e.g. "has_stairs": false). You MUST then add a plain-text description for this novel key into "user_descriptions".
    - LEVELS (CRITICAL): EVERY single key you output in room_overrides or global_overrides MUST have a corresponding entry in "user_constraint_levels". The value MUST be "hard" by default. If the user explicitly asks to make a constraint "soft", or vice-versa wants a normally flexible thing to be "hard", respect their choice exactly in this dictionary!
    
    Example user input:
    "I want 2 bedrooms of 100sq ft, 1 kitchen, and 1 living room that is at least 15 ft long. Also the max building height is 100 ft, but that's a soft constraint."
    
    Example JSON output:
    {
      "required_rooms": {
        "bedroom": 2,
        "kitchen": 1,
        "living": 1
      },
      "room_overrides": {
        "bedroom": {
          "min_area_ft2": 95.0,
          "max_area_ft2": 105.0
        },
        "living": {
          "min_side_ft": 14.5,
          "max_side_ft": 15.5
        }
      },
      "global_overrides": {
        "max_height_ft": 100
      },
      "user_constraint_levels": {
        "min_area_ft2": "hard",
        "max_area_ft2": "hard",
        "min_side_ft": "hard",
        "max_side_ft": "hard",
        "max_height_ft": "soft"
      }
    }
    
    Only output the pure JSON string, no markdown wrappers.
    """
    
    try:
        response = model.generate_content(
            f"{system_prompt}\n\nUser Input: {text}",
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"LLM Parsing Error: {e}")
        return {}
