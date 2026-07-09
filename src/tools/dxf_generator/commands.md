# DXF Generator — Commands & Testing Guide

---

## 1. Run the API Server

Start the FastAPI server (defaults to port 8003):

```bash
# From project root
source venv/bin/activate
python3 -m src.tools.dxf_generator.api
```

---

## 2. Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `GET`  | `/health` | Health check — confirms server is alive |
| `GET`  | `/metrics` | Prometheus metrics (auto-exposed) |
| `POST` | `/run` | Main endpoint — generate DXF and upload to S3 |
| `POST` | `/api/v1/generate_dxf` | Alias for `/run` |

---

## 3. Manual Testing (cURL)

**Step 1 — Start the server:**
```bash
source venv/bin/activate
python3 -m src.tools.dxf_generator.api
```

**Step 2 — Health check:**
```bash
curl http://localhost:8003/health
# Expected: {"status": "ok", "agent": "dxf_generator"}
```

**Step 3 — Check metrics:**
```bash
curl http://localhost:8003/metrics
# Expected: text starting with "# HELP"
```

**Step 4 — Call /run with a layout payload:**
```bash
curl -X POST "http://localhost:8003/run" \
     -H "Content-Type: application/json" \
     -d @src/tools/dxf_generator/demo_inputs/floor_plan.json
```

**Step 5 — Verify metrics updated:**
```bash
curl http://localhost:8003/metrics | grep agent_requests_total
# Expected: agent_requests_total{agent_name="dxf_generator",status="success"} 1.0
```

---

## 4. Automated Unit Tests (Test Script)

Run from the **project root** using the virtual environment:

```bash
source venv/bin/activate
python -m unittest src/tools/dxf_generator/test_dxf_generator.py -v
```

**What each test checks:**
- `test_health_check_returns_ok` — `/health` returns 200 with correct body
- `test_run_endpoint_exists` — `/run` route is registered (not 404)
- `test_cleanup_removes_existing_file` — `cleanup_files` deletes a real temp file
- `test_cleanup_ignores_nonexistent_file` — `cleanup_files` does not raise on missing files
- `test_cleanup_handles_multiple_files` — `cleanup_files` handles several paths at once
- `test_cleanup_handles_none_path` — `cleanup_files` silently skips `None` and empty strings
- `test_generate_dxf_produces_output_file` — End-to-end: a valid JSON produces a real `.dxf` file
- `test_generate_dxf_is_deterministic` — Same input always produces the same output size (no LLM)

---

## 5. CLI Usage

The DXF Generator can also be run directly from the command line without the API server.

> **Universal JSON Fallback**: The parser automatically detects and extracts geometric data from any JSON structure, even if it doesn't match the standard schema.

**Generate a single DXF:**
```bash
python3 -m src.tools.dxf_generator \
    src/tools/dxf_generator/demo_inputs/floor_plan.json \
    floor_plan.dxf
# Output saved to: src/tools/dxf_generator/demo_outputs/floor_plan.dxf
```

**Generate a combined DXF from multiple inputs:**
```bash
python3 -m src.tools.dxf_generator \
    src/tools/dxf_generator/demo_inputs/site_plan.json \
    src/tools/dxf_generator/demo_inputs/floor_plan.json \
    combined_plan.dxf
```

**Generate with a visual PNG preview:**
```bash
python3 -m src.tools.dxf_generator \
    src/tools/dxf_generator/demo_inputs/floor_plan.json \
    floor_plan.dxf \
    --render
```

**Custom prefix for rendered images:**
```bash
python3 -m src.tools.dxf_generator \
    src/tools/dxf_generator/demo_inputs/floor_plan.json \
    floor_plan.dxf \
    --render --img-prefix my_preview
```

> **Auto File Routing**: If you give a plain filename (not a full path) as output, files are automatically saved to `demo_outputs/` inside the tool directory.
