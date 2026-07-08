import os
import httpx
from typing import Any
from dotenv import load_dotenv
from supabase import create_client, Client
import json
import logging

logger = logging.getLogger(__name__)

from .validator import ConstraintValidator

load_dotenv()


class ConstraintAgent:
    """
    Manages and serves the master ruleset for the multi-agent building design system.
    Fetches per-entity constraints from the Entity Constraint Engine, applies
    per-jurisdiction overrides from the Zoning Agent, and returns a single unified
    constraint schema consumed by both the Generator and Verifier agents.
    """
    DEFAULT_DESCRIPTIONS = {
        "front_setback_ft": "Minimum front property line setback in feet.",
        "rear_setback_ft": "Minimum rear property line setback in feet.",
        "side_setback_ft": "Minimum side property line setback in feet.",
        "max_height_ft": "Maximum allowed building height in feet.",
        "max_impervious_surface_pct": "Maximum allowed percentage of impervious surfaces on the lot.",
        "max_lot_coverage_fraction": "Maximum allowed fraction of the lot that can be covered by the building footprint.",
        "min_house_width_ft": "Minimum allowed width of the main building structure.",
        "min_house_depth_ft": "Minimum allowed depth of the main building structure.",
        "parcel_area_sqft": "Total area of the property parcel in square feet.",
        "building_area_sqft": "Total calculated building area in square feet.",
        "door_corner_margin_ft": "Minimum distance a door must be placed from an internal corner.",
        "min_area_fraction_of_max": "Minimum percentage of the maximum allowed footprint that must be built.",
        "tree_protection_zone": "GeoJSON boundaries for protected trees that cannot be built over.",
        "building_file": "File path to the existing building geometry (if any).",
        "geometry_file": "File path to the raw lot geometry."
    }

    LEGAL_KEYS = {
        "requires_egress",
        "requires_exterior_window",
        "ventilation_type",
        "requires_garage_mechanical_ventilation_interlock",
        "requires_chapter_93_fire_safety_standards",
        "front_setback_ft",
        "rear_setback_ft",
        "side_setback_ft",
        "tree_protection_zone"
    }

    SOFT_KEYS: set[str] = set()  # Architectural preferences that are soft; populated dynamically from style_rules
    
    # We will dynamically add keys fetched from style_rules to SOFT_KEYS

    def __init__(self, entity_engine_url=None):
        """
        Initializes the ConstraintAgent with a Supabase client and the Entity Constraint Engine URL.

        Args:
            entity_engine_url (str | None): URL for the Entity Constraint Engine API.
                Defaults to the ENTITY_ENGINE_URL environment variable, falling back to localhost:8001.
        """
        self.entity_engine_url = entity_engine_url or os.environ.get("ENTITY_ENGINE_URL", "http://localhost:8001")
        logger.debug(f"ConstraintAgent initialized with entity_engine_url={self.entity_engine_url}")

        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            logger.warning("SUPABASE_URL or SUPABASE_KEY not set. Database queries will fail.")
        else:
            self.supabase: Client = create_client(supabase_url, supabase_key)
            logger.debug("Supabase client initialized successfully.")
        
    def process_zoning_input(self, data: dict, user_text: str | None = None) -> dict:
        """
        Takes raw JSON from the location/zoning agent, plus optional user override text,
        and translates it into our standard constraint schema.
        Also validates impossible constraints before proceeding.

        Args:
            data (dict): The raw JSON payload from the location/zoning agent containing zoning data.
            user_text (str | None): Optional natural language text describing user preferences. Defaults to None.

        Returns:
            dict: The final unified constraint schema dictionary.
        """
        # 0. Parse user constraints via LLM if provided
        parsed_user_constraints = {}
        if not user_text:
            user_constraints_file = os.path.join(os.path.dirname(__file__), "user_constraints.txt")
            if os.path.exists(user_constraints_file):
                with open(user_constraints_file, "r") as f:
                    user_text = f.read().strip()

        if user_text:
            try:
                from src.agents.constraints.llm_parser import parse_user_constraints
                parsed_user_constraints = parse_user_constraints(user_text)
            except Exception as e:
                logger.error(f"Failed to parse user_constraints with LLM: {e}", exc_info=True)

        # 1. Validate constraints before doing heavy lifting
        # Pass the parsed dictionary to the validator
        validator = ConstraintValidator(
            zoning_data=data,
            user_constraints=parsed_user_constraints,
            supabase_client=getattr(self, 'supabase', None)
        )
        validator.validate()
        
        # 1. Base Exterior defaults (Jurisdictions table removed)
        jurisdiction = data.get('jurisdiction')
        zone = data.get('zone_code') or data.get('zone')
        if not jurisdiction:
            # Fallback if zoning agent misses the jurisdiction entirely
            jurisdiction = "Unknown Jurisdiction"
            
        # Extract dynamic overrides provided by the Zoning Agent
        overrides = {'exterior': {}}
        
        # Extract offsets/setbacks
        offsets = data.get('offsets') or data.get('setbacks_ft')
        if offsets:
            if 'front' in offsets: overrides['exterior']['front_setback_ft'] = offsets['front']
            if 'rear' in offsets: overrides['exterior']['rear_setback_ft'] = offsets['rear']
            if 'side' in offsets: overrides['exterior']['side_setback_ft'] = offsets['side']
            
        # Extract max coverage
        max_cov = data.get('max_coverage') or data.get('max_lot_coverage_pct')
        if max_cov is not None:
            # Handle percentage vs fraction
            if max_cov > 1.0:
                overrides['exterior']['max_lot_coverage_fraction'] = max_cov / 100.0
            else:
                overrides['exterior']['max_lot_coverage_fraction'] = max_cov
                
        # Extract tree preservation
        trees = data.get('tree_preservation') or data.get('tree_protection_zones')
        if trees:
            overrides['exterior']['tree_protection_zone'] = trees
            
        # Dynamically extract all other constraints provided by the real zoning agent
        ignore_keys = {
            'address', 'city', 'zone', 'latitude', 'longitude', 'parcel_centroid',
            'parcel_area', 'lot_vertex_count', 'status', 'jurisdiction', 'zone_code',
            'zone_type', 'zone_description', 'overlay_districts', 'source_url',
            'parcel_id', 'building_count', 'offsets', 'setbacks_ft', 'max_coverage',
            'max_lot_coverage_pct', 'tree_preservation', 'tree_protection_zones'
        }
        for key, value in data.items():
            if key not in ignore_keys and value is not None:
                overrides['exterior'][key] = value
            
        return self.generate_constraints(jurisdiction, overrides=overrides, zone=zone, parsed_user_constraints=parsed_user_constraints)
        
    def generate_constraints(self, jurisdiction_name: str, overrides: dict | None = None, zone: str | None = None, parsed_user_constraints: dict | None = None) -> dict:
        """
        Generates the full constraint JSON for a given jurisdiction.
        Optionally applies overrides (e.g., from user preferences via Planner Agent).
        Returns the final JSON schema.

        Args:
            jurisdiction_name (str): The name of the jurisdiction (e.g., "Seattle_WA").
            overrides (dict | None): Optional dictionary of overrides to apply to exterior/interior constraints. Defaults to None.
            zone (str | None): Optional zoning code (e.g., "LR3"). Defaults to None.
            parsed_user_constraints (dict | None): Optional structured dictionary of parsed user constraints. Defaults to None.

        Returns:
            dict: The final JSON schema representing all constraints for the design.
        """
        def assign_level(k):
            # Dynamic checking
            if k in self.LEGAL_KEYS or k.startswith("min_") or k.startswith("max_"):
                return "legal"
            if k in self.SOFT_KEYS:
                return "soft"
            # Default to hard for architectural/adjacency rules
            return "hard"
        
        # 1. Base Exterior defaults (Jurisdictions table removed)
        source = "IRC R304/R305"
        status = "loaded"
        tolerance_ft = 1e-6
        
        exterior: dict[str, Any] = {
            "front_setback_ft": None,
            "rear_setback_ft": None,
            "side_setback_ft": None,
            "min_house_width_ft": None,
            "min_house_depth_ft": None,
            "door_corner_margin_ft": 2.0,
            "max_lot_coverage_fraction": None,
            "min_area_fraction_of_max": 0.85,
            "tree_protection_zone": {"type": "polygon", "coordinates": []}
        }
        
        # 2. Fetch Interior rules ONLY for required entities
        # Baseline minimums required for a valid layout (instance IDs)
        required_instances = ["bathroom_1", "bathroom_2", "bedroom_1", "bedroom_2", "living_1", "kitchen_1", "corridor_1"]
        
        # 2.1 Parse user constraints via LLM if provided
        room_overrides = {}
        user_global_exterior = {}
        user_global_interior = {}
        user_constraint_levels = {}
        user_descriptions = {}
        user_adjacency_overrides = []
        user_requested_styles = []
        
        if parsed_user_constraints:
            try:
                parsed = parsed_user_constraints
                if "required_instances" in parsed and isinstance(parsed["required_instances"], list):
                    # Replace defaults entirely if the user explicitly provided instances
                    required_instances = parsed["required_instances"]
                if "excluded_base_types" in parsed and isinstance(parsed["excluded_base_types"], list):
                    excluded = set(parsed["excluded_base_types"])
                    # Remove any default instances whose base type is excluded
                    required_instances = [inst for inst in required_instances if inst.rsplit('_', 1)[0] not in excluded and inst.replace('_1','').replace('_2','') not in excluded]
                if "room_overrides" in parsed and isinstance(parsed["room_overrides"], dict):
                    room_overrides = parsed["room_overrides"]
                if "global_exterior_overrides" in parsed and isinstance(parsed["global_exterior_overrides"], dict):
                    user_global_exterior = parsed["global_exterior_overrides"]
                if "global_interior_overrides" in parsed and isinstance(parsed["global_interior_overrides"], dict):
                    user_global_interior = parsed["global_interior_overrides"]
                if "user_constraint_levels" in parsed and isinstance(parsed["user_constraint_levels"], dict):
                    user_constraint_levels = parsed["user_constraint_levels"]
                if "user_descriptions" in parsed and isinstance(parsed["user_descriptions"], dict):
                    user_descriptions = parsed["user_descriptions"]
                if "adjacency_overrides" in parsed and isinstance(parsed["adjacency_overrides"], list):
                    user_adjacency_overrides = parsed["adjacency_overrides"]
                if "requested_styles" in parsed and isinstance(parsed["requested_styles"], list):
                    user_requested_styles = parsed["requested_styles"]
            except Exception as e:
                logger.error(f"Failed to process user_constraints: {e}", exc_info=True)
        
        room_specs: dict[str, Any] = {}
        descriptions = {}
        adjacency_rules = []
        area_rules_list = []
        seen_adj = set()
        
        # Helper to extract base type from instance (e.g. "bedroom_1" -> "bedroom", "master_bedroom" -> "bedroom")
        def get_base_type(instance_id):
            if "bedroom" in instance_id: return "bedroom"
            if "bathroom" in instance_id: return "bathroom"
            if "kitchen" in instance_id: return "kitchen"
            if "living" in instance_id: return "living"
            if "corridor" in instance_id: return "corridor"
            if "dining" in instance_id: return "dining"
            if "garage" in instance_id: return "garage"
            if "laundry" in instance_id: return "laundry"
            if "entry" in instance_id: return "entry"
            if "balcony" in instance_id: return "balcony"
            # Fallback
            return instance_id.rsplit('_', 1)[0]
            
        base_types_needed = list(set([get_base_type(inst) for inst in required_instances]))
        
        overridden_pairs = set()
        for u_adj in user_adjacency_overrides:
            if "a" in u_adj and "b" in u_adj:
                overridden_pairs.add(tuple(sorted([u_adj["a"], u_adj["b"]])))
        
        # 1. Fetch specifications for all required base entities in a single batch request
        if base_types_needed:
            logger.debug(f"Fetching rules for base entity types: {base_types_needed}")
            try:
                # Sync HTTP request to the internal engine
                response = httpx.post(
                    f"{self.entity_engine_url}/api/v1/entity_constraints",
                    json={"entities": base_types_needed, "include_relations": True},
                    timeout=10.0
                )
                if response.status_code == 200:
                    batch_data = response.json().get("entities", {})
                    # 1a. Build room specs for each instance
                    for inst in required_instances:
                        base = get_base_type(inst)
                        ent_data = batch_data.get(base, {})
                        if not ent_data:
                            continue
                            
                        # Merge into our aggregate structures
                        specs = {**ent_data.get("size_rules", {}), **ent_data.get("feature_rules", {})}
                        specs["entity_type"] = base
                        
                        # Apply specific user overrides for this room instance from the LLM
                        if inst in room_overrides:
                            user_or = room_overrides[inst]
                            specs.update(user_or)
                            
                            # Auto-adjust max_aspect_ratio and max_area_ft2 if sides push it beyond defaults
                            min_s = user_or.get("min_side_ft")
                            max_s = user_or.get("max_side_ft")
                            if min_s is not None and max_s is not None and min_s > 0:
                                req_ar = max_s / min_s
                                if req_ar > specs.get("max_aspect_ratio", 0):
                                    specs["max_aspect_ratio"] = req_ar
                                
                                min_possible_area = min_s * min_s
                                if min_possible_area > specs.get("max_area_ft2", 0):
                                    specs["max_area_ft2"] = min_possible_area
                                    
                        room_specs[inst] = specs
                        
                    # 1b. Process relational and area rules from base types globally
                    for base, ent_data in batch_data.items():
                        # Store any adjacency rules
                        for rel in ent_data.get("relational_rules", []):
                            # The base rules use base types (e.g. "bedroom", "bathroom").
                            # Since we operate on instances, we could map them. For now, keep as is.
                            pass
                                
                        # Store any area rules
                        for a_rule in ent_data.get("area_rules", []):
                            rule_copy = dict(a_rule)
                            rule_copy["level"] = assign_level(rule_copy["rule"])
                            # Prevent duplicates since we might process the same base type twice? No, we are iterating batch_data.items()
                            if rule_copy not in area_rules_list:
                                area_rules_list.append(rule_copy)
                if base_types_needed:
                    logger.warning(f"Could not fetch constraints for entities: {base_types_needed}")
            except Exception as e:
                logger.error(f"Error calling Entity Constraint Engine API: {e}", exc_info=True)
                    
        # Now append all user adjacency overrides to adjacency_rules
        for u_adj in user_adjacency_overrides:
             if u_adj.get("a") in required_instances and u_adj.get("b") in required_instances:
                  desc_key = f"{u_adj['a']}_{u_adj['relation']}_{u_adj['b']}"
                  u_adj["level"] = user_constraint_levels.get(desc_key, "hard")
                  if "description" not in u_adj:
                       u_adj["description"] = user_descriptions.get(desc_key, f"User rule: {desc_key}")
                  adjacency_rules.append(u_adj)
                
        # Default interior constraints
        interior: dict[str, Any] = {
            "required_rooms": required_instances,
            "room_specs": room_specs,
            "adjacency_rules": adjacency_rules,
            "area_rules": area_rules_list,
            "corridor_max_fraction_of_usable": 0.15,
            "coverage_tol_fraction": 0.05
        }
        
        # Inject user global exterior overrides
        if user_global_exterior:
            for k, v in user_global_exterior.items():
                exterior[k] = v
                
        # Inject user global interior overrides
        if user_global_interior:
            for k, v in user_global_interior.items():
                interior[k] = v
        
        # 2.5 Apply Zone Specific Rules
        if zone:
            # Sanitize jurisdiction name for the table lookup (e.g. "Seattle, WA" -> "Seattle_WA")
            loc = jurisdiction_name.replace(", ", "_").replace(" ", "_")
            try:
                if hasattr(self, 'supabase'):
                    response = self.supabase.table("zone_rules").select("rule_key, rule_value, description").eq("location", loc).eq("zone", zone).execute()
                    for row in response.data:
                        if not isinstance(row, dict):
                            continue
                        key, val_str, desc = str(row.get("rule_key")), row.get("rule_value"), row.get("description")
                        try:
                            val = float(val_str) if isinstance(val_str, (int, float, str)) else val_str
                        except (ValueError, TypeError):
                            val = val_str
                            
                        if key in exterior:
                            exterior[key] = val
                        else:
                            interior[key] = val
                            
                        if desc:
                            descriptions[key] = desc
            except Exception as e:
                logger.error(f"Error querying Supabase zone_rules: {e}", exc_info=True)
                
        # Inject user descriptions
        if user_descriptions:
            descriptions.update(user_descriptions)
            
        # 2.6 Apply Style Specific Rules (Vastu, Xhengoi, etc.) ONLY IF REQUESTED
        for style in user_requested_styles:
            style_clean = style.lower().strip()
            try:
                if hasattr(self, 'supabase'):
                    response = self.supabase.table("style_rules").select("rule_key, rule_value, description").eq("style", style_clean).execute()
                    for row in response.data:
                        if not isinstance(row, dict):
                            continue
                        key, val_str, desc = str(row.get("rule_key")), row.get("rule_value"), row.get("description")
                        try:
                            val = float(val_str) if isinstance(val_str, (int, float, str)) else val_str
                        except (ValueError, TypeError):
                            val = val_str
                            
                        # Mark it as a soft rule dynamically
                        self.SOFT_KEYS.add(key)
                            
                        # Inject into interior global constraints by default
                        interior[key] = val
                        if desc:
                            descriptions[key] = desc
            except Exception as e:
                logger.error(f"Error querying Supabase style_rules: {e}", exc_info=True)
            
        # 3. Apply Overrides (if any)
        if overrides:
            if 'exterior' in overrides:
                exterior.update(overrides['exterior'])
            if 'interior' in overrides:
                interior.update(overrides['interior'])
                
        # 4. Assemble final JSON
        # Ensure default descriptions are added for exterior base rules
        for key in exterior.keys():
            if key not in descriptions:
                if key in self.DEFAULT_DESCRIPTIONS:
                    descriptions[key] = self.DEFAULT_DESCRIPTIONS[key]
                else:
                    readable = key.replace("_", " ").capitalize()
                    descriptions[key] = f"Dynamic zoning constraint: {readable}."

        # Ensure constraint_levels are assigned
        constraint_levels = {}
        # We assign levels based on all defined descriptions and keys in exterior/interior/room_specs
            
        for key in descriptions.keys():
            constraint_levels[key] = assign_level(key)
            
        for key in exterior.keys():
            constraint_levels[key] = assign_level(key)
            
        for room, specs in room_specs.items():
            for spec_key in specs.keys():
                constraint_levels[spec_key] = assign_level(spec_key)
                
        # Now overlay the explicitly requested levels from the user
        if user_constraint_levels:
            constraint_levels.update(user_constraint_levels)

        # SAFETY CHECK: If the LLM forgot to put an overridden key into user_constraint_levels, force it to 'hard'
        if room_overrides:
            for ent, room_ovr in room_overrides.items():
                if not isinstance(room_ovr, dict):
                    continue
                for k in room_ovr.keys():
                    if k not in constraint_levels:
                        constraint_levels[k] = "hard"
        if user_global_exterior:
            for k in user_global_exterior.keys():
                if k not in constraint_levels:
                    constraint_levels[k] = "hard"
        if user_global_interior:
            for k in user_global_interior.keys():
                if k not in constraint_levels:
                    constraint_levels[k] = "hard"

        final_schema = {
            "jurisdiction": jurisdiction_name,
            "version": "v1",
            "source": source,
            "status": status,
            "tolerance_ft": tolerance_ft,
            "exterior": exterior,
            "interior": interior,
            "descriptions": descriptions,
            "constraint_levels": constraint_levels
        }
        
        # Filter descriptions and constraint_levels to ONLY include keys present in the final_schema
        def get_all_keys(obj):
            keys = set()
            if isinstance(obj, dict):
                for k, v in obj.items():
                    keys.add(k)
                    keys.update(get_all_keys(v))
            elif isinstance(obj, list):
                for item in obj:
                    keys.update(get_all_keys(item))
            return keys
            
        active_keys = get_all_keys(final_schema)
        
        filtered_levels = {k: v for k, v in constraint_levels.items() if k in active_keys}
        filtered_descriptions = {k: v for k, v in descriptions.items() if k in active_keys}
        
        final_schema["constraint_levels"] = filtered_levels
        final_schema["descriptions"] = filtered_descriptions
        
        # 5. Return final JSON
        return final_schema

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        logger.info("Usage: python3 constraint_agent.py <zoning_json_file>")
        sys.exit(1)
        
    zoning_file = sys.argv[1]
    
    try:
        with open(zoning_file, 'r') as f:
            zoning_data = json.load(f)
            
        agent = ConstraintAgent()
        final_schema = agent.process_zoning_input(zoning_data)
        logger.info(json.dumps(final_schema, indent=2))
    except Exception as e:
        logger.error(f"Error running Constraint Agent: {e}", exc_info=True)
