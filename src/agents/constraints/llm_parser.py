import os
import json
import warnings
import logging

logger = logging.getLogger(__name__)

# Suppress the google.generativeai deprecation warning
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import google.generativeai as genai
    from google.generativeai import configure as genai_configure  # type: ignore[attr-defined]
    from google.generativeai import GenerativeModel  # type: ignore[attr-defined]
    from google.generativeai import GenerationConfig  # type: ignore[attr-defined]

def parse_user_constraints(text: str) -> dict:
    """
    Parses unstructured natural language text from the user and outputs
    a structured JSON dictionary with required_rooms and room_overrides.

    Args:
        text (str): The unstructured natural language text provided by the user.

    Returns:
        dict: A structured dictionary containing parsed constraints like required_instances, room_overrides, etc.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Please set it to use the LLM parser.")
        
    genai_configure(api_key=api_key)
    
    # We use the requested model
    model = GenerativeModel('gemini-3.1-flash-lite')
    
    system_prompt = """
    You are an AI constraint parser for a home generation engine.
    The user will provide simple text describing what rooms they want and any specific dimension constraints.
    
    CRITICAL INSTRUCTION: You must operate at the INSTANCE level, not the type level. A house might have multiple bedrooms. 
    You must output specific unique IDs for every room using strictly the format `<base_type>_<number>` (e.g., "bedroom_1", "bedroom_2", "bathroom_1").
    Do NOT use custom names like "master_bedroom" or "guest_bedroom". Map them to "bedroom_1", "bedroom_2", etc.
    
    Your job is to output a strictly formatted JSON object with nine keys:
    1. "required_instances": A list of specific unique room IDs requested by the user (e.g. `["bedroom_1", "bedroom_2", "kitchen_1", "bathroom_1"]`).
    2. "excluded_base_types": A list of base room types (e.g. "living", "bathroom") that the user explicitly states they do NOT want.
    3. "room_overrides": A dictionary mapping the specific room instance IDs (e.g. "bedroom_1") to another dictionary of rule overrides just for that room.
    4. "global_exterior_overrides": A dictionary of novel or flat constraints that apply to the whole property exterior, architecture, lot, or outer shape (e.g. max_height_ft, max_lot_coverage, building_shape). Do NOT include non-layout things like budget or style.
    5. "global_interior_overrides": A dictionary of novel or flat constraints that apply globally to the inside of the house (e.g. global_ceiling_height, corridor_max_fraction_of_usable).
    6. "user_constraint_levels": A dictionary mapping EVERY overridden property key (from room_overrides and both global override dicts) to either "hard" or "soft".
    7. "user_descriptions": A dictionary mapping any NOVEL keys you invent to a human-readable description string explaining the rule.
    8. "adjacency_overrides": A list of relationship overrides. E.g., `[{"a": "bedroom_1", "b": "kitchen_1", "relation": "must_touch", "description": "User requested master bedroom and kitchen to be adjacent"}]`. You must use valid relation types like `must_touch`, `must_not_touch`, `ensuite_required`, etc. Note that 'a' and 'b' must be specific instance IDs, not base types.
    9. "requested_styles": A list of architectural or cultural styles requested by the user, such as "vastu" or "xhengoi". If none are requested, return an empty list.
    
    Rules for Overrides:
    - ALIGNMENT: You must map common spatial concepts to these EXACT keys: 'min_area_ft2', 'max_area_ft2', 'min_side_ft', 'max_side_ft', 'max_aspect_ratio', 'min_aspect_ratio', 'max_height_ft', 'front_setback_ft', 'rear_setback_ft', 'side_setback_ft'. Do NOT invent your own keys for these concepts.
    - TOLERANCES: If the user specifies a single target area (e.g., 100 sq ft), apply a +/- 10% buffer. Set 'min_area_ft2' = (value * 0.9) and 'max_area_ft2' = (value * 1.1).
    - TOLERANCES: If they specify a single length/breadth, apply a +/- 10% buffer. Set 'min_side_ft' = (value * 0.9) and 'max_side_ft' = (value * 1.1).
    - DIMENSIONS TO AREA: If the user provides explicit dimensions (e.g. 15x10 ft), you MUST calculate the area (150 sq ft) and apply the +/- 10% buffer to output `min_area_ft2` and `max_area_ft2` alongside the side limits.
    - RANGES: If they provide an explicit range (e.g. 100 to 120 sq ft), use exactly those bounds.
    - NOVEL RULES: If the user requests a constraint that does not fit the standard layout keys (e.g. "no stairs", "south facing"), invent a clear, concise snake_case key for it (e.g. "has_stairs": false). You MUST then add a plain-text description for this novel key into "user_descriptions".
    - LEVELS (CRITICAL): EVERY single key you output in room_overrides or global_overrides MUST have a corresponding entry in "user_constraint_levels". The value MUST be "hard" by default.
    - COUNTING & NEGATIVE PHRASING (CRITICAL): Count the exact number of physical rooms explicitly requested. Do NOT hallucinate extra rooms. If the user mentions a room negatively (e.g., "a bedroom without an attached bathroom"), do NOT count that as requesting an additional bathroom. Furthermore, "without an attached bathroom" just means no `ensuite_required` relation should exist; it does NOT mean you must add a `must_not_touch` constraint. Only use `must_not_touch` if the user strictly forbids the rooms from sharing a wall.
    
    Example user input:
    "I want a 300 sq ft master bedroom with an attached bathroom, a 100 sq ft guest bedroom without an attached bathroom, 1 common bathroom, 1 kitchen, and absolutely no living room. Also the max building height is 100 ft, but that's a soft constraint."
    
    Example JSON output:
    {
      "required_instances": [
        "bedroom_1",
        "bedroom_2",
        "bathroom_1",
        "bathroom_2",
        "kitchen_1"
      ],
      "excluded_base_types": [
        "living"
      ],
      "room_overrides": {
        "bedroom_1": {
          "min_area_ft2": 270.0,
          "max_area_ft2": 330.0
        },
        "bedroom_2": {
          "min_area_ft2": 90.0,
          "max_area_ft2": 110.0
        }
      },
      "global_exterior_overrides": {
        "max_height_ft": 100
      },
      "global_interior_overrides": {},
      "user_constraint_levels": {
        "min_area_ft2": "hard",
        "max_area_ft2": "hard",
        "max_height_ft": "soft"
      },
      "user_descriptions": {},
      "adjacency_overrides": [
        {
          "a": "bedroom_1",
          "b": "bathroom_1",
          "relation": "ensuite_required",
          "description": "User requested master bedroom to have an attached bathroom."
        }
      ],
      "requested_styles": []
    }
    
    Only output the pure JSON string, no markdown wrappers.
    """
    
    try:
        response = model.generate_content(
            f"{system_prompt}\n\nUser Input: {text}",
            generation_config=GenerationConfig(
                response_mime_type="application/json"
            ),
            request_options={"timeout": 60.0}
        )
        text_resp = response.text.strip()
        if text_resp.startswith("```json"):
            text_resp = text_resp[7:]
        if text_resp.startswith("```"):
            text_resp = text_resp[3:]
        if text_resp.endswith("```"):
            text_resp = text_resp[:-3]
        text_resp = text_resp.strip()
        
        start = text_resp.find('{')
        end = text_resp.rfind('}')
        if start != -1 and end != -1:
            text_resp = text_resp[start:end+1]
            
        return json.loads(text_resp)
    except Exception as e:
        logger.error(f"LLM Parsing Error: {e}", exc_info=True)
        return {}
