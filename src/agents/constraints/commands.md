# Setup & Initialization

If you ever need to completely wipe and reset the ruleset database, run these commands starting from the `PS1 Project` folder:

```bash
cd src
python3 db.py
python3 demodb.py
```

---

# Demo Hashkeys

These are mock outputs from the Location Zoning Agent that have been seeded into the database for testing:

1. `zoning_3ded7e729f3d` 
   *(Redmond OBAT zone, Mixed Use, 80% max impervious)*

2. `zoning_403aa1801269` 
   *(Bellevue MDR-1 zone, Residential, 40% max coverage)*

---

# How to Generate a Final Ruleset

Pass one of the zoning hashkeys into the Constraint Agent. It will merge the zoning overrides with the interior building codes and output a unique final Ruleset ID.

```bash
cd src
python3 constraint_agent.py zoning_3ded7e729f3d
```

---

# LLM Parsing & User Constraints

If you want the Constraint Agent to parse natural language layout instructions (e.g. *"I want 3 bedrooms of 100sq ft"*), you can create a `user_constraints.txt` file in the `src` folder.

```bash
cd src

# Export your API key first!
export GEMINI_API_KEY="<YOUR_API_KEY>"

# Running the constraint agent will now automatically trigger the LLM to parse the text file
python3 constraint_agent.py zoning_3ded7e729f3d
```

---

# How to Extract/View a JSON Payload

Use the extractor script to grab ANY JSON from the database using its ID. It will automatically generate a `.json` file inside the `src/json_files` folder.

```bash
cd src
python3 extract_file.py zoning_3ded7e729f3d
```
*(This will generate `src/json_files/zoning_3ded7e729f3d.json`)*

---

# How to run the Entity Constraint Engine Independently

To see the pure architectural baseline rules for a specific room type *before* it gets merged into a final ruleset, run the Engine directly with a room name. You can pass multiple rooms, or use `all` to see the complete internal architectural dictionary. The output will automatically be saved into the `src/Entity_Constraints` folder.

*(Currently available entities: `bedroom`, `bathroom`, `kitchen`, `living`, `dining`, `corridor`, `laundry`, `garage`, `balcony`)*

**For a specific room:**
```bash
cd src
python3 entity_constraint_engine.py bedroom
```
*(Generates `src/Entity_Constraints/bedroom.json`)*

**For multiple specific rooms:**
```bash
cd src
python3 entity_constraint_engine.py bedroom bathroom kitchen
```
*(Generates `src/Entity_Constraints/bedroom_bathroom_kitchen.json`)*

**For all rooms at once:**
```bash
cd src
python3 entity_constraint_engine.py all
```
*(Generates `src/Entity_Constraints/all_entities.json`)*
