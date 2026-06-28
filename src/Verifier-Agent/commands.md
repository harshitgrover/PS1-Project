# Verifier Agent Commands

## Installation
First, ensure you are in the `Verifier-Agent` directory and install the required dependencies:
```bash
pip install -r requirements.txt
```

## Running the Server
To run the FastAPI server locally for development:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
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
