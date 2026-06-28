# Agentic CAD / AI-Driven House Design Pipeline

This repository contains the backend systems for the Agentic CAD project. It is structured into multiple independent agents that handle constraints and verification in a GAN-style pipeline.

## System Architecture

The project consists of several core components located in the `src` directory:

- **Constraint_Agent+Engine**: A deterministic, rule-based service that structures raw architectural constraints into JSON-parsable rulesets.
- **Verifier-Agent**: A stateless validation engine that evaluates proposed layouts against the rulesets using the Z3 mathematical solver. It returns specific constraint violations without leaking coordinate fixes.
- **z3_verifier_tool**: The underlying mathematical solver wrapper utilized by the Verifier Agent.

## Getting Started

Each agent operates as an independent service and has its own configuration and command structure. Please refer to the specific documentation within each agent's directory:
- [Verifier Agent Documentation](src/Verifier-Agent/README.md)
- [Constraint Agent Documentation](src/Constraint_Agent+Engine/README.md)
