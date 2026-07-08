# DXF Generator

## Overview
The DXF Generator is a deterministic rendering tool designed to take raw, verified JSON coordinates from upstream generator agents and perfectly convert them into an industry-standard AutoCAD `.dxf` file. By enforcing strict programmatic drafting at this final stage, the pipeline ensures zero LLM hallucinations or geometric drift can occur during the final export.

## Key Features
- **Universal IR Parser**: Natively understands an explicit JSON contract defining views, layers, and entities, while intelligently falling back to legacy formats.
- **Multi-View Support**: Capable of processing floor plans, site plans, side elevations, and multi-floor layouts seamlessly in a single pipeline.
- **Auto-Dimensioning**: Smartly calculates offsets and automatically places standard linear and aligned dimensions to all exterior and interior bounds.
- **Preview Renderer**: Can simultaneously generate a high-quality `matplotlib`-based 2D `.png` preview alongside the `.dxf` output for rapid visual validation.

## Input & Output Formats
- **Input**: A JSON payload conforming to the Universal IR Contract (or legacy layouts like `floor_plan.json`). Main fields include:
  - `views`: An array of drawings (e.g., floor plan, site plan).
  - `layers`: Array defining `name` and AutoCAD `color` codes.
  - `entities`: Array of geometric objects detailing `type` (`polygon`, `label`), `points` (coordinate arrays), and optional `auto_dimension` flags.
- **Output**: A deterministically drafted AutoCAD `.dxf` binary file. If the render flag is active, it also outputs a 2D `matplotlib` preview as a `.png` file.

## Directory Structure
- `dxf_generator.py`: The CLI orchestrator tying the sub-modules together.
- `api.py`: FastAPI web server for synchronous generation over HTTP.
- `parser.py`: The data adapter that normalizes incoming JSON into an Intermediate Representation.
- `core_engine.py`: The drafting engine wrapping `ezdxf` to place polygons, layers, and text.
- `dimensioning.py`: The mathematical engine for placing non-overlapping dimension lines.
- `renderer.py`: The graphical preview generator.

## Commands & API Integration
For CLI usage, visualization flags, and API server instructions, please refer to [commands.md](commands.md).
