import sqlite3
import json
import os

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

def init_db(db_path=DEFAULT_DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()


    # Table for interior entity specifications
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS EntitySpecs (
            entity_type TEXT PRIMARY KEY,
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
            requires_closet BOOLEAN,
            area_rules_json TEXT
        )
    ''')

    # Adjacency tables for each entity
    entities = ["living", "kitchen", "bedroom", "bathroom", "corridor", "dining", "laundry", "garage", "balcony", "entry"]
    for ent in entities:
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS Adjacency_{ent} (
                target_entity TEXT,
                relation TEXT,
                min_shared_wall_ft REAL,
                max_dist_ft REAL,
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

    # Table for zone-specific overrides per location
    locations = ["Seattle_Downtown_NR", "Redmond_WA", "Bellevue_WA", "Kirkland_WA", "Seattle_WA", "Bothell_WA"]
    for loc in locations:
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS ZoneRules_{loc} (
                zone TEXT,
                rule_key TEXT,
                rule_value TEXT,
                description TEXT,
                PRIMARY KEY (zone, rule_key)
            )
        ''')

    conn.commit()
    conn.close()

def seed_data(db_path=DEFAULT_DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()



    # 2. Entity Specs
    # Proportions, ventilation, safety, presence of components, and embedded area rules
    entities = [
        # (entity_type, min_area, min_side, max_side, habitable, min_aspect, max_aspect, req_window, req_egress, vent_type, req_door, req_closet, area_rules_json)
        ("living", 70.0, 7.0, None, True, 1.2, 2.0, True, False, "natural", True, False, json.dumps([{"rule": "living_gt_each_bedroom", "description": "Living room must be larger than each individual bedroom."}])),
        ("kitchen", 70.0, 7.0, None, True, 1.0, 2.0, False, False, "mechanical_or_natural", True, False, "[]"),
        ("bedroom", 70.0, 7.0, None, True, 1.0, 1.8, True, True, "natural", True, True, "[]"),
        ("bathroom", 25.0, 5.0, 15.0, False, 1.0, 2.0, False, False, "exhaust", True, False, json.dumps([{"rule": "bathroom_lt_served_bedroom", "description": "Bathroom must be smaller than the bedroom it serves."}])),
        ("corridor", 16.0, 4.0, None, False, 3.0, 10.0, False, False, "none", False, False, "[]"),
        ("dining", 70.0, 7.0, None, True, 1.2, 1.8, False, False, "natural", True, False, "[]"),
        ("laundry", 20.0, 4.0, None, False, 1.0, 3.0, False, False, "exhaust", True, False, "[]"),
        ("garage", 200.0, 10.0, None, False, 1.0, 3.0, False, False, "natural", True, False, "[]"),
        ("balcony", 40.0, 4.0, None, False, 1.0, 4.0, False, False, "natural", True, False, "[]")
    ]
    cursor.executemany('''
        INSERT OR REPLACE INTO EntitySpecs (entity_type, min_area_ft2, min_side_ft, max_side_ft, habitable, min_aspect_ratio, max_aspect_ratio, requires_exterior_window, requires_egress, ventilation_type, requires_door, requires_closet, area_rules_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', entities)
    
    # 3. Adjacency Lists per entity
    adjacency_lists = {
        "bathroom": [
            ("bedroom", "ensuite_required", 4.0, None, "Bathroom must be ensuite to the bedroom sharing at least 4ft of wall."),
            ("corridor", "must_touch", 2.5, None, "Bathroom must connect to a corridor sharing at least 2.5ft of wall."),
            ("kitchen", "must_not_touch", None, None, "Bathroom must not share a wall with the kitchen."),
            ("dining", "must_not_touch", None, None, "Bathroom must not share a wall with the dining room."),
            ("bathroom", "must_not_touch", None, None, "Bathrooms must not share a wall with each other.")
        ],
        "bedroom": [
            ("bathroom", "ensuite_required", 4.0, None, "Bathroom must be ensuite to the bedroom sharing at least 4ft of wall."),
            ("corridor", "must_touch", 3.0, None, "Bedroom must connect to a corridor sharing at least 3ft of wall."),
            ("kitchen", "must_not_touch", None, None, "Kitchen should not share a wall with a bedroom."),
            ("laundry", "must_not_touch", None, None, "Laundry should not touch quiet spaces like bedrooms."),
            ("bathroom", "distance_limit", None, 25.0, "Bedroom to Bathroom must be < 25 ft."),
            ("laundry", "distance_limit", None, 40.0, "Laundry to Bedrooms must be < 40 ft.")
        ],
        "kitchen": [
            ("living", "must_touch", 2.5, None, "Kitchen must connect to the living room sharing at least 2.5ft of wall."),
            ("dining", "must_touch", 4.0, None, "Kitchen must connect to dining."),
            ("bathroom", "must_not_touch", None, None, "Bathroom must not share a wall with the kitchen."),
            ("bedroom", "must_not_touch", None, None, "Kitchen should not share a wall with a bedroom."),
            ("dining", "distance_limit", None, 15.0, "Kitchen to Dining must be < 15 ft."),
            ("garage", "distance_limit", None, 30.0, "Garage to Kitchen must be < 30 ft.")
        ],
        "living": [
            ("kitchen", "must_touch", 2.5, None, "Kitchen must connect to the living room sharing at least 2.5ft of wall."),
            ("dining", "must_touch", 4.0, None, "Living room must connect to dining."),
            ("entry", "near", None, 2.0, "Living room should be near the entry within 2ft distance."),
            ("balcony", "must_touch", 4.0, None, "Balcony must connect to the living room sharing at least 4ft of wall."),
            ("garage", "must_not_touch", None, None, "Garage must not share a wall with the living room."),
            ("entry", "distance_limit", None, 20.0, "Entry to Living must be < 20 ft.")
        ],
        "dining": [
            ("kitchen", "must_touch", 4.0, None, "Kitchen must connect to dining."),
            ("living", "must_touch", 4.0, None, "Living room must connect to dining."),
            ("bathroom", "must_not_touch", None, None, "Bathroom must not share a wall with the dining room."),
            ("kitchen", "distance_limit", None, 15.0, "Kitchen to Dining must be < 15 ft.")
        ],
        "corridor": [
            ("bedroom", "must_touch", 3.0, None, "Bedroom must connect to a corridor sharing at least 3ft of wall."),
            ("bathroom", "must_touch", 2.5, None, "Bathroom must connect to a corridor sharing at least 2.5ft of wall."),
            ("living", "must_touch", 3.0, None, "Living room must connect to a corridor sharing at least 3ft of wall."),
            ("kitchen", "must_touch", 3.0, None, "Kitchen must connect to a corridor sharing at least 3ft of wall.")
        ],
        "entry": [
            ("living", "near", None, 2.0, "Living room should be near the entry within 2ft distance."),
            ("living", "distance_limit", None, 20.0, "Entry to Living must be < 20 ft.")
        ],
        "balcony": [
            ("living", "must_touch", 4.0, None, "Balcony must connect to the living room sharing at least 4ft of wall.")
        ],
        "garage": [
            ("living", "must_not_touch", None, None, "Garage must not share a wall with the living room."),
            ("kitchen", "distance_limit", None, 30.0, "Garage to Kitchen must be < 30 ft.")
        ],
        "laundry": [
            ("bedroom", "must_not_touch", None, None, "Laundry should not touch quiet spaces like bedrooms."),
            ("bedroom", "distance_limit", None, 40.0, "Laundry to Bedrooms must be < 40 ft.")
        ]
    }
    
    for ent, rules in adjacency_lists.items():
        # First, ensure the table exists just in case
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS Adjacency_{ent} (
                target_entity TEXT,
                relation TEXT,
                min_shared_wall_ft REAL,
                max_dist_ft REAL,
                description TEXT
            )
        ''')
        cursor.execute(f'DELETE FROM Adjacency_{ent}')
        cursor.executemany(f'''
            INSERT INTO Adjacency_{ent} (target_entity, relation, min_shared_wall_ft, max_dist_ft, description)
            VALUES (?, ?, ?, ?, ?)
        ''', rules)


    # 5. Zone-Specific Rule Overrides per location
    zone_rules = {
        "Redmond_WA": [
            ("OBAT", "min_bicycle_parking_spaces_per_unit", "1.0", "Minimum bicycle parking spaces per unit (Transit-oriented design)."),
            ("OBAT", "max_vehicle_parking_spaces_per_unit", "1.5", "Maximum vehicle parking spaces per unit (TMP cap)."),
            ("OBAT", "max_far", "3.0", "Maximum Floor Area Ratio (FAR) allowed before purchasing bonus density.")
        ],
        "Bellevue_WA": [
            ("MDR-1", "min_vehicle_parking_spaces_per_unit", "1.0", "Minimum vehicle parking spaces per unit."),
            ("MDR-1", "min_recreation_space_sqft_per_unit", "150.0", "Minimum recreation space per unit."),
            ("MDR-1", "min_significant_tree_diameter_inches", "6.0", "Trees with a diameter (DBH) equal to or greater than this value are legally classified as 'Significant' and cannot be cut down without a special permit and replacement plan."),
            ("MDR-1", "requires_garage_mechanical_ventilation_interlock", "true", "Garage mechanical ventilation must operate at 100% capacity upon fire alarm activation.")
        ],
        "Kirkland_WA": [
            ("RM-3.6", "min_open_space_fraction", "0.40", "Minimum open space fraction.")
        ],
        "Seattle_WA": [
            ("LR3", "min_amenity_area_fraction", "0.05", "Minimum amenity area fraction."),
            ("LR3", "min_green_factor", "0.60", "Minimum required landscaping score."),
            ("LR3", "requires_chapter_93_fire_safety_standards", "true", "Must comply with Seattle Fire Code Chapter 93 minimum life safety standards.")
        ],
        "Bothell_WA": [
            ("R5", "min_vehicle_parking_spaces_per_unit", "0.0", "Minimum vehicle parking spaces per unit.")
        ]
    }
    
    for loc, rules in zone_rules.items():
        # Ensure table exists dynamically if new locations added to dict
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS ZoneRules_{loc} (
                zone TEXT,
                rule_key TEXT,
                rule_value TEXT,
                description TEXT,
                PRIMARY KEY (zone, rule_key)
            )
        ''')
        cursor.execute(f'DELETE FROM ZoneRules_{loc}')
        cursor.executemany(f'''
            INSERT INTO ZoneRules_{loc} (zone, rule_key, rule_value, description)
            VALUES (?, ?, ?, ?)
        ''', rules)

    conn.commit()
    conn.close()
    print("Database initialized and seeded.")

if __name__ == "__main__":
    init_db()
    seed_data()
