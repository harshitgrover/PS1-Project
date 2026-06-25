import sqlite3
import json
import sys

import os

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

def extract_file(hashkey: str, db_path: str = DEFAULT_DB_PATH):
    """
    Connects to the database and extracts the full JSON ruleset by its ID.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT data_json FROM AgentOutputs WHERE id=?", (hashkey,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # Parse and return as pretty JSON
            parsed_json = json.loads(row[0])
            return json.dumps(parsed_json, indent=2)
        else:
            return f"Error: Hashkey '{hashkey}' not found in database."
            
    except Exception as e:
        return f"Database error: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 extract_file.py <hashkey>")
        sys.exit(1)
        
    r_id = sys.argv[1]
    result = extract_file(r_id)
    
    if result.startswith("Error"):
        print(result)
    else:
        out_dir = os.path.join(os.path.dirname(__file__), 'json_files')
        os.makedirs(out_dir, exist_ok=True)
        filename = f"{r_id}.json"
        output_filename = os.path.join(out_dir, filename)
        with open(output_filename, 'w') as f:
            f.write(result)
        print(f"Success! Extracted JSON saved to: json_files/{filename}")
