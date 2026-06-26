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
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 1. Fetch Exterior rules for jurisdiction
        cursor.execute('''
            SELECT schema_version, source, status, tolerance_ft,
                   front_setback_ft, rear_setback_ft, side_setback_ft,
                   min_house_width_ft, min_house_depth_ft, door_corner_margin_ft,
                   max_lot_coverage_fraction, min_area_fraction_of_max, tree_protection_zone_json
            FROM Jurisdictions WHERE name=?
        ''', (jurisdiction_name,))
        
        row = cursor.fetchone()
        
        if not row:
            # If jurisdiction is missing, fail loudly per schema ("no_data")
            conn.close()
            return {
                "jurisdiction": jurisdiction_name,
                "status": "no_data",
                "message": f"Jurisdiction '{jurisdiction_name}' not found in database."
            }
            
        (schema_version, source, status, tolerance_ft, 
         front_sb, rear_sb, side_sb, min_w, min_d, door_m, 
         max_lot, min_area_frac, tree_json) = row
         
        tree_zone = json.loads(tree_json) if tree_json else {"type": "polygon", "coordinates": []}
        
        exterior = {
            "front_setback_ft": front_sb,
            "rear_setback_ft": rear_sb,
            "side_setback_ft": side_sb,
            "min_house_width_ft": min_w,
            "min_house_depth_ft": min_d,
            "door_corner_margin_ft": door_m,
            "max_lot_coverage_fraction": max_lot,
            "min_area_fraction_of_max": min_area_frac,
            "tree_protection_zone": tree_zone
        }
        
        # 2. Fetch Interior rules ONLY for required entities
        # required_rooms usually comes from Planner Agent, but we define a baseline here
        required_rooms = { "living": 1, "kitchen": 1, "corridor": 1, "bedroom": 3, "bathroom": 2, "balcony": 1 }
        
        room_specs = {}
        descriptions = {}
        entities = list(required_rooms.keys())
        
        for ent in entities:
            ent_rules = self.entity_engine.get_entity_rules(ent, include_relations=False)
            if ent_rules.get("status") != "no_data":
                specs = dict(ent_rules["size_rules"])
                if "feature_rules" in ent_rules:
                    specs.update(ent_rules["feature_rules"])
                room_specs[ent] = specs
                
        # 2b. Fetch relational rules in ONE bulk query using the indexes
        raw_adjacency_rules = self.entity_engine.get_bulk_relational_rules(entities)
        adjacency_rules = []
        
        for adj in raw_adjacency_rules:
            if "description" in adj:
                desc = adj.pop("description")
                desc_key = f"{adj['a']}_{adj['relation']}_{adj['b']}"
                descriptions[desc_key] = desc
            adjacency_rules.append(adj)
                        
        # Get area rules
        cursor.execute("SELECT rule, description FROM AreaRules")
        area_rules = []
        for rule, desc in cursor.fetchall():
            area_rules.append({"rule": rule})
            if desc:
                descriptions[rule] = desc
                
        # Default interior constraints (these could also be stored in DB per jurisdiction)
        interior = {
            "required_rooms": required_rooms,
            "room_specs": room_specs,
            "adjacency_rules": adjacency_rules,
            "area_rules": area_rules,
            "corridor_max_fraction_of_usable": 0.15,
            "coverage_tol_fraction": 0.05
        }
        
        # 2.5 Apply Zone Specific Rules
        if zone:
            cursor.execute('''
                SELECT rule_key, rule_value, description 
                FROM ZoneSpecificRules 
                WHERE jurisdiction=? AND zone=?
            ''', (jurisdiction_name, zone))
            zone_overrides = cursor.fetchall()
            
            for r_key, r_value, desc in zone_overrides:
                # Try parsing value as float
                try:
                    val = float(r_value)
                except ValueError:
                    val = r_value
                    
                if r_key in exterior:
                    exterior[r_key] = val
                else:
                    # Append all other rules (including novel ones) to the interior dictionary
                    interior[r_key] = val
                    
                if desc:
                    descriptions[r_key] = desc
                    
        conn.close()
        
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
        
        def assign_level(k):
            return self.DEFAULT_CONSTRAINT_LEVELS.get(k, "hard")
            
        for key in descriptions.keys():
            constraint_levels[key] = assign_level(key)
            
        for key in exterior.keys():
            constraint_levels[key] = assign_level(key)
            
        for room, specs in room_specs.items():
            for spec_key in specs.keys():
                constraint_levels[spec_key] = assign_level(spec_key)

        final_schema = {
            "jurisdiction": jurisdiction_name,
            "schema_version": schema_version,
            "source": source,
            "status": status,
            "tolerance_ft": tolerance_ft,
            "exterior": exterior,
            "interior": interior,
            "descriptions": descriptions,
            "constraint_levels": constraint_levels
        }
        
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
