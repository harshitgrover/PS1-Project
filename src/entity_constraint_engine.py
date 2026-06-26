import sqlite3
import os
import json
import sys

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

class EntityConstraintEngine:
    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = db_path
        
    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def get_entity_rules(self, entity_type: str, include_relations: bool = True) -> dict:
        """
        Retrieves the size rules (and optionally adjacency rules) for a specific entity.
        Returns a dictionary with the entity's constraints.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 1. Get entity size rules and feature rules
        cursor.execute('''
            SELECT min_area_ft2, min_side_ft, max_side_ft, habitable, min_aspect_ratio, max_aspect_ratio, requires_exterior_window, requires_egress, ventilation_type, requires_door, requires_closet, area_rules_json 
            FROM EntitySpecs 
            WHERE entity_type=?
        ''', (entity_type,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {"status": "no_data", "message": f"Entity '{entity_type}' not found."}
            
        (min_area, min_side, max_side, habitable, min_aspect, max_aspect, req_window, req_egress, vent_type, req_door, req_closet, area_rules_json) = row
         
        size_rules = {
            "min_area_ft2": min_area,
            "min_side_ft": min_side,
            "max_side_ft": max_side,
            "min_aspect_ratio": min_aspect,
            "max_aspect_ratio": max_aspect,
            "habitable": bool(habitable)
        }
        
        feature_rules = {
            "requires_exterior_window": bool(req_window) if req_window is not None else None,
            "requires_egress": bool(req_egress) if req_egress is not None else None,
            "ventilation_type": vent_type,
            "requires_door": bool(req_door) if req_door is not None else None,
            "requires_closet": bool(req_closet) if req_closet is not None else None
        }
        
        # Remove nulls for cleaner output matching schema
        size_rules = {k: v for k, v in size_rules.items() if v is not None}
        feature_rules = {k: v for k, v in feature_rules.items() if v is not None}
        
        # 2. Get relational rules if requested
        relational_rules = []
        if include_relations:
            # Note: We query the specific adjacency table for this entity
            cursor.execute(f'''
                SELECT target_entity, relation, min_shared_wall_ft, max_dist_ft, description 
                FROM Adjacency_{entity_type}
            ''')
            rel_rows = cursor.fetchall()
            
            for target_entity, relation, min_wall, max_dist, description in rel_rows:
                # We format it to a/b so it looks identical to the old schema downstream
                rule = {"a": entity_type, "b": target_entity, "relation": relation}
                if min_wall is not None:
                    rule["min_shared_wall_ft"] = min_wall
                if max_dist is not None:
                    rule["max_dist_ft"] = max_dist
                if description is not None:
                    rule["description"] = description
                relational_rules.append(rule)
                
        conn.close()
        
        
        import json
        try:
            area_rules = json.loads(area_rules_json) if area_rules_json else []
        except json.JSONDecodeError:
            area_rules = []
            
        return {
            "entity_type": entity_type,
            "size_rules": size_rules,
            "feature_rules": feature_rules,
            "relational_rules": relational_rules,
            "area_rules": area_rules
        }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 entity_constraint_engine.py <entity_type> [entity_type2 ...]")
        print("Example: python3 entity_constraint_engine.py bedroom")
        print("         python3 entity_constraint_engine.py bedroom bathroom kitchen")
        print("         python3 entity_constraint_engine.py all")
        sys.exit(1)
        
    engine = EntityConstraintEngine()
    args = [arg.lower() for arg in sys.argv[1:]]
    
    out_dir = os.path.join(os.path.dirname(__file__), 'Entity_Constraints')
    os.makedirs(out_dir, exist_ok=True)
    
    if len(args) == 1 and args[0] == "all":
        conn = engine._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT entity_type FROM EntitySpecs")
        entities = [r[0] for r in cursor.fetchall()]
        conn.close()
        
        all_rules = {}
        for ent in entities:
            all_rules[ent] = engine.get_entity_rules(ent)
            
        filename = "all_entities.json"
        out_path = os.path.join(out_dir, filename)
        with open(out_path, 'w') as f:
            json.dump(all_rules, f, indent=2)
        print(f"Success! Output saved to: Entity_Constraints/{filename}")
        
    elif len(args) == 1:
        result = engine.get_entity_rules(args[0])
        if result.get("status") == "no_data":
            print(f"Error: {result['message']}")
        else:
            filename = f"{args[0]}.json"
            out_path = os.path.join(out_dir, filename)
            with open(out_path, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Success! Output saved to: Entity_Constraints/{filename}")
            
    else:
        multi_rules = {}
        for ent in args:
            multi_rules[ent] = engine.get_entity_rules(ent)
            
        filename = "_".join(args) + ".json"
        out_path = os.path.join(out_dir, filename)
        with open(out_path, 'w') as f:
            json.dump(multi_rules, f, indent=2)
        print(f"Success! Output saved to: Entity_Constraints/{filename}")
