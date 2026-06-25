# System Architecture
## AI-Assisted Residential House Design System

**Version:** 1.0 (Draft)
**Author:** Anirudh
**Status:** For Team Review

---

## 1. Vision and Objective

This system is an AI-driven pipeline that accepts homeowner requirements and produces a **city-submittable residential permit package** — equivalent to the professional architectural submissions used by city planning departments.

The output is not a floor plan. It is a complete permit package.

---

## 2. System Pipeline (High Level)

```
┌────────────────────────────────────────────────────────────────┐
│                         USER INPUT                             │
│         Budget · Requirements · Preferences · Examples         │
└──────────────────────────────┬─────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      PLANNING LAYER                              │
│     Planning Agent · Location Agent · Constraint Engine          │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     GENERATION LAYER                             │
│  Generator Agent · Similarity Layout Agent · Livability Agent    │
│  Site Plan · Floor Plans · Elevation · Roof · Mechanical         │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                    VERIFICATION LAYER                            │
│             Verifier Agent · Z3 Verifier · Reviewer Agent        │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                 HUMAN-IN-THE-LOOP (HITL)                         │
│          Client Approval · Architect Sign-off                     │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                    OUTPUT / REPORT LAYER                         │
│          Report Generation · PDF · DXF · JSON                    │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                    CITY SUBMISSION                                │
│              City Reviewer (HITL) · Final Approval               │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Layer-by-Layer Breakdown

### 3.1 User Interface Layer

**Components:** UI (Web Application)

**Responsibilities:**
- Collect user requirements: budget, bedroom count, lot info, preferences, example images
- Show design previews
- Support HITL approval steps
- Receive notifications

**Inputs:**
- Natural language requirements
- CAD/DXF files (from surveyors)
- Example images / reference designs

---

### 3.2 Security Layer

**Components:** Authentication, Authorization, Guardrails

**Responsibilities:**
- Verify user identity (Authentication)
- Control access by role: client, architect, reviewer (Authorization)
- Prevent invalid requests, unsafe designs, or policy violations (Guardrails)

---

### 3.3 Planning Layer

#### 3.3.1 Planning Agent

**Purpose:** Requirement gathering and high-level planning.

**Inputs:** Raw user requirements
**Outputs:** Room requirements, design constraints, layout options

**Example flow:**
```
Input:  "I need a 4-bedroom house on a 6000 sqft lot with a budget of $500K"
Output: {
  rooms: [master_bedroom, 3x_bedroom, living, kitchen, 2x_bathroom],
  approx_sqft: 2200,
  floors: 2,
  initial_constraints: [...]
}
```

#### 3.3.2 Location Agent

**Purpose:** Apply jurisdiction-specific rules.

**Knowledge base includes:**
- City-specific building codes (Seattle, Bellevue, Redmond, etc.)
- Setback requirements
- Square footage calculation rules
- Environmental and fire regulations

**Outputs:** Location-specific constraint set appended to the Constraint Engine.

#### 3.3.3 Constraint Engine

> "Planning determines what *should* be built. The Constraint Engine determines what is *legally and physically possible*."
> — Project Mentor

**Constraint types:**

| Category | Examples |
|----------|---------|
| Spatial | Room size limits, adjacency requirements, bathroom placement |
| Legal | Setback requirements, fire regulations, environmental rules |
| Structural | Wall alignment, load-bearing constraints, multi-floor stacking |
| Regional | Square footage calculation rules, carport/patio counting |

Every major entity (room, wall, floor, roof) must have associated constraints.

---

### 3.4 Generation Layer

#### 3.4.1 Generator Agent

**Generates:**
- Exterior layout (site plan, property boundaries)
- Interior layout (floor-by-floor room placement)
- Multi-floor designs
- Elevation designs (front, rear, sides)
- Roof geometry

**Key challenge:** Multi-floor design — changing one floor affects all others. Requires iterative optimization.

#### 3.4.2 Similarity Layout Agent

**Use cases:**
- "I like this house. Generate something similar."
- "Match the style of my previous 50 houses." (builder use case)

**Functions:**
- Similarity retrieval from design repository
- Builder style learning
- Historical design matching

**Depends on:** RAG system, Design Database

#### 3.4.3 Livability Agent

**Optimizes:**
- Natural daylight (window placement, orientation)
- Airflow and ventilation
- Living comfort metrics

#### 3.4.4 Site Plan Generator

**Generates:**
- Property boundary representation
- Existing structures
- Water and sewer line placements
- Tree locations (existing, protected, to-be-removed)
- Setback zone visualization

---

### 3.5 Verification Layer

#### 3.5.1 Verifier Agent

**Checks:**
- Constraint compliance
- Design consistency
- Building regulation adherence

#### 3.5.2 Z3 Verifier

**Role:** Formal mathematical verification of constraints.

**Responsibilities:**
- Formally prove or disprove constraint satisfaction
- Guarantee correctness of constraint validation
- Flag violations with specificity (which wall, which setback, which rule)

#### 3.5.3 Reviewer Agent

**Purpose:** Simulate how a city reviewer evaluates plans.

**Reviews:**
- Every wall
- Every setback
- All fire and safety requirements
- Environmental compliance
- Permit-level checklist items

---

### 3.6 Human-in-the-Loop (HITL) Layer

Three human actors participate at distinct stages:

| Actor | Stage | Responsibility |
|-------|-------|----------------|
| Client | Post-design-generation | Approve or request changes to the design |
| Architect | Post-client-approval | Professional review and sign-off |
| City Reviewer | Post-submission | Final permit approval |

**Important:** City submission cannot be fully automated. Human sign-off is mandatory at each gate.

---

### 3.7 Output / Report Layer

#### 3.7.1 Report Generation

**Generates:**
- Permit submission report
- Phase-wise progress reports
- Reviewer-facing compliance summaries

#### 3.7.2 PDF Generation

Converts generated designs and reports into shareable, submission-ready PDF documents.

#### 3.7.3 DXF Generation

Produces architectural drawings in CAD-compatible DXF format for city submission.

#### 3.7.4 JSON Extractor

Converts all internal design representations into structured JSON for storage and inter-agent communication.

---

### 3.8 Supporting Infrastructure

#### 3.8.1 LLM

Core language model powering the planning, generation, and review agents.

#### 3.8.2 RAG (Retrieval-Augmented Generation)

```
Design Repository → Retrieval → LLM → Constraint Validation
```

Used for: similar house retrieval, builder style retrieval, historical design lookup.

#### 3.8.3 Training Layer

**Training data sources (public):**
- Public house design databases
- Builder websites
- Public floor plan repositories
- Public layout archives

*Note: Full permit reports are confidential and are NOT used for training.*

#### 3.8.4 Database

**Stores:**
- Project designs
- Constraint sets
- Reports
- User profiles and preferences

#### 3.8.5 Memory

| Type | Scope | Contents |
|------|-------|---------|
| Short-term | Current session | Active design context, conversation state |
| Long-term | Persistent | User preferences, historical projects |

#### 3.8.6 Caching / Performance

Used for faster retrieval of frequently accessed designs, constraints, and RAG results.

#### 3.8.7 Notification Service

Notifies stakeholders on key events:
- Review requested
- Approval complete
- Report generated

#### 3.8.8 Agent Manager

Coordinates all agents. Determines execution order, manages dependencies between agents, sequences the full workflow.

#### 3.8.9 Cost Estimation

Estimates construction cost, material cost, and provides design alternative comparisons (Option A vs Option B).

#### 3.8.10 CAD/DXF File Reader

Ingests CAD/DXF files provided by surveyors as input to the pipeline. Surveyors often provide DXF files as the starting point.

#### 3.8.11 Billing

Handles user billing and usage metering.

---

## 4. Permit Package — Output Components

A complete city permit package produced by this system must include:

| Document | Contents |
|----------|---------|
| Approval Sheet | Compliance statements, review notes |
| Lot Survey | Property dimensions, angles, boundaries, elevations |
| Site Plan | House placement, walkways, patios, setbacks |
| Tree Documentation | Existing, removed, and protected trees |
| Floor Plans | All rooms, staircases, closets, pantries (per floor) |
| Mechanical Room Plan | HVAC, heating, water heater placement |
| Crawl Space Documentation | Access paths for plumbing and electrical |
| Elevation Plans | Front, rear, left side, right side |
| Roof Design | Geometry, pitch (e.g., 12:4), slopes |
| Square Footage Calculations | Location-specific; with exclusion rules |

---

## 5. Technical Complexity Areas

### 5.1 Multi-floor Design
Iterative optimization required. Constraints: wall alignment, structural consistency, bathroom stacking, staircase placement.

### 5.2 Height Elevation Design
Must handle sloped terrain, uneven lots, cliff-like lots, garages below main floor, and basement configurations.

### 5.3 Double-Height Areas
Living room spanning two floors requires special handling in area calculations, floor planning, and 3D modeling.

### 5.4 3D Modeling
Required to properly handle floor interactions, roof geometry, and double-height spaces. 2D plans alone are insufficient.

### 5.5 Square Footage Calculation Engine
Location-specific rules. Exclusions commonly include: staircases, double-height voids, patios, carports.

---

## 6. Interfaces Between Components

```
User Input
  ↓
UI → Planning Agent → Location Agent
                   → Constraint Engine
                   ↓
             Agent Manager
                   ↓
            Generator Agent ←→ Similarity Layout Agent ←→ RAG
            Generator Agent ←→ Livability Agent
                   ↓
             Verifier Agent → Z3 Verifier
                   ↓
             Reviewer Agent
                   ↓
              HITL Gates (Client → Architect → City)
                   ↓
             Report Generation → PDF / DXF / JSON
                   ↓
             City Submission
```

---

## 7. Components Not Yet Designed (Open Items)

- 3D Modeling engine (architecture TBD)
- Square footage calculation engine (rules per jurisdiction)
- Crawl space modeling details
- Mechanical planning (HVAC room generation)
- Window placement logic (Livability Agent input)
- Roof modeling (pitch engine, geometry generator)
- Multi-floor optimization algorithm (iterative or solver-based)

---

*This document is a living reference. All team members should flag gaps or corrections to Anirudh for incorporation.*
