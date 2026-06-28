# Verifier Agent

The Verifier Agent serves as the deterministic, stateless validation engine for the generative architectural pipeline. It acts as the mathematical "Discriminator" in a GAN-style system: it evaluates layouts proposed by upstream Generator Agents against a dynamic, centralized ruleset, returning a proven SAT (Satisfied) or UNSAT (Unsatisfied) result alongside precise diagnostic feedback.

## Key Features
- **Stateless Validation**: Uses a completely stateless API to evaluate geometric and constraint logic.
- **"No-Leak" Feedback**: Returns directional guidance and magnitude of error without leaking exact coordinate corrections to the Generator.
- **Adapter Pattern Integration**: Encapsulates external mathematical tools (like Z3) through a dynamic dispatcher and adapter client.

## Directory Structure
- `main.py`: FastAPI Transport Layer.
- `contracts.py`: Pydantic Models defining the public API boundary.
- `dispatcher.py`: Core routing and constraint logic processing.
- `z3_client.py`: Adapter for the external Z3 mathematical solver.
- `index.html`: Interactive web dashboard for testing payloads dynamically.
- `demo_inputs/`: JSON payloads for testing dynamic exterior and interior rules.

For commands to run and test this agent, see [commands.md](commands.md).
