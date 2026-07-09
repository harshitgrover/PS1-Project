# Constraint Agent

## Overview
The Constraint Agent serves as the "Master Rules Aggregator" for the generative pipeline. It receives zoning payloads from the external Location Zoning Agent, queries its internal database to extract specific environmental overrides, and dynamically delegates to the Entity Constraint Engine to build a complete rulebook for interior rooms. It outputs a rigid JSON structure that acts as the single source of truth for downstream Floor Plan Generators and Verifier Agents.

## Key Features
- **Zone Overrides**: Automatically detects and applies municipal codes (e.g. `max_far`, setbacks) based on the target jurisdiction.
- **Direct JSON Communication**: Outputs direct JSON schema payloads as the single source of truth for downstream Floor Plan Generators and Verifier Agents.
- **LLM User Parsing**: Utilizes an integrated Gemini LLM Parser (`llm_parser.py`) to convert conversational layout requests (e.g., "I want 3 bedrooms of 100sq ft") into strict JSON requirements.
- **Dynamic Extensibility**: Entirely database-driven; adding new room types or municipal safety codes requires zero code changes.

## Input & Output Formats
- **Input**: Expects a JSON payload containing `session_id`, `Properties`, and optionally `file_refs`. The `Properties` must contain `location_zoning_output` (the upstream zoning JSON containing fields like `jurisdiction`, `zone`, `offsets`, etc.), and optionally `user_constraints` (a string of natural language requests).
- **Local Input**: Optionally reads from a `user_constraints.txt` file (if present in the directory and no string was passed via API) to ingest natural language overrides via the Gemini LLM.
- **Output**: Synchronously returns a massive, aggregated JSON ruleset in its response body. The output schema (`final_schema`) is strictly divided into two main blocks:
  - `exterior`: Contains `setbacks`, `max_height`, `lot_coverage`, etc.
  - `interior`: Contains dictionaries for each room, listing `size_rules`, `feature_rules`, and `relational_rules`.

## Directory Structure
- `constraint_agent.py`: Core aggregator and logic pipeline.
- `api.py`: FastAPI server exposing the agent over HTTP (port 8002). Includes `/health`, `/run`, `/metrics`.
- `llm_parser.py`: Natural language processing logic using Google Gemini.
- `validator.py`: Pre-flight constraint validation logic.
- `test_constraint_agent.py`: Unit tests for this module (run with `python -m unittest`).
- `demo_inputs/`: Demo zoning JSON payloads for manual testing.
- `user_constraints.txt`: Optional file for natural language overrides (read automatically if present).

## Testing & Commands
For CLI usage, unit test commands, manual cURL tests, and API server instructions, please refer to [commands.md](commands.md).
