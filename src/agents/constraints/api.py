from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import os
import sys

# Add the project root to sys.path so absolute imports like 'src.agents...' work
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from src.agents.constraints.constraint_agent import ConstraintAgent

app = FastAPI(title="Constraint Agent API")

class FileRef(BaseModel):
    type: str
    bucket: str
    key: str

class ConstraintRequest(BaseModel):
    session_id: str
    Properties: Dict[str, Any]
    file_refs: Optional[List[FileRef]] = []

@app.post("/api/v1/constraints")
def generate_constraints(request: ConstraintRequest):
    """
    Accepts a ConstraintRequest, triggers constraint generation synchronously,
    and returns the final constraint schema.
    """
    try:
        # Get ECE URL from environment
        ece_url = os.environ["ECE_URL"]
        agent = ConstraintAgent(entity_engine_url=ece_url)
        
        # location_zoning_output and user_constraints come from Properties
        zoning_data = request.Properties.get("location_zoning_output", {})
        raw_user_constraints = request.Properties.get("user_constraints")
        user_constraints = str(raw_user_constraints) if raw_user_constraints else ""
        
        # process_zoning_input returns final_schema
        final_schema = agent.process_zoning_input(zoning_data, user_text=user_constraints)
        
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
        # Check if it's our custom validation error by checking class name
        if type(e).__name__ == "ConstraintValidationError":
            reasons = getattr(e, "reasons", [str(e)])
            print(f"Validation Error for {request.session_id}: {reasons}")
            return {
                "session_id": request.session_id,
                "status": "failed",
                "file_refs": [],
                "Properties": {
                    "error_message": "Constraint validation failed",
                    "validation_errors": getattr(e, "reasons", [])
                }
            }
            
        print(f"Error generating constraints for {request.session_id}: {e}")
        return {
            "session_id": request.session_id,
            "status": "failed",
            "file_refs": [],
            "Properties": {
                "error_message": str(e)
            }
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
