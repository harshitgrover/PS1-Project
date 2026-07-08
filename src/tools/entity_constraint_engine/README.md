# Entity Constraint Engine

## Overview
The Entity Constraint Engine acts as the strict, isolated rules repository for individual architectural entities (rooms, spaces, features). Instead of hardcoding room rules, this engine reads from a unified SQLite database (`EntitySpecs` and `RelationalRules` tables) to dynamically generate the baseline requirements for any requested room. It operates in total isolation per entity to ensure rules don't bleed across different spatial types.

## Key Features
- **Granular Specs**: Queries and enforces min sizes, aspect ratios, and feature requirements (e.g., `requires_window`, `requires_egress`) per room type.
- **Relational Logic**: Extracts and maps adjacency, required connectivities, or distance limitations between different entities.
- **Version Tracked**: Every entity rule within the database is version-tracked to ensure backward compatibility.
- **Standalone Accessibility**: Can be queried by the Constraint Agent natively, or run as a totally independent microservice.

## Input & Output Formats
- **Input**: A JSON payload (or CLI argument) containing `entity_type` (e.g., `"bedroom"`) and a boolean `include_relations`.
- **Output**: A precise JSON dictionary returning the rules for that room. Main fields include:
  - `size_rules`: E.g., `min_area`, `aspect_ratio`.
  - `feature_rules`: E.g., `requires_window`, `requires_egress`, `requires_door`.
  - `relational_rules`: Adjacency matrices, required connectivities, or distance limits.
  - `area_rules`: Broad architectural ratios.

## Directory Structure
- `entity_constraint_engine.py`: Core logic for querying the database and formatting the room rules.
- `api.py`: FastAPI web server exposing the engine's query capabilities to network clients.
- `Entity_Constraints/`: Auto-generated output directory where raw JSON rulesets are saved when debugging individual rooms.

## Commands & API Integration
For all CLI testing scripts and API server instructions, please refer to [commands.md](commands.md).
