import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Ensure variables exist
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in environment.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def seed_constraint_agent_data():
    print("Seeding Constraint Agent Data (Zone Rules & Style Rules)...")
    
    # Zone Rules
    zone_rules_data = {
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
            ("R5", "min_vehicle_parking_spaces_per_unit", "0.0", "Minimum vehicle parking spaces per unit (Bothell eliminated minimum parking)."),
            ("R5", "min_front_setback_ft", "20.0", "Minimum front property line setback in feet."),
            ("R5", "min_side_setback_ft", "5.0", "Minimum side property line setback in feet for 1-story structures."),
            ("R5", "min_rear_setback_ft", "10.0", "Minimum rear property line setback in feet.")
        ]
    }
    
    zone_rows = []
    for loc, rules in zone_rules_data.items():
        for rule in rules:
            zone_rows.append({
                "location": loc,
                "zone": rule[0],
                "rule_key": rule[1],
                "rule_value": rule[2],
                "description": rule[3]
            })
            
    if zone_rows:
        supabase.table("zone_rules").upsert(zone_rows, on_conflict="location,zone,rule_key").execute()

    # Style Rules
    style_rules_data = [
        ("vastu", "kitchen_location", "southeast", "According to Vastu, the kitchen should be in the southeast corner."),
        ("vastu", "master_bedroom_location", "southwest", "According to Vastu, the master bedroom should be in the southwest corner."),
        ("vastu", "entrance_facing", "east_or_north", "According to Vastu, the main entrance should face East or North."),
        ("vastu", "bathroom_location", "northwest_or_west", "According to Vastu, bathrooms and toilets should be in the Northwest or West zones, never in the Northeast or Center."),
        ("vastu", "living_room_location", "east_or_north", "According to Vastu, the living room should be in the East or North direction for positive energy."),
        ("vastu", "center_zone_status", "empty", "The center of the house (Brahmasthan) must be kept completely empty and free of heavy structures or bathrooms."),
        ("vastu", "staircase_location", "south_or_west", "Staircases should ideally be located in the South or West zones."),
        ("vastu", "guest_bedroom_location", "northwest", "Guest bedrooms are best placed in the Northwest corner."),
        ("vastu", "study_room_location", "east_or_north", "Study rooms should be located in the East, North, or Northeast."),
        ("vastu", "puja_room_location", "northeast", "The prayer (Puja) room must be strictly in the Northeast corner (Ishan Kona)."),
        ("vastu", "window_placement", "north_east_bias", "Maximum windows should be placed on North and East walls to allow morning sunlight."),
        ("vastu", "staircase_direction", "clockwise", "Staircases should always turn clockwise as you go up."),
        ("vastu", "kitchen_cooking_facing", "east", "While cooking, one must face East."),
        ("vastu", "master_bed_direction", "head_south", "While sleeping, the head should point towards South or East, never North."),
        ("vastu", "door_count", "even", "Total number of doors and windows should be an even number (but avoid ending in 0 like 10 or 20)."),
        ("vastu", "boundary_wall_height", "high_south_west", "The boundary walls in the South and West should be thicker and higher than North and East walls."),
        
        ("xhengoi", "front_door_facing", "south", "According to Xhengoi (Feng Shui), the front door should ideally face south."),
        ("xhengoi", "bed_facing", "not_door", "According to Xhengoi, the bed should not directly face the door."),
        ("xhengoi", "bathroom_location", "not_center", "According to Xhengoi (Feng Shui), bathrooms should never be in the center of the home (the heart of the house)."),
        ("xhengoi", "staircase_facing", "not_front_door", "Staircases must not directly face the front door so energy (Chi) does not immediately flow out."),
        ("xhengoi", "kitchen_bathroom_relation", "must_not_face", "The kitchen door should not directly face the bathroom door to avoid mixing fire and water elements."),
        ("xhengoi", "bed_position", "command_position", "Beds should be in the command position (facing the door but not directly in line with it, with a solid wall behind)."),
        ("xhengoi", "living_room_location", "front_half", "The living room should be located in the front half of the house, close to the main entrance."),
        ("xhengoi", "hallway_shape", "not_straight_line", "Avoid long, straight hallways connecting the front and back doors to prevent fast-moving energy (Sha Chi)."),
        ("xhengoi", "kitchen_stove_placement", "not_under_window", "The stove must have a solid wall behind it and not be placed under a window."),
        ("xhengoi", "kitchen_sink_stove_relation", "not_adjacent", "Sink (water) and stove (fire) should not be adjacent or directly face each other.")
    ]
    
    style_rows = []
    for rule in style_rules_data:
        style_rows.append({
            "style": rule[0],
            "rule_key": rule[1],
            "rule_value": rule[2],
            "description": rule[3]
        })
        
    if style_rows:
        supabase.table("style_rules").upsert(style_rows, on_conflict="style,rule_key").execute()

def seed_entity_constraint_engine_data():
    print("Seeding Entity Constraint Engine Data (Entity Specs & Adjacency Rules)...")
    
    # Entity Specs
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
    
    spec_rows = []
    for e in entities:
        spec_rows.append({
            "entity_type": e[0],
            "min_area_ft2": e[1],
            "min_side_ft": e[2],
            "max_side_ft": e[3],
            "habitable": e[4],
            "min_aspect_ratio": e[5],
            "max_aspect_ratio": e[6],
            "requires_exterior_window": e[7],
            "requires_egress": e[8],
            "ventilation_type": e[9],
            "requires_door": e[10],
            "requires_closet": e[11],
            "area_rules_json": e[12]
        })
        
    if spec_rows:
        supabase.table("entity_specs").upsert(spec_rows, on_conflict="entity_type").execute()
        
    # Adjacency Rules
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
    
    adj_rows = []
    for source_ent, rules in adjacency_lists.items():
        for rule in rules:
            adj_rows.append({
                "source_entity": source_ent,
                "target_entity": rule[0],
                "relation": rule[1],
                "min_shared_wall_ft": rule[2],
                "max_dist_ft": rule[3],
                "description": rule[4]
            })
            
    if adj_rows:
        supabase.table("adjacency_rules").upsert(adj_rows, on_conflict="source_entity,target_entity,relation").execute()

if __name__ == "__main__":
    seed_constraint_agent_data()
    seed_entity_constraint_engine_data()
    print("Seeding complete.")
