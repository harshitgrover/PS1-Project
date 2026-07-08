# Verifier Agent Commands

## Installation
First, ensure you are in the `Verifier-Agent` directory and install the required dependencies:
```bash
pip install -r requirements.txt
```

## Running the Server
To run the FastAPI server locally for development:
```bash
python3 -m src.agents.verifier.api
```
*The API will be available at `http://127.0.0.1:8000`. This root URL hosts the interactive Verifier Agent Core dashboard for testing JSON payloads.*

## Running Tests
To run the automated tests via FastAPI's `TestClient`:
```bash
python3 test_api.py
```

## Manual Testing via cURL
You can manually test the endpoints using `curl` with the provided demo inputs.

**Pass scenario (Dynamic Seattle Exterior):**
```bash
curl -X POST "http://127.0.0.1:8000/verify" \
     -H "Content-Type: application/json" \
     -d @demo_inputs/dynamic_seattle.json
```

**Dynamic Interior testing:**
```bash
curl -X POST "http://127.0.0.1:8000/verify" \
     -H "Content-Type: application/json" \
     -d @demo_inputs/dynamic_interior.json
```

```bash
mkdir -p json_files && \
curl -s -X POST "http://127.0.0.1:8000/verify" \
     -H "Content-Type: application/json" \
     -d @demo_inputs/dynamic_interior.json | jq . > json_files/interior_output.json
```

---

# API Usage

The API runs via FastAPI (defaults to port 8000):

```bash
python3 -m src.agents.verifier.api
```

### Endpoints
- **`GET /`**: Renders the interactive Verifier Agent Core dashboard.
- **`POST /verify`**: Evaluates proposed geometric layouts against Z3 constraints.

**Example cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/verify" \
     -H "Content-Type: application/json" \
     -d @demo_inputs/dynamic_seattle.json
```
