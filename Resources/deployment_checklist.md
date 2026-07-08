# 📋 Agent Owner Checklist — What YOU Must Add to Your Code
### — Multi-Agent Deployment (Final Version, Verified)


> **Why:** The deployment team can only deploy, health-check, and monitor your agent if your code follows this exact contract.

---

## 🔑 The Contract — 3 Endpoints Your Agent MUST Expose

```
YOUR AGENT CODE
    │
    ├── POST /run        ← Your actual AI logic (you already have this)
    ├── GET  /health     ← "Am I alive?" — Kubernetes uses this to restart crashed pods
    └── GET  /metrics    ← "How am I performing?" — Prometheus scrapes this every 15s → Grafana graphs
```



---

## ✅ STEP 1 — Update `requirements.txt`

Add these monitoring libraries. Do not skip — they are needed for metrics.

### If your agent uses **FastAPI** (recommended):

```txt
# Monitoring libraries (REQUIRED — add these)
prometheus-fastapi-instrumentator>=6.1.0
prometheus-client>=0.20.0
```

### If your agent uses **Flask**:

```txt
# Monitoring libraries (REQUIRED — add these)
prometheus-client>=0.20.0
```

> ⚠️ **Note:** `prometheus-fastapi-instrumentator` only works with FastAPI.
> Flask agents use `prometheus-client` directly (no instrumentator package needed).

> 📌 Server dependencies (gunicorn, uvicorn) and Dockerfile are handled by the deployment team — you don't need to worry about those.

---

## ✅ STEP 2 — Add These Imports at the TOP of your main app file

### FastAPI agents:

```python
# ── MONITORING IMPORTS ─────────────────────────────────────────────
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram
```

### Flask agents:

```python
# ── MONITORING IMPORTS ─────────────────────────────────────────────
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from flask import Response   # you likely already have this
```

---

## ✅ STEP 3 — Define Your 3 Custom Metrics

Add these **immediately after** you create your `app` object.
These must be **module-level variables** (NOT inside any function).

```python
# ── AFTER: app = FastAPI(...)  OR  app = Flask(__name__) ──────────

# METRIC 1 — Request counter
# Counts every /run call, labelled by success or error
# Grafana query: rate(agent_requests_total[5m]) — shows live call rate per agent
REQUEST_COUNT = Counter(
    "agent_requests_total",
    "Total requests handled by this agent",
    ["agent_name", "status"]    # ← change "planner" to your agent's name in .labels() calls below
)

# METRIC 2 — Inference latency histogram
# Records how long each /run call takes
# Grafana query: histogram_quantile(0.95, rate(agent_inference_latency_seconds_bucket[5m]))
# → "95% of /run calls finish within X seconds"
INFERENCE_LATENCY = Histogram(
    "agent_inference_latency_seconds",
    "Time taken to process one /run request (includes LLM call + solver)"
)

# METRIC 3 — Model/solver error counter
# Counts Gemini API failures, Z3 timeouts, Groq errors — separate from HTTP errors
# Grafana query: rate(agent_model_errors_total[5m]) — alerts you to LLM issues
MODEL_ERROR_COUNT = Counter(
    "agent_model_errors_total",
    "Failed LLM API calls or solver errors (NOT HTTP 500s)",
    ["agent_name", "error_type"]
)
```

**SIMPLE :**
- `Counter` → only goes UP. Like a tally. "How many times did X happen?"
- `Histogram` → records durations, auto-calculates p50/p90/p95/p99. "How long did it take?"

---

## ✅ STEP 4 — Wire Prometheus Auto-Instrumentation (FastAPI ONLY — 1 line)

```python
# Add this line IMMEDIATELY AFTER: app = FastAPI(...)
# This one line:
#   1. Creates the /metrics endpoint automatically
#   2. Auto-tracks ALL routes: request count, latency, status codes
Instrumentator().instrument(app).expose(app)
```

FastAPI agents: **you now have `/metrics` for free.** Skip Step 7.

Flask agents: **skip this step entirely.** You will manually add `/metrics` in Step 7.

---

## ✅ STEP 5 — Add the `/health` Endpoint

```python
# ── FastAPI version ──────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "agent": "planner"}   # ← change agent name


# ── Flask version ────────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok", "agent": "planner"})   # ← change agent name
```

**What Kubernetes does with this:**
- Calls `GET /health` every 15–20 seconds (**liveness probe**)
- Calls `GET /health` every 10 seconds before sending traffic (**readiness probe**)
- If it fails 3 times in a row → **automatically restarts your pod**
- The deployment team writes the probe YAML — you just need this route to exist and return 200

> ⚠️ **Critical:** This endpoint must NEVER crash. Keep it simple — just return `{"status": "ok"}`. Do NOT put database calls or heavy logic here.

---

## ✅ STEP 6 — Instrument Your `/run` Endpoint

Wrap your existing logic. **Your internal logic does not change at all.**

### FastAPI:

```python
@app.post("/run")
@INFERENCE_LATENCY.time()          # ← ADD: auto-times how long this function takes
async def run(payload: dict):
    try:
        result = your_existing_agent_logic(payload)    # ← your code, UNCHANGED
        REQUEST_COUNT.labels(agent_name="planner", status="success").inc()
        return result
    except Exception as e:
        REQUEST_COUNT.labels(agent_name="planner", status="error").inc()
        MODEL_ERROR_COUNT.labels(
            agent_name="planner",
            error_type=type(e).__name__     # e.g. "TimeoutError", "ValueError"
        ).inc()
        raise   # ← IMPORTANT: re-raise so FastAPI returns proper HTTP 500

# STANDARDISED ERROR RESPONSE — if you catch errors and return manually:
# return JSONResponse(
#     status_code=500,
#     content={"error": str(e), "agent": "planner", "status": "error"}
# )
```

