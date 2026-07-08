# Entity Constraint Engine — Commands & Testing Guide

---

## 1. Run the API Server

Start the FastAPI server (defaults to port 8001):

```bash
# From project root
source venv/bin/activate
python3 -m src.tools.entity_constraint_engine.api
```

---

## 2. Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `GET`  | `/health` | Health check — confirms server is alive |
| `GET`  | `/metrics` | Prometheus metrics (auto-exposed) |
| `POST` | `/run` | Main endpoint — fetch rules for a list of entities |
| `POST` | `/api/v1/entity_constraints` | Alias for `/run` |

---

## 3. Manual Testing (cURL)

**Step 1 — Start the server:**
```bash
source venv/bin/activate
python3 -m src.tools.entity_constraint_engine.api
```

**Step 2 — Health check:**
```bash
curl http://localhost:8001/health
# Expected: {"status": "ok", "agent": "entity_engine"}
```

**Step 3 — Check metrics:**
```bash
curl http://localhost:8001/metrics
# Expected: text starting with "# HELP"
```

**Step 4 — Fetch rules for a single entity:**
```bash
curl -X POST "http://localhost:8001/run" \
     -H "Content-Type: application/json" \
     -d '{"entities": ["bedroom"], "include_relations": true}'
```

**Step 4b — Save single entity output to `Entity_Constraints/`:**
```bash
curl -s -X POST "http://localhost:8001/run" \
     -H "Content-Type: application/json" \
     -d '{"entities": ["bedroom"], "include_relations": true}' \
     | python3 -m json.tool > src/tools/entity_constraint_engine/Entity_Constraints/bedroom.json
```

**Step 5 — Fetch rules for multiple entities (as the Constraint Agent does):**
```bash
curl -X POST "http://localhost:8001/api/v1/entity_constraints" \
     -H "Content-Type: application/json" \
     -d '{"entities": ["bedroom", "bathroom", "kitchen", "living", "corridor"], "include_relations": true}'
```

**Step 5b — Save all entities output to `Entity_Constraints/`:**
```bash
curl -s -X POST "http://localhost:8001/api/v1/entity_constraints" \
     -H "Content-Type: application/json" \
     -d '{"entities": ["bedroom", "bathroom", "kitchen", "living", "dining", "corridor", "laundry", "garage", "balcony"], "include_relations": true}' \
     | python3 -m json.tool > src/tools/entity_constraint_engine/Entity_Constraints/all_entities.json
```
*(The `-s` flag silences curl's progress bar. `python3 -m json.tool` pretty-prints the JSON before saving.)*

**Step 6 — Verify metrics updated after the call:**
```bash
curl http://localhost:8001/metrics | grep agent_requests_total
# Expected: agent_requests_total{agent_name="entity_engine",status="success"} 1.0
```

---

## 4. Automated Unit Tests (Test Script)

Run from the **project root** using the virtual environment:

```bash
source venv/bin/activate
python -m unittest src/tools/entity_constraint_engine/test_entity_constraint_engine.py -v
```

**What each test checks:**
- `test_health_check_returns_ok` — `/health` returns 200 with correct body
- `test_run_endpoint_exists` — `/run` route is registered (not 404)
- `test_initialization_without_credentials` — Engine starts without crashing even if Supabase creds are missing
- `test_get_entity_rules_returns_no_data_when_supabase_not_initialized` — Returns `{"status": "no_data"}` gracefully
- `test_get_entities_rules_returns_empty_dict_for_no_data` — Returns `{}` for all entities when no DB
- `test_get_entity_rules_response_structure` — Full response has `version`, `size_rules`, `feature_rules`, `relational_rules`, `area_rules`
- `test_get_entities_rules_filters_cross_entity_relations` — Drops relations pointing to entities not in the request

---

## 5. Run Standalone (CLI mode)

Inspect raw rules for any entity type directly. Output is saved to `Entity_Constraints/` folder.

*(Available entities: `bedroom`, `bathroom`, `kitchen`, `living`, `dining`, `corridor`, `laundry`, `garage`, `balcony`)*

**For a specific room:**
```bash
cd src/tools/entity_constraint_engine
python3 entity_constraint_engine.py bedroom
# Generates: Entity_Constraints/bedroom.json
```

**For multiple rooms:**
```bash
python3 entity_constraint_engine.py bedroom bathroom kitchen
# Generates: Entity_Constraints/bedroom_bathroom_kitchen.json
```

**For all rooms:**
```bash
python3 entity_constraint_engine.py all
# Generates: Entity_Constraints/all_entities.json
```
