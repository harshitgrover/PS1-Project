import sqlite3
import json
import hashlib

import os

def get_zoning_hash(data_dict):
    json_str = json.dumps(data_dict)
    return "zoning_" + hashlib.sha256(json_str.encode('utf-8')).hexdigest()[:12]

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

def seed_demo_data(db_path=DEFAULT_DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    demo_1_dict = {
      "address": "one microsoft way, redmond, usa",
      "city": "Redmond",
      "zone": "OBAT",
      "latitude": 47.6411813,
      "longitude": -122.1266792,
      "parcel_centroid": {
        "lat": 47.63956595727283,
        "lon": -122.12844753035155
      },
      "parcel_area": 4289358.725313804,
      "lot_vertex_count": 32,
      
      "status": "ok",
      "jurisdiction": "Redmond, WA",
      "zone_code": "OBAT",
      "zone_type": "mixed_use",
      "zone_description": "Overlake Business and Advanced Technology District",
      "overlay_districts": [],
      "setbacks_ft": {
        "front": 0,
        "rear": 0,
        "side": 0
      },
      "max_lot_coverage_pct": None,
      "max_impervious_surface_pct": 80,
      "max_height_ft": 150,
      "max_height_ft_nonresidential": 120,
      "max_height_ft_with_incentives": 230,
      "min_height_ft": 35,
      "max_far": 3.0,
      "max_far_with_incentives": 9.5,
      "ground_floor_min_ceiling_ft": 16,
      "tree_protection_zones": [],
      "source_url": "https://redmond.municipal.codes/RZC/21.12.500",
      
      "parcel_id": "5503000010",
      "parcel_area_sqft": 4289358.725313804,
      "building_count": 39,
      "building_area_sqft": 1113207.6441514671,
      "building_file": "outputs/one microsoft way_ redmond_ usa_buildings.json",
      "geometry_file": "outputs/one microsoft way_ redmond_ usa_geometry.json"
    }
    
    demo_2_dict = {
      "address": "4115 178th ln se, bellevue, wa",
      "city": "Bellevue",
      "zone": "MDR-1",
      "latitude": 47.5716098,
      "longitude": -122.1016754,
      "parcel_centroid": {
        "lat": 47.571133432573134,
        "lon": -122.10194810311646
      },
      "parcel_area": 116818.63735631616,
      "lot_vertex_count": 13,
      
      "status": "ok",
      "jurisdiction": "Bellevue, WA",
      "zone_code": "MDR-1",
      "zone_type": "residential",
      "zone_description": None,
      "overlay_districts": [],
      "setbacks_ft": {
        "front": 20,
        "rear": 20,
        "side": 5
      },
      "max_lot_coverage_pct": 40.0,
      "max_impervious_surface_pct": None,
      "max_height_ft": 40.0,
      "max_height_ft_nonresidential": None,
      "max_height_ft_with_incentives": None,
      "min_height_ft": None,
      "max_far": None,
      "max_far_with_incentives": None,
      "ground_floor_min_ceiling_ft": None,
      "tree_protection_zones": [],
      "source_url": "https://bellevue.municipal.codes/LUC/20.20.010",
      
      "parcel_id": "4192000000",
      "parcel_area_sqft": 116818.63735631616,
      "building_count": 16,
      "building_area_sqft": 37484.973767939344,
      "building_file": "outputs/4115 178th ln se_ bellevue_ wa_buildings.json",
      "geometry_file": "outputs/4115 178th ln se_ bellevue_ wa_geometry.json"
    }
    
    hash_1 = get_zoning_hash(demo_1_dict)
    hash_2 = get_zoning_hash(demo_2_dict)
    
    # Wipe old demo hashes
    cursor.execute("DELETE FROM AgentOutputs WHERE id LIKE 'zoning_%'")
    
    cursor.execute('INSERT INTO AgentOutputs (id, data_json) VALUES (?, ?)', (hash_1, json.dumps(demo_1_dict)))
    cursor.execute('INSERT INTO AgentOutputs (id, data_json) VALUES (?, ?)', (hash_2, json.dumps(demo_2_dict)))

    conn.commit()
    conn.close()
    
    print("--- Demo Zoning Outputs Seeded ---")
    print(f"Redmond OBAT Hash: {hash_1}")
    print(f"Bellevue MDR-1 Hash: {hash_2}")

if __name__ == "__main__":
    seed_demo_data()
