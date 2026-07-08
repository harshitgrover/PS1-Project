# Constraint Agent

## Overview
The Constraint Agent serves as the "Master Rules Aggregator" for the generative pipeline. It receives zoning payloads from the external Location Zoning Agent, queries its internal database to extract specific environmental overrides, and dynamically delegates to the Entity Constraint Engine to build a complete rulebook for interior rooms. It outputs a rigid JSON structure that acts as the single source of truth for downstream Floor Plan Generators and Verifier Agents.

## Key Features
- **Zone Overrides**: Automatically detects and applies municipal codes (e.g. `max_far`, setbacks) based on the target jurisdiction.
- **Direct JSON Communication**: Outputs direct JSON schema payloads as the single source of truth for downstream Floor Plan Generators and Verifier Agents.
- **LLM User Parsing**: Utilizes an integrated Gemini LLM Parser (`llm_parser.py`) to convert conversational layout requests (e.g., "I want 3 bedrooms of 100sq ft") into strict JSON requirements.
- **Dynamic Extensibility**: Entirely database-driven; adding new room types or municipal safety codes requires zero code changes.

## Input & Output Formats
- **Input**: Expects a JSON payload containing `session_id`, `callback_url`, `zoning_data`, and optionally `user_constraints` (a string of natural language requests). The `zoning_data` is the upstream zoning JSON that contains main fields like: `jurisdiction`, `zone`, `offsets`, `max_coverage`, and `tree_preservation`.
- **Local Input**: Optionally reads from a `user_constraints.txt` file (if present in the directory and no string was passed via API) to ingest natural language overrides via the Gemini LLM.
- **Output**: Asynchronously sends a massive, aggregated JSON ruleset to the `callback_url`. The output schema (`final_schema`) is strictly divided into two main blocks:
  - `exterior`: Contains `setbacks`, `max_height`, `lot_coverage`, etc.
  - `interior`: Contains dictionaries for each room, listing `size_rules`, `feature_rules`, and `relational_rules`.

## Directory Structure
- `constraint_agent.py`: The core aggregator and logic pipeline.
- `api.py`: FastAPI server exposing the agent over HTTP.
- `llm_parser.py`: Natural language processing logic using Google Gemini.
- `extract_file.py`: Utility script to quickly extract generated JSON payloads from the database into the `json_files` folder.
- `db.py` & `demodb.py`: Database initialization and seeding scripts.
- `database.db`: The unified local SQLite database holding all rules and agent outputs.

## Commands & API Integration
For all CLI execution scripts, database initialization commands, and API server instructions, please refer to [commands.md](commands.md).
