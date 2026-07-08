# Setup & Initialization

If you ever need to completely wipe and reset the ruleset database in Supabase, run this command from the root `PS1 Project` folder:

```bash
python3 src/supabase_seed.py
```

---

# Demo JSON Files

These are mock outputs from the Location Zoning Agent that can be used for testing:

1. `json_files/zoning_3ded7e729f3d.json` 
   *(Redmond OBAT zone, Mixed Use, 80% max impervious)*

2. `json_files/zoning_403aa1801269.json` 
   *(Bellevue MDR-1 zone, Residential, 40% max coverage)*

---

# How to Generate a Final Ruleset

Pass a zoning JSON file into the Constraint Agent. It will merge the zoning overrides with the interior building codes and output the final Ruleset JSON to stdout.

```bash
cd src/agents/constraints
python3 constraint_agent.py json_files/zoning_3ded7e729f3d.json
```

---

# LLM Parsing & User Constraints

If you want the Constraint Agent to parse natural language layout instructions (e.g. *"I want 3 bedrooms of 100sq ft"*), you can create a `user_constraints.txt` file in the `src` folder.

```bash
cd src/agents/constraints

# Export your API key first!
export GEMINI_API_KEY="<YOUR_API_KEY>"

# Running the constraint agent will now automatically trigger the LLM to parse the text file
python3 constraint_agent.py json_files/zoning_3ded7e729f3d.json
```

---



# API Usage

Run the dedicated FastAPI server (defaults to port 8002):

```bash
python3 -m src.agents.constraints.api
```

### Endpoints
- **`GET /health`**: Health check.
- **`POST /api/v1/constraints`**: Send an asynchronous generation request.

**Example cURL:**
```bash
curl -X POST "http://localhost:8002/api/v1/constraints" \
     -H "Content-Type: application/json" \
     -d '{"session_id": "test_001", "callback_url": "http://localhost:8002/webhook", "zoning_data": {"jurisdiction": "Redmond, WA", "zone_code": "OBAT", "max_height_ft": 150}, "user_constraints": "I want a very large kitchen and exactly 4 bedrooms."}'
```
*The API will immediately return `{"status": "started"}` and later send the final `result` containing the ruleset to your provided `callback_url`.*
