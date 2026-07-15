from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import tempfile
import os
import uuid
import json
import boto3
import logging

from src.tools.dxf_generator.dxf_generator import generate_dxf

# ── MONITORING IMPORTS ─────────────────────────────────────────────
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="DXF Generator API")

Instrumentator().instrument(app).expose(app)

REQUEST_COUNT = Counter("agent_requests_total", "Total requests", ["agent_name", "status"])
INFERENCE_LATENCY = Histogram("agent_inference_latency_seconds", "Time per /run request")
MODEL_ERROR_COUNT = Counter("agent_model_errors_total", "LLM/solver errors", ["agent_name", "error_type"])

class FileRef(BaseModel):
    """
    Reference to a file stored in S3.
    """
    type: str
    bucket: str
    key: str

class DXFRequest(BaseModel):
    """
    Request model for DXF generation endpoint.
    """
    session_id: str
    Properties: Dict[str, Any]
    file_refs: Optional[List[FileRef]] = []

def cleanup_files(*file_paths):
    """
    Removes temporary local files after they have been uploaded to S3.
    Silently ignores files that do not exist or cannot be deleted.

    Args:
        *file_paths (str): Variable number of file path strings to delete.

    Returns:
        None
    """
    for path in file_paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
                logger.debug(f"Cleaned up temporary file: {path}")
        except Exception:
            pass

@app.get("/health")
def health_check() -> dict:
    """
    Returns the health status of the agent.

    Args:
        None

    Returns:
        dict: A dictionary containing the status and agent name.
    """
    return {"status": "ok", "agent": "dxf_generator"}

@app.post("/run")
@INFERENCE_LATENCY.time()
def generate_dxf_endpoint(request: DXFRequest, background_tasks: BackgroundTasks) -> dict:
    """
    Synchronously generates a DXF file (and PNG if render is True) from the input JSON data,
    uploads to S3, and returns the file reference(s).

    Args:
        request (DXFRequest): The incoming request payload containing the layout output.
        background_tasks (BackgroundTasks): FastAPI background tasks manager for cleanup.

    Returns:
        dict: A dictionary containing the session_id, status, file_refs, and properties.
    """
    try:
        temp_dir = tempfile.gettempdir()
        file_id = str(uuid.uuid4())
        
        json_path = os.path.join(temp_dir, f"{file_id}.json")
        dxf_path = os.path.join(temp_dir, f"{file_id}.dxf")
        img_prefix = os.path.join(temp_dir, f"{file_id}")
        
        # Get data from the upstream agent's output block (e.g. layout_output, site_plan_output)
        data = request.Properties
        for key, value in request.Properties.items():
            if key.endswith("_output") and isinstance(value, dict):
                data = value
                break
        
        with open(json_path, 'w') as f:
            json.dump(data, f)
            
        render_preview = request.Properties.get("render_preview", False)
        # Call the orchestrator logic (json_paths must be a list)
        generate_dxf([json_path], dxf_path, render=render_preview, out_img_prefix=img_prefix)
        
        if not os.path.exists(dxf_path):
            raise Exception("Failed to generate DXF file")
            
        # Upload to S3
        aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        bucket_name = os.environ.get('S3_BUCKET_NAME', 'shared-bucket-name')
        
        iteration = request.Properties.get("iteration_number", 1)
        
        s3 = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        s3_key_dxf = f"dxf_generator/{request.session_id}/{iteration}_dxf.dxf"
        s3.upload_file(Filename=dxf_path, Bucket=bucket_name, Key=s3_key_dxf)
        
        file_refs = [
            {"type": "dxf", "bucket": bucket_name, "key": s3_key_dxf}
        ]
        
        cleanup_list = [json_path, dxf_path]
        
        if render_preview:
            png_path = f"{img_prefix}_preview.png"
            if os.path.exists(png_path):
                s3_key_png = f"dxf_generator/{request.session_id}/{iteration}_png.png"
                s3.upload_file(Filename=png_path, Bucket=bucket_name, Key=s3_key_png)
                file_refs.append({"type": "png", "bucket": bucket_name, "key": s3_key_png})
                cleanup_list.append(png_path)
        
        # Clean up local files
        background_tasks.add_task(cleanup_files, *cleanup_list)
        
        REQUEST_COUNT.labels(agent_name="dxf_generator", status="success").inc()
        return {
            "session_id": request.session_id,
            "status": "success",
            "file_refs": file_refs,
            "Properties": {
                "message": "Files generated and uploaded successfully."
            }
        }
        
    except HTTPException:
        REQUEST_COUNT.labels(agent_name="dxf_generator", status="error").inc()
        raise
    except Exception as e:
        REQUEST_COUNT.labels(agent_name="dxf_generator", status="error").inc()
        MODEL_ERROR_COUNT.labels(agent_name="dxf_generator", error_type=type(e).__name__).inc()
        logger.error(f"Error generating DXF for {request.session_id}: {e}", exc_info=True)
        return {
            "session_id": request.session_id,
            "status": "failed",
            "file_refs": [],
            "Properties": {
                "error": str(e),
                "agent": "dxf_generator"
            }
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
