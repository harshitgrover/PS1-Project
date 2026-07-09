import os
import json
import sys
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

logger = logging.getLogger(__name__)

load_dotenv()

class EntityConstraintEngine:
    """
    Execution layer for the constraint system. Reads per-entity rules (size, features,
    adjacency) from the Supabase database and serves them to the Constraint Agent.
    Acts as the single source of truth for both the Floor Plan Generator and the Verifier.
    """

    def __init__(self):
        """
        Initializes the EntityConstraintEngine by connecting to Supabase.
        Logs a warning if credentials are missing; does not raise so the
        server can still start and return graceful errors per-request.

        Args:
            None
        """
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            logger.warning("SUPABASE_URL or SUPABASE_KEY not set. Database queries will fail.")
        else:
            self.supabase: Client = create_client(supabase_url, supabase_key)
            logger.debug("Supabase client initialized successfully.")

    def get_entity_rules(self, entity_type: str, include_relations: bool = True) -> dict:
        """
        Retrieves the size rules (and optionally adjacency rules) for a specific entity.
        Returns a dictionary with the entity's constraints.

        Args:
            entity_type (str): The type of entity to fetch rules for (e.g., 'bedroom').
            include_relations (bool): Whether to include adjacency/relational rules. Defaults to True.

        Returns:
            dict: A dictionary containing the entity's size_rules, feature_rules, and relational_rules.
        """
        if not hasattr(self, 'supabase'):
            return {"status": "no_data", "message": "Supabase client not initialized."}
            
        # 1. Get entity size rules and feature rules
        try:
            response = self.supabase.table("entity_specs").select("*").eq("entity_type", entity_type).execute()
        except Exception as e:
            logger.error(f"Error querying Supabase entity_specs: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
            
        if not response.data:
            return {"status": "no_data", "message": f"Entity '{entity_type}' not found."}
            
        raw_row = response.data[0]
        assert isinstance(raw_row, dict)
        row: dict = raw_row
         
        size_rules = {
            "min_area_ft2": row.get("min_area_ft2"),
            "min_side_ft": row.get("min_side_ft"),
            "max_side_ft": row.get("max_side_ft"),
            "min_aspect_ratio": row.get("min_aspect_ratio"),
            "max_aspect_ratio": row.get("max_aspect_ratio"),
            "habitable": bool(row.get("habitable")) if row.get("habitable") is not None else None
        }
        
        feature_rules = {
            "requires_exterior_window": bool(row.get("requires_exterior_window")) if row.get("requires_exterior_window") is not None else None,
            "requires_egress": bool(row.get("requires_egress")) if row.get("requires_egress") is not None else None,
            "ventilation_type": row.get("ventilation_type"),
            "requires_door": bool(row.get("requires_door")) if row.get("requires_door") is not None else None,
            "requires_closet": bool(row.get("requires_closet")) if row.get("requires_closet") is not None else None
        }
        
        # Remove nulls for cleaner output matching schema
        size_rules = {k: v for k, v in size_rules.items() if v is not None}
        feature_rules = {k: v for k, v in feature_rules.items() if v is not None}
        
        # 2. Get relational rules if requested
        relational_rules = []
        if include_relations:
            try:
                rel_res = self.supabase.table("adjacency_rules").select("*").eq("source_entity", entity_type).execute()
                for rel_row_raw in rel_res.data:
                    if not isinstance(rel_row_raw, dict):
                        continue
                    rel_row: dict = rel_row_raw
                    # We format it to a/b so it looks identical to the old schema downstream
                    rule = {"a": entity_type, "b": rel_row.get("target_entity"), "relation": rel_row.get("relation")}
                    if rel_row.get("min_shared_wall_ft") is not None:
                        rule["min_shared_wall_ft"] = rel_row.get("min_shared_wall_ft")
                    if rel_row.get("max_dist_ft") is not None:
                        rule["max_dist_ft"] = rel_row.get("max_dist_ft")
                    if rel_row.get("description") is not None:
                        rule["description"] = rel_row.get("description")
                    relational_rules.append(rule)
            except Exception as e:
                logger.error(f"Error querying Supabase adjacency_rules: {e}", exc_info=True)
                
        area_rules_json = row.get("area_rules_json")
        
        
        try:
            area_rules = json.loads(str(area_rules_json)) if area_rules_json else []
        except json.JSONDecodeError:
            area_rules = []
            
        return {
            "entity_type": entity_type,
            "version": "v1",
            "size_rules": size_rules,
            "feature_rules": feature_rules,
            "relational_rules": relational_rules,
            "area_rules": area_rules
        }

    def get_entities_rules(self, entities: list, include_relations: bool = True) -> dict:
        """
        Retrieves the size rules (and optionally adjacency rules) for a list of entities.
        Filters the adjacency rules so they only link the requested entities, dropping extras.
        Returns a dictionary mapping entity_type to its constraints.

        Args:
            entities (list): A list of entity type strings to fetch rules for.
            include_relations (bool): Whether to include adjacency/relational rules. Defaults to True.

        Returns:
            dict: A mapping of entity_type to its full ruleset dictionary.
        """
        result = {}
        for entity in entities:
            logger.debug(f"Fetching rules for entity: '{entity}'")
            res = self.get_entity_rules(entity, include_relations)
            if res.get("status") != "no_data":
                # Filter out relations pointing to entities outside the requested list
                # ONLY if we requested multiple entities. If exactly 1 is requested, return all its relations.
                if include_relations and "relational_rules" in res and len(entities) > 1:
                    original_count = len(res["relational_rules"])
                    res["relational_rules"] = [
                        rule for rule in res["relational_rules"]
                        if rule["b"] in entities
                    ]
                    logger.debug(
                        f"Entity '{entity}': filtered relational_rules from "
                        f"{original_count} to {len(res['relational_rules'])} (kept only requested entities)"
                    )

                result[entity] = res
        return result

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Silence httpx to prevent it from spamming every Supabase API call
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if len(sys.argv) < 2:
        logger.info("Usage: python3 entity_constraint_engine.py <entity_type> [entity_type2 ...]")
        logger.info("Example: python3 entity_constraint_engine.py bedroom")
        logger.info("         python3 entity_constraint_engine.py bedroom bathroom kitchen")
        logger.info("         python3 entity_constraint_engine.py all")
        sys.exit(1)
        
    engine = EntityConstraintEngine()
    args = [arg.lower() for arg in sys.argv[1:]]
    
    out_dir = os.path.join(os.path.dirname(__file__), 'json_files')
    os.makedirs(out_dir, exist_ok=True)
    
    if "all" in args:
        entities = []
        if hasattr(engine, 'supabase'):
            try:
                res = engine.supabase.table("entity_specs").select("entity_type").execute()
                entities = [str(r["entity_type"]) for r in res.data if isinstance(r, dict)]
            except Exception as e:
                logger.error(f"Error fetching entities from Supabase: {e}", exc_info=True)
        
        all_rules = {}
        for ent in entities:
            all_rules[ent] = engine.get_entity_rules(ent)
            
        filename = "all_entities.json"
        out_path = os.path.join(out_dir, filename)
        with open(out_path, 'w') as f:
            json.dump(all_rules, f, indent=2)
        logger.info(f"Success! Output saved to: json_files/{filename}")
        
    elif len(args) == 1:
        result = engine.get_entity_rules(args[0])
        if result.get("status") == "no_data":
            logger.error(f"Error: {result['message']}")
        else:
            filename = f"{args[0]}.json"
            out_path = os.path.join(out_dir, filename)
            with open(out_path, 'w') as f:
                json.dump(result, f, indent=2)
            logger.info(f"Success! Output saved to: json_files/{filename}")
            
    else:
        multi_rules = {}
        for ent in args:
            multi_rules[ent] = engine.get_entity_rules(ent)
            
        filename = "_".join(args) + ".json"
        out_path = os.path.join(out_dir, filename)
        with open(out_path, 'w') as f:
            json.dump(multi_rules, f, indent=2)
        logger.info(f"Success! Output saved to: json_files/{filename}")
