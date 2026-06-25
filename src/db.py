import sqlite3
import json
import os

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

def init_db(db_path=DEFAULT_DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Table for Jurisdiction exterior rules
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Jurisdictions (
            name TEXT PRIMARY KEY,
            schema_version TEXT,
            source TEXT,
            status TEXT,
            tolerance_ft REAL,
            front_setback_ft REAL,
            rear_setback_ft REAL,
            side_setback_ft REAL,
            min_house_width_ft REAL,
            min_house_depth_ft REAL,
            door_corner_margin_ft REAL,
            max_lot_coverage_fraction REAL,
            min_area_fraction_of_max REAL,
            tree_protection_zone_json TEXT
        )
    ''')

    # Table for interior entity specifications
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS EntitySpecs (
            entity_type TEXT PRIMARY KEY,
            version TEXT,
            min_area_ft2 REAL,
            min_side_ft REAL,
            max_side_ft REAL,
            habitable BOOLEAN,
            min_aspect_ratio REAL,
            max_aspect_ratio REAL,
            requires_exterior_window BOOLEAN,
            requires_egress BOOLEAN,
            ventilation_type TEXT,
            requires_door BOOLEAN,
            requires_closet BOOLEAN
        )
    ''')

    # Table for relational rules between entities
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS RelationalRules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_a TEXT,
            entity_b TEXT,
            relation TEXT,
            min_shared_wall_ft REAL,
            max_dist_ft REAL,
            version TEXT,
            description TEXT
        )
    ''')

    # Table for specific area rules
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS AreaRules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule TEXT,
            description TEXT
        )
    ''')

    # Table for all Agent JSON outputs (Zoning, Constraint, etc.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS AgentOutputs (
            id TEXT PRIMARY KEY,
            data_json TEXT
        )
    ''')

    # Table for zone-specific overrides
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ZoneSpecificRules (
            jurisdiction TEXT,
            zone TEXT,
            rule_key TEXT,
            rule_value TEXT,
            description TEXT,
            PRIMARY KEY (jurisdiction, zone, rule_key)
        )
    ''')

    conn.commit()
    conn.close()