### Flask:

```python
@app.route("/run", methods=["POST"])
def run():
    with INFERENCE_LATENCY.time():    # ← ADD: context manager version of .time()
        try:
            payload = request.get_json()
            result = your_existing_agent_logic(payload)    # ← your code, UNCHANGED
            REQUEST_COUNT.labels(agent_name="planner", status="success").inc()
            return jsonify(result)
        except Exception as e:
            REQUEST_COUNT.labels(agent_name="planner", status="error").inc()
            MODEL_ERROR_COUNT.labels(
                agent_name="planner",
                error_type=type(e).__name__
            ).inc()
            # STANDARDISED error response format for all agents:
            return jsonify({"error": str(e), "agent": "planner", "status": "error"}), 500
```

---

## ✅ STEP 7 — Add `/metrics` Endpoint (Flask ONLY)

FastAPI users: **skip this** — Instrumentator already created it in Step 4.

```python
# Flask agents ONLY — add this route:
@app.route("/metrics")
def metrics():
    # generate_latest() converts all your Counters/Histograms into
    # the text format Prometheus expects when it scrapes /metrics
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
```

---



## 📄 Complete Minimal Working File (FastAPI — copy-paste template)

```python
# agent_server.py — paste this structure, fill in your logic

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram

# 1. Create app
app = FastAPI(title="Planner Agent", version="1.0.0")   # ← change name

# 2. Auto-wire Prometheus (creates /metrics, tracks all HTTP routes)
Instrumentator().instrument(app).expose(app)

# 3. Custom metrics
REQUEST_COUNT = Counter("agent_requests_total", "Total requests", ["agent_name", "status"])
INFERENCE_LATENCY = Histogram("agent_inference_latency_seconds", "Time per /run request")
MODEL_ERROR_COUNT = Counter("agent_model_errors_total", "LLM/solver errors", ["agent_name", "error_type"])

# 4. Health endpoint
@app.get("/health")
async def health():
    return {"status": "ok", "agent": "planner"}   # ← change name

# 5. Run endpoint (your logic goes inside)
@app.post("/run")
@INFERENCE_LATENCY.time()
async def run(payload: dict):
    try:
        result = your_actual_logic(payload)   # ← replace with your function
        REQUEST_COUNT.labels(agent_name="planner", status="success").inc()
        return result
    except Exception as e:
        REQUEST_COUNT.labels(agent_name="planner", status="error").inc()
        MODEL_ERROR_COUNT.labels(agent_name="planner", error_type=type(e).__name__).inc()
        raise

# 6. Entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)   # ← change port
```

---

## 🔍 Local Verification — Do This Before Handing Off

### Step A — Install the server tool (one-time, local only)

**FastAPI agents:**
```bash
# Uvicorn is needed to run FastAPI locally (not added to requirements.txt — local only)
pip install uvicorn
```

**Flask agents:**
```bash
# Flask has a built-in dev server — nothing extra needed
# (gunicorn for production is handled by the deployment team in Dockerfile)
```

---

### Step B — Start your agent

**FastAPI agents:**
```bash
# Recommended — run directly from command line:
uvicorn agent_server:app --host 0.0.0.0 --port 8001
#       ↑ your filename   ↑ your FastAPI app variable

# Replace 8001 with your agent's port: 

```

**Flask agents:**
```bash
# Just run directly — Flask's built-in server handles it:
python app.py
```

---

### Step C — Run the 4 verification tests

```bash
# Test 1 — Health check (must return {"status": "ok", "agent": "<your-name>"})
curl http://localhost:<your-port>/health

# Test 2 — Metrics endpoint (must return text starting with "# HELP")
curl http://localhost:<your-port>/metrics

# Test 3 — Call your /run endpoint once
curl -X POST http://localhost:<your-port>/run \
     -H "Content-Type: application/json" \
     -d '{"test": "data"}'

# Test 4 — Check metrics updated after the /run call
curl http://localhost:<your-port>/metrics | grep agent_requests_total
# Expected output:
# agent_requests_total{agent_name="planner",status="success"} 1.0
```

All 4 tests must pass before handoff to deployment team.

---



---

## 🚦 Final Checklist — Tick Before Handing Off

```
REQUIREMENTS.TXT
[ ] Added prometheus-fastapi-instrumentator>=6.1.0  (FastAPI only)
[ ] Added prometheus-client>=0.20.0

APP FILE
[ ] Added monitoring imports at top
[ ] Defined REQUEST_COUNT counter
[ ] Defined INFERENCE_LATENCY histogram
[ ] Defined MODEL_ERROR_COUNT counter
[ ] Added Instrumentator().instrument(app).expose(app)  (FastAPI only)
[ ] Added /health endpoint returning {"status": "ok", "agent": "<your-name>"}
[ ] Added /metrics route  (Flask only)
[ ] Wrapped /run with @INFERENCE_LATENCY.time() or with INFERENCE_LATENCY.time():
[ ] Added REQUEST_COUNT.labels(...).inc() inside /run for success + error cases
[ ] Added MODEL_ERROR_COUNT.labels(...).inc() in except block

TESTED LOCALLY
[ ] curl /health  → returns {"status": "ok", "agent": "<name>"}
[ ] curl /metrics → returns text starting with "# HELP"
[ ] curl /run     → returns your result
[ ] curl /metrics again → agent_requests_total shows 1.0
```
