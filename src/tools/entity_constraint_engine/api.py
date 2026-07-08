import sys
import os

# Add the project root to sys.path so absolute imports like 'src.tools...' work
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from src.tools.entity_constraint_engine.entity_constraint_engine import EntityConstraintEngine

app = FastAPI(title="Entity Constraint Engine API")

# Setup the engine
engine = EntityConstraintEngine()

class EntityRulesRequest(BaseModel):
    entities: List[str]
    include_relations: bool = True

class EntityRulesResponse(BaseModel):
    # Map of entity name to their rules
    entities: Dict[str, Any]

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/v1/entity_constraints", response_model=EntityRulesResponse)
def get_rules(request: EntityRulesRequest):
    """
    Synchronously fetches the rules for a list of entity types.
    """
    result = engine.get_entities_rules(request.entities, request.include_relations)
    if not result:
        raise HTTPException(status_code=404, detail="No entities found")
    return {"entities": result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
