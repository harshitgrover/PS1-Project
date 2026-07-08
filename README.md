# Agentic CAD / AI-Driven House Design Pipeline

This repository contains the backend systems for the Agentic CAD project. It is structured into multiple independent agents and specialized tools that handle constraints, verification, and output generation in a GAN-style pipeline.

## System Architecture

The project consists of several core components located in the `src` directory:

### Core Tools & Agents
- **[Constraint Agent](src/agents/constraints/README.md)**: A deterministic, rule-based agent service that delegates to the Engine to structure raw architectural constraints into JSON-parsable rulesets. It supports **3-tier constraint severities (legal, hard, soft)** and incorporates natural language rules via LLM parsing.
- **[Entity Constraint Engine](src/tools/entity_constraint_engine/README.md)**: A standalone rule-management backend for architectural entities, serving rules via a synchronous FastAPI.
- **[DXF Generator](src/tools/dxf_generator/README.md)**: An open-ended conversion engine that parses universal JSON layouts (floor plans, site plans, side views) into richly formatted and dimensioned AutoCAD `.dxf` files along with visual previews. It features a **Universal Fallback** algorithm that can mathematically extract and render coordinates from virtually any unrecognized JSON structure.
- **[Verifier Agent](src/agents/verifier/README.md)**: A stateless validation engine that evaluates proposed layouts against the rulesets. It returns specific constraint violations without leaking coordinate fixes.

### External Integrations
- **[z3_verifier_tool](src/tools/z3_verifier/README.md)**: The underlying mathematical solver wrapper utilized by the Verifier Agent to perform rigid constraint mathematics (imported integration).

## Getting Started

Each agent and tool operates as an independent service and has its own configuration and command structure. Please refer to the specific documentation and `commands.md` within each component's directory for API and CLI usage instructions.
