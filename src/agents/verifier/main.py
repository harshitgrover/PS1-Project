from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import ValidationError
from contracts import VerificationRequest, VerificationResponse
from dispatcher import dispatch
import os

app = FastAPI(title="Verifier Agent API")

@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    with open(os.path.join(os.path.dirname(__file__), "index.html"), "r") as f:
        return f.read()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/constraints/supported")
def supported_constraints():
    return {
        "supported": [
            "front_setback", "rear_setback", "side_setback",
            "lot_coverage", "tree_buffer", "door_egress",
            "min_utilization", "room_min_area", "room_no_overlap"
        ]
    }

@app.post("/verify", response_model=VerificationResponse)
def verify_layout(request: VerificationRequest):
    """
    Accepts a VerificationRequest, processes it via the Dispatcher,
    and returns a VerificationResponse.
    Note: Geometric violations still return a 200 OK.
    """
    result, hard_violations, soft_violations = dispatch(request)
    
    return VerificationResponse(
        session_id=request.session_id,
        result=result,
        hard_violations=hard_violations,
        soft_violations=soft_violations
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
