Updated codes of Constraint Agent, Verifier Agent, Entity Constraint Engine and DXF Generator acc to coding standards and all feedbacks implemented. Connected to Supabase, s3 bucket respectively. Environment variables need to be set while deploying.

Verifier agent has been scrapped so did not add that.
Accepts and returns in the new i/o format and follows the deployment checklist as well.

### `src/agents/constraints`
- **`api.py`**: FastAPI endpoints serving the constraint generation service.
- **`constraint_agent.py`**: Core logic for fetching, merging, and standardizing constraints.
- **`llm_parser.py`**: Uses Gemini LLM to parse unstructured text preferences into JSON.
- **`validator.py`**: Validates requested layout against legal zoning and building codes.
- **`test_constraint_agent.py`**: Unit tests verifying logic, overrides, and endpoints.
- **`commands.md`**: Guide for running, testing, and setting up the agent.
- **`schema.md`**: Documentation of the standardized JSON output schema.
- **`requirements.txt`**: Required Python dependencies.
- **`README.md`**: High-level overview of the constraint agent.

### `src/tools/entity_constraint_engine`
- **`api.py`**: FastAPI endpoints for querying entity-specific rules.
- **`entity_constraint_engine.py`**: Connects to Supabase to fetch room sizes and adjacencies.
- **`supabase_schema.sql`**: SQL migration definitions for the Supabase tables.
- **`supabase_seed.py`**: Python script to seed the database with baseline building codes.
- **`test_entity_constraint_engine.py`**: Unit tests for database queries and API behavior.
- **`commands.md`**: Guide for running the engine and seeding the database.
- **`schema.md`**: Documentation of the engine's rule output schema.
- **`requirements.txt`**: Required Python dependencies.
- **`README.md`**: High-level overview of the entity constraint engine.

### `src/tools/dxf_generator`
- **`api.py`**: FastAPI endpoints handling layout ingestion and automated S3 uploading.
- **`dxf_generator.py`**: Main orchestrator for parsing layouts and generating CAD/PNG files.
- **`parser.py`**: Transforms varying layout JSON formats into a standardized internal representation.
- **`core_engine.py`**: Object-oriented wrapper around ezdxf for drawing CAD primitives.
- **`dimensioning.py`**: Math utilities for calculating and drawing architectural dimension lines.
- **`renderer.py`**: Uses matplotlib to generate a 2D PNG preview of the floor plan.
- **`test_dxf_generator.py`**: Unit tests for parsing, drawing, and API generation limits.
- **`commands.md`**: Guide for running and testing the DXF generator.
- **`schema.md`**: Documentation of the DXF layer and object structures.
- **`requirements.txt`**: Required Python dependencies.
- **`README.md`**: High-level overview of the DXF generator.
- **`__main__.py` / `__init__.py`**: Python package entry points for CLI execution.
