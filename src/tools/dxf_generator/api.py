from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import tempfile
import os
import uuid
import json
import boto3

from src.tools.dxf_generator.dxf_generator import generate_dxf

app = FastAPI(title="DXF Generator API")

class FileRef(BaseModel):
    type: str
    bucket: str
    key: str

class DXFRequest(BaseModel):
    session_id: str
    Properties: Dict[str, Any]
    file_refs: Optional[List[FileRef]] = []

def cleanup_files(*file_paths):
    for path in file_paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/v1/generate_dxf")
def generate_dxf_endpoint(request: DXFRequest, background_tasks: BackgroundTasks):
    """
    Synchronously generates a DXF file (and PNG if render is True) from the input JSON data,
    uploads to S3, and returns the file reference(s).
    """
    try:
        temp_dir = tempfile.gettempdir()
        file_id = str(uuid.uuid4())
        
        json_path = os.path.join(temp_dir, f"{file_id}.json")
        dxf_path = os.path.join(temp_dir, f"{file_id}.dxf")
        img_prefix = os.path.join(temp_dir, f"{file_id}")
        
        # Get data from layout_output or directly from Properties
        data = request.Properties.get("layout_output", request.Properties)
        
        with open(json_path, 'w') as f:
            json.dump(data, f)
            
        render_preview = request.Properties.get("render_preview", False)
        # Call the orchestrator logic (json_paths must be a list)
        generate_dxf([json_path], dxf_path, render=render_preview, out_img_prefix=img_prefix)
        
        if not os.path.exists(dxf_path):
            raise HTTPException(status_code=500, detail="Failed to generate DXF file")
            
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
        
        return {
            "session_id": request.session_id,
            "status": "success",
            "file_refs": file_refs,
            "Properties": {
                "message": "Files generated and uploaded successfully."
            }
        }
        
    except Exception as e:
        print(f"Error generating DXF for {request.session_id}: {e}")
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
    uvicorn.run(app, host="0.0.0.0", port=8003)
