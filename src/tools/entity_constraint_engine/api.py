import sys
import os
import logging

# Add the project root to sys.path so absolute imports like 'src.tools...' work
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from src.tools.entity_constraint_engine.entity_constraint_engine import EntityConstraintEngine

# ── MONITORING IMPORTS ─────────────────────────────────────────────
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Entity Constraint Engine API")

Instrumentator().instrument(app).expose(app)

REQUEST_COUNT = Counter("agent_requests_total", "Total requests", ["agent_name", "status"])
INFERENCE_LATENCY = Histogram("agent_inference_latency_seconds", "Time per /run request")
MODEL_ERROR_COUNT = Counter("agent_model_errors_total", "LLM/solver errors", ["agent_name", "error_type"])

# Setup the engine
engine = EntityConstraintEngine()

class EntityRulesRequest(BaseModel):
    entities: List[str]
    include_relations: bool = True

class EntityRulesResponse(BaseModel):
    # Map of entity name to their rules
    entities: Dict[str, Any]

@app.get("/health")
def health_check() -> dict:
    """
    Returns the health status of the agent.

    Args:
        None

    Returns:
        dict: A dictionary containing the status and agent name.
    """
    return {"status": "ok", "agent": "entity_engine"}

@app.post("/api/v1/entity_constraints", response_model=EntityRulesResponse)
@app.post("/run", response_model=EntityRulesResponse)
@INFERENCE_LATENCY.time()
def get_rules(request: EntityRulesRequest) -> dict:
    """
    Synchronously fetches the rules for a list of entity types.

    Args:
        request (EntityRulesRequest): The incoming request containing the list of entities.

    Returns:
        dict: A dictionary containing the rules for each requested entity.
    """
    try:
        result = engine.get_entities_rules(request.entities, request.include_relations)
        if not result:
            REQUEST_COUNT.labels(agent_name="entity_engine", status="error").inc()
            raise HTTPException(status_code=404, detail="No entities found")
        
        REQUEST_COUNT.labels(agent_name="entity_engine", status="success").inc()
        return {"entities": result}
    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels(agent_name="entity_engine", status="error").inc()
        MODEL_ERROR_COUNT.labels(agent_name="entity_engine", error_type=type(e).__name__).inc()
        logger.error(f"Error in get_rules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
