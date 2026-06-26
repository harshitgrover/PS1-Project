import sqlite3
import json
import os
import hashlib
from entity_constraint_engine import EntityConstraintEngine

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

class ConstraintAgent:
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

    DEFAULT_CONSTRAINT_LEVELS = {
        # Soft constraints
        "requires_egress": "soft",
        "requires_exterior_window": "soft",
        "ventilation_type": "soft",
        "requires_garage_mechanical_ventilation_interlock": "soft",
        
        # Hard constraints (fallback default for everything else)
        # Note: We will default to "hard" for any key not explicitly listed as "soft"
    }

    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = db_path
        self.entity_engine = EntityConstraintEngine(db_path)

    def _get_connection(self):
        return sqlite3.connect(self.db_path)
        
    def process_zoning_input(self, zoning_hashkey: str) -> str:
        """
        Reads the Zoning Agent's JSON output from the database using its hashkey,
        extracts the jurisdiction, zone, and overrides, and generates the constraints.
        Returns the ID of the generated ruleset.
        """
        conn = self.entity_engine._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT data_json FROM AgentOutputs WHERE id=?", (zoning_hashkey,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise ValueError(f"Zoning output with hashkey '{zoning_hashkey}' not found in DB.")
            
        data = json.loads(row[0])
            
        jurisdiction = data.get('jurisdiction')
        zone = data.get('zone_code') or data.get('zone')
        if not jurisdiction:
            raise ValueError("Input JSON must contain 'jurisdiction'")
            
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
            
        # Extract new limits provided by the real zoning agent
        for key in ['max_height_ft', 'max_far', 'max_impervious_surface_pct', 'parcel_area_sqft', 'building_area_sqft', 'building_file', 'geometry_file']:
            if key in data and data[key] is not None:
                overrides['exterior'][key] = data[key]
            
        return self.generate_constraints(jurisdiction, overrides=overrides, zone=zone)
        
    def generate_constraints(self, jurisdiction_name: str, overrides: dict = None, zone: str = None) -> str:
        """
        Generates the full constraint JSON for a given jurisdiction.
        Optionally applies overrides (e.g., from user preferences via Planner Agent).
        Stores the final JSON in the database and returns its hash ID.
        """
        def assign_level(k):
            return self.DEFAULT_CONSTRAINT_LEVELS.get(k, "hard")
            
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 1. Base Exterior defaults (Jurisdictions table removed)
        source = "IRC R304/R305"
        status = "loaded"
        tolerance_ft = 1e-6
        
        exterior = {
            "front_setback_ft": None,
            "rear_setback_ft": None,
            "side_setback_ft": None,
            "min_house_width_ft": 20.0,
            "min_house_depth_ft": 20.0,
            "door_corner_margin_ft": 2.0,
            "max_lot_coverage_fraction": None,
            "min_area_fraction_of_max": 0.85,
            "tree_protection_zone": {"type": "polygon", "coordinates": []}
        }
        
        # 2. Fetch Interior rules ONLY for required entities
        # Baseline minimums required for a valid layout
        required_rooms = { "bathroom": 2, "bedroom": 2, "living": 1, "kitchen": 1 }
        
        # 2.1 Parse user constraints via LLM if provided
        room_overrides = {}
        user_global_overrides = {}
        user_constraint_levels = {}
        user_descriptions = {}
        
        user_constraints_file = os.path.join(os.path.dirname(__file__), "user_constraints.txt")
        if os.path.exists(user_constraints_file):
            with open(user_constraints_file, "r") as f:
                user_text = f.read().strip()
            
            if user_text:
                try:
                    from llm_parser import parse_user_constraints
                    parsed = parse_user_constraints(user_text)
                    if "required_rooms" in parsed and isinstance(parsed["required_rooms"], dict):
                        for room, count in parsed["required_rooms"].items():
                            required_rooms[room] = count
                    if "room_overrides" in parsed and isinstance(parsed["room_overrides"], dict):
                        room_overrides = parsed["room_overrides"]
                    if "global_overrides" in parsed and isinstance(parsed["global_overrides"], dict):
                        user_global_overrides = parsed["global_overrides"]
                    if "user_constraint_levels" in parsed and isinstance(parsed["user_constraint_levels"], dict):
                        user_constraint_levels = parsed["user_constraint_levels"]
                    if "user_descriptions" in parsed and isinstance(parsed["user_descriptions"], dict):
                        user_descriptions = parsed["user_descriptions"]
                except Exception as e:
                    print(f"Failed to process user_constraints.txt: {e}")
        
        # Remove any entities that were explicitly set to 0 by the user
        required_rooms = {k: v for k, v in required_rooms.items() if v > 0}
        
        room_specs = {}
        descriptions = {}
        adjacency_rules = []
        area_rules_list = []
        seen_adj = set()
        entities = list(required_rooms.keys())
        
        for ent in entities:
            # We now fetch relations specifically from Adjacency_{ent} per entity
            ent_rules = self.entity_engine.get_entity_rules(ent, include_relations=True)
            if ent_rules.get("status") != "no_data":
                specs = dict(ent_rules["size_rules"])
                if "feature_rules" in ent_rules:
                    specs.update(ent_rules["feature_rules"])
                    
                # Apply specific user overrides for this room from the LLM
                if ent in room_overrides:
                    specs.update(room_overrides[ent])
                    
                room_specs[ent] = specs
                
                # Add relational rules locally
                for adj in ent_rules["relational_rules"]:
                    # Only include rule if BOTH entities are actually required in this layout
                    if adj["a"] in entities and adj["b"] in entities:
                        key = tuple(sorted([adj["a"], adj["b"]]) + [adj["relation"]])
                        if key not in seen_adj:
                            seen_adj.add(key)
                            
                            adj_copy = dict(adj)
                            desc_key = f"{adj['a']}_{adj['relation']}_{adj['b']}"
                            adj_copy["level"] = assign_level(desc_key)
                            adjacency_rules.append(adj_copy)
                        
                # Add area rules locally
                for a_rule in ent_rules.get("area_rules", []):
                    rule_copy = dict(a_rule)
                    rule_copy["level"] = assign_level(rule_copy["rule"])
                    area_rules_list.append(rule_copy)
                
        # Default interior constraints
        interior = {
            "required_rooms": required_rooms,
            "room_specs": room_specs,
            "adjacency_rules": adjacency_rules,
            "area_rules": area_rules_list,
            "corridor_max_fraction_of_usable": 0.15,
            "coverage_tol_fraction": 0.05
        }
        
        # Inject user global overrides into interior
        if user_global_overrides:
            interior.update(user_global_overrides)
        
        # 2.5 Apply Zone Specific Rules
        if zone:
            # Sanitize jurisdiction name for the table lookup (e.g. "Seattle, WA" -> "Seattle_WA")
            loc = jurisdiction_name.replace(", ", "_").replace(" ", "_")
            try:
                cursor.execute(f'''
                    SELECT rule_key, rule_value, description 
                    FROM ZoneRules_{loc} 
                    WHERE zone=?
                ''', (zone,))
                for row in cursor.fetchall():
                    key, val_str, desc = row[0], row[1], row[2]
                    try:
                        val = float(val_str)
                    except:
                        val = val_str
                        
                    if key in exterior:
                        exterior[key] = val
                    else:
                        interior[key] = val
                        
                    if desc:
                        descriptions[key] = desc
            except sqlite3.OperationalError:
                pass
                
        # Inject user descriptions
        if user_descriptions:
            descriptions.update(user_descriptions)
            
        # 3. Apply Overrides (if any)
        if overrides:
            if 'exterior' in overrides:
                exterior.update(overrides['exterior'])
            if 'interior' in overrides:
                interior.update(overrides['interior'])
                
        # 4. Assemble final JSON
        # Ensure default descriptions are added for exterior base rules
        for key in exterior.keys():
            if key not in descriptions and key in self.DEFAULT_DESCRIPTIONS:
                descriptions[key] = self.DEFAULT_DESCRIPTIONS[key]

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
            for ent, overrides in room_overrides.items():
                for k in overrides.keys():
                    if k not in constraint_levels:
                        constraint_levels[k] = "hard"
        if user_global_overrides:
            for k in user_global_overrides.keys():
                if k not in constraint_levels:
                    constraint_levels[k] = "hard"

        final_schema = {
            "jurisdiction": jurisdiction_name,
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
        
        # 5. Hash, save to DB, and return ID
        json_str = json.dumps(final_schema, sort_keys=True)
        version_id = "ruleset_" + hashlib.sha256(json_str.encode('utf-8')).hexdigest()[:12]
        
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO AgentOutputs (id, data_json)
            VALUES (?, ?)
        ''', (version_id, json_str))
        conn.commit()
        conn.close()
        
        return version_id

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 constraint_agent.py <zoning_hashkey>")
        sys.exit(1)
        
    zoning_hashkey = sys.argv[1]
    
    try:
        agent = ConstraintAgent()
        ruleset_id = agent.process_zoning_input(zoning_hashkey)
        print(f"Success! Generated Final Ruleset ID: {ruleset_id}")
    except Exception as e:
        print(f"Error running Constraint Agent: {e}")