def seed_data(db_path=DEFAULT_DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Jurisdictions
    # Bellevue, Redmond, Kirkland, Seattle Downtown NR, Bothell
    # Offsets, lot coverage, and tree protection are set to None here 
    # to guarantee they are ONLY sourced authentically from the Zoning Agent input.
    jurisdictions = [
        # name, schema_version, source, status, tolerance_ft, front_sb, rear_sb, side_sb, min_w, min_d, door_margin, max_cov, min_area, tree_zone
        ("Seattle Downtown NR", "1.0", "IRC R304/R305", "loaded", 1e-6, None, None, None, 20.0, 20.0, 2.0, None, 0.90, None),
        ("Redmond, WA", "1.0", "IRC R304/R305", "loaded", 1e-6, None, None, None, 25.0, 25.0, 2.5, None, 0.85, None),
        ("Bellevue, WA", "1.0", "IRC R304/R305", "loaded", 1e-6, None, None, None, 20.0, 20.0, 2.0, None, 0.85, None),
        ("Kirkland, WA", "1.0", "IRC R304/R305", "loaded", 1e-6, None, None, None, 20.0, 20.0, 2.0, None, 0.90, None),
        ("Bothell, WA", "1.0", "IRC R304/R305", "loaded", 1e-6, None, None, None, 20.0, 20.0, 2.0, None, 0.85, None)
    ]
    cursor.executemany('''
        INSERT OR REPLACE INTO Jurisdictions 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', jurisdictions)

    # 2. Entity Specs (versioned v1)
    # Proportions, ventilation, safety, presence of components
    entities = [
        # (entity_type, version, min_area, min_side, max_side, habitable, min_aspect, max_aspect, req_window, req_egress, vent_type, req_door, req_closet)
        ("living", "v1", 70.0, 7.0, None, True, 1.2, 2.0, True, False, "natural", True, False),
        ("kitchen", "v1", 70.0, 7.0, None, True, 1.0, 2.0, False, False, "mechanical_or_natural", True, False),
        ("bedroom", "v1", 70.0, 7.0, None, True, 1.0, 1.8, True, True, "natural", True, True),
        ("bathroom", "v1", 25.0, 5.0, 15.0, False, 1.0, 2.0, False, False, "exhaust", True, False),
        ("corridor", "v1", 16.0, 4.0, None, False, 3.0, 10.0, False, False, "none", False, False),
        ("dining", "v1", 70.0, 7.0, None, True, 1.2, 1.8, False, False, "natural", True, False),
        ("laundry", "v1", 20.0, 4.0, None, False, 1.0, 3.0, False, False, "exhaust", True, False),
        ("garage", "v1", 200.0, 10.0, None, False, 1.0, 3.0, False, False, "natural", True, False),
        ("balcony", "v1", 40.0, 4.0, None, False, 1.0, 4.0, False, False, "natural", True, False)
    ]
    cursor.executemany('''
        INSERT OR REPLACE INTO EntitySpecs (entity_type, version, min_area_ft2, min_side_ft, max_side_ft, habitable, min_aspect_ratio, max_aspect_ratio, requires_exterior_window, requires_egress, ventilation_type, requires_door, requires_closet)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', entities)

    # 3. Relational Rules (versioned v1)
    # Adjacencies, distances, avoidances
    relations = [
        # Must connect / near (Preferences)
        ("bathroom", "bedroom", "ensuite_required", 4.0, None, "v1", "Bathroom must be ensuite to the bedroom sharing at least 4ft of wall."),
        ("kitchen", "living", "must_touch", 2.5, None, "v1", "Kitchen must connect to the living room sharing at least 2.5ft of wall."),
        ("kitchen", "dining", "must_touch", 4.0, None, "v1", "Kitchen must connect to dining."),
        ("living", "dining", "must_touch", 4.0, None, "v1", "Living room must connect to dining."),
        ("living", "entry", "near", None, 2.0, "v1", "Living room should be near the entry within 2ft distance."),
        ("bedroom", "corridor", "must_touch", 3.0, None, "v1", "Bedroom must connect to a corridor sharing at least 3ft of wall."),
        ("bathroom", "corridor", "must_touch", 2.5, None, "v1", "Bathroom must connect to a corridor sharing at least 2.5ft of wall."),
        ("balcony", "living", "must_touch", 4.0, None, "v1", "Balcony must connect to the living room sharing at least 4ft of wall."),
        
        # Avoidances (must_not_touch / far)
        ("bathroom", "kitchen", "must_not_touch", None, None, "v1", "Bathroom must not share a wall with the kitchen."),
        ("bathroom", "dining", "must_not_touch", None, None, "v1", "Bathroom must not share a wall with the dining room."),
        ("bathroom", "bathroom", "must_not_touch", None, None, "v1", "Bathrooms must not share a wall with each other."),
        ("kitchen", "bedroom", "must_not_touch", None, None, "v1", "Kitchen should not share a wall with a bedroom."),
        ("garage", "living", "must_not_touch", None, None, "v1", "Garage must not share a wall with the living room."),
        ("laundry", "bedroom", "must_not_touch", None, None, "v1", "Laundry should not touch quiet spaces like bedrooms."),
        
        # Distances
        ("kitchen", "dining", "distance_limit", None, 15.0, "v1", "Kitchen to Dining must be < 15 ft."),
        ("bedroom", "bathroom", "distance_limit", None, 25.0, "v1", "Bedroom to Bathroom must be < 25 ft."),
        ("entry", "living", "distance_limit", None, 20.0, "v1", "Entry to Living must be < 20 ft."),
        ("garage", "kitchen", "distance_limit", None, 30.0, "v1", "Garage to Kitchen must be < 30 ft."),
        ("laundry", "bedroom", "distance_limit", None, 40.0, "v1", "Laundry to Bedrooms must be < 40 ft.")
    ]
    cursor.execute('DELETE FROM RelationalRules')
    cursor.executemany('''
        INSERT INTO RelationalRules (entity_a, entity_b, relation, min_shared_wall_ft, max_dist_ft, version, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', relations)

    # 4. Area Rules
    area_rules = [
        ("living_gt_each_bedroom", "Living room must be larger than each individual bedroom."),
        ("bathroom_lt_served_bedroom", "Bathroom must be smaller than the bedroom it serves.")
    ]
    cursor.execute('DELETE FROM AreaRules')
    cursor.executemany('INSERT INTO AreaRules (rule, description) VALUES (?, ?)', area_rules)

    # 5. Zone-Specific Rule Overrides
    zone_rules = [
        ("Redmond, WA", "OBAT", "min_bicycle_parking_spaces_per_unit", "1.0", "Minimum bicycle parking spaces per unit (Transit-oriented design)."),
        ("Redmond, WA", "OBAT", "max_vehicle_parking_spaces_per_unit", "1.5", "Maximum vehicle parking spaces per unit (TMP cap)."),
        ("Redmond, WA", "OBAT", "max_far", "3.0", "Maximum Floor Area Ratio (FAR) allowed before purchasing bonus density."),
        ("Bellevue, WA", "MDR-1", "min_vehicle_parking_spaces_per_unit", "1.0", "Minimum vehicle parking spaces per unit."),
        ("Bellevue, WA", "MDR-1", "min_recreation_space_sqft_per_unit", "150.0", "Minimum recreation space per unit."),
        ("Bellevue, WA", "MDR-1", "min_significant_tree_diameter_inches", "6.0", "Trees with a diameter (DBH) equal to or greater than this value are legally classified as 'Significant' and cannot be cut down without a special permit and replacement plan."),
        ("Bellevue, WA", "MDR-1", "requires_garage_mechanical_ventilation_interlock", "true", "Garage mechanical ventilation must operate at 100% capacity upon fire alarm activation."),
        ("Kirkland, WA", "RM-3.6", "min_open_space_fraction", "0.40", "Minimum open space fraction."),
        ("Seattle, WA", "LR3", "min_amenity_area_fraction", "0.05", "Minimum amenity area fraction."),
        ("Seattle, WA", "LR3", "min_green_factor", "0.60", "Minimum required landscaping score."),
        ("Seattle, WA", "LR3", "requires_chapter_93_fire_safety_standards", "true", "Must comply with Seattle Fire Code Chapter 93 minimum life safety standards."),
        ("Bothell, WA", "R5", "min_vehicle_parking_spaces_per_unit", "0.0", "Minimum vehicle parking spaces per unit.")
    ]
    cursor.execute('DELETE FROM ZoneSpecificRules')
    cursor.executemany('INSERT INTO ZoneSpecificRules (jurisdiction, zone, rule_key, rule_value, description) VALUES (?, ?, ?, ?, ?)', zone_rules)

    conn.commit()
    conn.close()
    print("Database initialized and seeded.")

if __name__ == "__main__":
    init_db()
    seed_data()
