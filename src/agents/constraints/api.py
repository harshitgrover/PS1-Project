import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import os
import sys

# ── MONITORING IMPORTS ─────────────────────────────────────────────
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram

# Add the project root to sys.path so absolute imports like 'src.agents...' work
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from src.agents.constraints.constraint_agent import ConstraintAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Constraint Agent API")

Instrumentator().instrument(app).expose(app)

REQUEST_COUNT = Counter("agent_requests_total", "Total requests", ["agent_name", "status"])
INFERENCE_LATENCY = Histogram("agent_inference_latency_seconds", "Time per /run request")
MODEL_ERROR_COUNT = Counter("agent_model_errors_total", "LLM/solver errors", ["agent_name", "error_type"])

class FileRef(BaseModel):
    type: str
    bucket: str
    key: str

class ConstraintRequest(BaseModel):
    session_id: str
    Properties: Dict[str, Any]
    file_refs: Optional[List[FileRef]] = []

@app.get("/health")
async def health():
    """
    Returns the health status of the agent.

    Args:
        None

    Returns:
        dict: A dictionary containing the status and agent name.
    """
    return {"status": "ok", "agent": "constraint_agent"}

@app.post("/api/v1/constraints")
@app.post("/run")
@INFERENCE_LATENCY.time()
def generate_constraints(request: ConstraintRequest) -> dict:
    """
    Accepts a ConstraintRequest, triggers constraint generation synchronously,
    and returns the final constraint schema.

    Args:
        request (ConstraintRequest): The incoming request payload containing session_id and Properties.

    Returns:
        dict: A dictionary containing the session_id, status, file_refs, and the generated schema.
    """
    try:
        # Get ECE URL from environment
        ece_url = os.environ["ECE_URL"]
        agent = ConstraintAgent(entity_engine_url=ece_url)
        
        # location_zoning_output and user_constraints come from Properties
        # user_constraints may come directly (for testing) or via planner_output
        zoning_output = request.Properties.get("location_zoning_output", {})
        zoning_schema = zoning_output.get("Properties", {}).get("schema", {})
        
        planner_data = request.Properties.get("planner_output", {})
        raw_user_constraints = request.Properties.get("user_constraints") or planner_data.get("user_constraints")
        user_constraints = str(raw_user_constraints) if raw_user_constraints else ""
        
        # process_zoning_input returns final_schema
        final_schema = agent.process_zoning_input(zoning_schema, user_text=user_constraints)
        
        REQUEST_COUNT.labels(agent_name="constraint_agent", status="success").inc()
        
        # Prepare the response payload matching standard Option B
        return {
            "session_id": request.session_id,
            "status": "success",
            "file_refs": [],
            "Properties": {
                "schema": final_schema
            }
        }
    except Exception as e:
        REQUEST_COUNT.labels(agent_name="constraint_agent", status="error").inc()
        MODEL_ERROR_COUNT.labels(
            agent_name="constraint_agent",
            error_type=type(e).__name__
        ).inc()
        # Check if it's our custom validation error by checking class name
        if type(e).__name__ == "ConstraintValidationError":
            reasons = getattr(e, "reasons", [str(e)])
            logger.error(f"Validation Error for {request.session_id}: {reasons}")
            return {
                "session_id": request.session_id,
                "status": "failed",
                "file_refs": [],
                "Properties": {
                    "error": "Constraint validation failed",
                    "validation_errors": reasons,
                    "agent": "constraint_agent"
                }
            }
            
        logger.error(f"Error generating constraints for {request.session_id}: {e}", exc_info=True)
        return {
            "session_id": request.session_id,
            "status": "failed",
            "file_refs": [],
            "Properties": {
                "error": str(e),
                "agent": "constraint_agent"
            }
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
