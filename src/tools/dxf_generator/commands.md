# DXF Generator Commands

## CLI Usage

The DXF Generator can ingest one or *multiple* JSON files simultaneously. If you pass multiple files, they will be combined into a single, perfectly layered DXF (e.g., overlapping a site plan and floor plan).

> **Universal JSON Fallback**: The parser has been upgraded to automatically detect and extract geometric data (2D coordinate arrays like `[[x,y], [x,y]]`) from **any** JSON structure, even if it doesn't match a known schema (e.g. raw GeoJSON). It will dynamically assign layer names based on the keys where it found the coordinates!

**Generate a Single DXF:**
```bash
python3 -m src.tools.dxf_generator.dxf_generator src/tools/dxf_generator/demo_inputs/floor_plan.json floor_plan.dxf
```

**Generate a Combined DXF (Multiple Inputs):**
```bash
python3 -m src.tools.dxf_generator.dxf_generator src/tools/dxf_generator/demo_inputs/site_plan.json src/tools/dxf_generator/demo_inputs/floor_plan.json combined_plan.dxf
```

> **Automatic File Routing:** If you specify a simple filename for the output (like `floor_plan.dxf` above) instead of an absolute path, the engine will automatically create a `generated_files/` folder inside the tool directory and cleanly save all `.dxf` and `.png` outputs there!

**Generate with Visual Preview:**
Add the `--render` flag to automatically generate a rich, color-coded `matplotlib` PNG preview alongside the DXF output.

```bash
python3 -m src.tools.dxf_generator.dxf_generator src/tools/dxf_generator/demo_inputs/floor_plan.json floor_plan.dxf --render
```

**Custom Prefix for Renders:**
```bash
python3 -m src.tools.dxf_generator.dxf_generator src/tools/dxf_generator/demo_inputs/floor_plan.json floor_plan.dxf --render --img-prefix custom_prefix
```

## API Usage

Start the synchronous FastAPI endpoint on port `8002`:

```bash
python3 -m src.tools.dxf_generator.api
```

### Endpoints

- **`GET /health`**: Health check.
- **`POST /api/v1/generate_dxf`**: Send a JSON payload containing `data` (the plan structure) and optionally `render_preview` (boolean). The endpoint will synchronously return the generated `.dxf` file as an `application/dxf` binary attachment.

### How to Call the API

Once the server is running (`python3 -m src.tools.dxf_generator.api`), another agent or script can call it to get a DXF file.

#### Using cURL:
```bash
curl -X POST "http://localhost:8002/api/v1/generate_dxf" \
     -H "Content-Type: application/json" \
     -d '{"data": {"job_id": "test", "boundary": [[0,0], [10,0], [10,10], [0,10]]}}' \
     --output my_generated_file.dxf
```
