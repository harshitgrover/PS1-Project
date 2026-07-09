# Constraint Agent — Commands & Testing Guide

---

## 1. Setup & Initialization

Seed/reset the rules database in Supabase (run once from project root):

```bash
source venv/bin/activate
python3 src/supabase_seed.py
```

---

## 2. Run the API Server

Start the Entity Constraint Engine (Dependency) on port 8001, and the Constraint Agent FastAPI server on port 8002. It's recommended to run these in separate terminal windows.

**Window 1: Entity Constraint Engine**
```bash
# From project root
source venv/bin/activate
# Optional: lsof -ti:8001 | xargs kill -9
python3 -m src.tools.entity_constraint_engine.api
```

**Window 2: Constraint Agent**
```bash
# From project root
source venv/bin/activate
# Optional: lsof -ti:8002 | xargs kill -9
python3 -m src.agents.constraints.api
```

---

## 3. Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `GET`  | `/health` | Health check — confirms server is alive |
| `GET`  | `/metrics` | Prometheus metrics (auto-exposed) |
| `POST` | `/run` | Main endpoint — generates constraint schema |
| `POST` | `/api/v1/constraints` | Alias for `/run` |

---

## 4. Manual Testing (cURL)

**Step 1 — Start the servers (in separate terminal windows):**

**Window 1 (Entity Constraint Engine):**
```bash
source venv/bin/activate

# Optional: if port 8001 is already in use, kill the existing process first:
# lsof -ti:8001 | xargs kill -9

python3 -m src.tools.entity_constraint_engine.api
```

**Window 2 (Constraint Agent):**
```bash
source venv/bin/activate

# Optional: if port 8002 is already in use, kill the existing process first:
# lsof -ti:8002 | xargs kill -9

python3 -m src.agents.constraints.api
```

**Step 2 — Health check:**
```bash
curl http://localhost:8002/health
# Expected: {"status": "ok", "agent": "constraint_agent"}
```

**Step 3 — Check metrics:**
```bash
curl http://localhost:8002/metrics | grep agent_requests_total
# Expected: lines starting with "# HELP agent_requests_total"
```

**Step 4 — Call /run with a standard Agent Manager payload and save to JSON:**
```bash
curl -s -X POST "http://localhost:8002/run" \
     -H "Content-Type: application/json" \
     -d @src/agents/constraints/demo_inputs/demo_input_1.json \
     | python3 -m json.tool > src/agents/constraints/demo_outputs/ruleset_redmond_obat.json
```
*(The `-s` flag silences curl's progress bar. `python3 -m json.tool` pretty-prints the JSON before saving.)*

**Step 5 — Verify metrics updated:**
```bash
curl http://localhost:8002/metrics | grep agent_requests_total
# Expected: agent_requests_total{agent_name="constraint_agent",status="success"} 1.0
```

---

## 5. Automated Unit Tests (Test Script)

Run from the **project root** using the virtual environment:

```bash
# Run tests in the module folder (recommended)
source venv/bin/activate
python -m unittest src/agents/constraints/test_constraint_agent.py -v
```

**What each test checks:**
- `test_health_check_returns_ok` — `/health` returns 200 with correct body
- `test_run_endpoint_exists` — `/run` route is registered (returns 422, not 404, on bad input)
- `test_initialization_with_custom_url` — ConstraintAgent stores the provided ECE URL
- `test_initialization_default_url_from_env` — Falls back to `ECE_URL` env var
- `test_default_descriptions_contains_required_keys` — All standard setback keys exist
- `test_legal_keys_set_contains_setbacks` — LEGAL_KEYS has the standard setback fields
- `test_process_zoning_input_returns_dict_with_required_keys` — Output schema has all required blocks
- `test_process_zoning_input_applies_setback_overrides` — Setbacks from zoning data land in `exterior`

---

## 6. Demo JSON Files

Mock inputs pre-formatted into the centralized Agent Manager structure. These single files contain both the upstream Location Zoning output and the user constraints:

- `demo_inputs/demo_input_1.json` — Redmond OBAT zone (Mixed Use, 80% max impervious) + Vastu Rules
- `demo_inputs/demo_input_2.json` — Bellevue MDR-1 zone (Residential, 40% max coverage) + Vastu Rules

**Run the agent directly against a demo file (CLI mode):**
```bash
python3 -m src.agents.constraints.constraint_agent src/agents/constraints/demo_inputs/demo_input_1.json > src/agents/constraints/demo_outputs/ruleset_vastu.json
```

---

## 7. LLM Parsing & User Constraints

To parse natural language layout instructions, include the text in the `user_constraints` property of the `Properties` object in your input JSON payload. 

```bash
export GEMINI_API_KEY="<YOUR_API_KEY>"
```

The LLM parser is triggered automatically when `user_constraints` is found inside the payload (either directly in `Properties.user_constraints` or inherited from `Properties.planner_output.user_constraints`).
