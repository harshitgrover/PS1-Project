import json
import random
from typing import Dict, Any, List

def _convert_generic_json_to_ir(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback parser that converts a generic JSON dictionary into an Intermediate Representation (IR).
    Recursively searches for anything resembling a list of 2D points to create polygons.

    Args:
        data (Dict[str, Any]): A generic unstructured JSON dictionary containing geometric data.

    Returns:
        Dict[str, Any]: A structured Intermediate Representation (IR) containing views and entities.
    """
    layers_dict = {}
    entities = []
    
    def is_list_of_points(node: Any) -> bool:
        """
        Determines if a given node represents a list of coordinates (e.g. [[x, y], [x, y]]).

        Args:
            node (Any): The data node to evaluate.

        Returns:
            bool: True if it is a list of 2D/3D points, False otherwise.
        """
        if not isinstance(node, list) or len(node) < 2:
            return False
        for p in node:
            if not isinstance(p, (list, tuple)) or len(p) not in (2, 3):
                return False
            if not all(isinstance(c, (int, float)) for c in p):
                return False
        return True

    def traverse(node: Any, current_key: str = "Generic") -> None:
        """
        Recursively traverses a JSON structure to find point arrays.
        Infers context for layer names and labels.

        Args:
            node (Any): The current JSON node being traversed.
            current_key (str): The context or key inferred from the parent dictionary.
        """
        if isinstance(node, dict):
            # Try to build a better context string
            context = ""
            if "type" in node and isinstance(node["type"], str):
                context = node["type"]
            elif "name" in node and isinstance(node["name"], str):
                context = node["name"]
            elif "id" in node and isinstance(node["id"], str):
                context = node["id"]
                
            for k, v in node.items():
                pass_key = f"{context}_{k}" if context else k
                # Clean up the layer name to avoid weird characters
                pass_key = "".join(c if c.isalnum() else "_" for c in pass_key).strip("_")
                if not pass_key:
                    pass_key = "Generic"
                traverse(v, pass_key)
                
        elif isinstance(node, list):
            if is_list_of_points(node):
                # We found a polygon/polyline!
                # Ensure it only takes x, y (ignore z for 2D DXF)
                pts = [[float(p[0]), float(p[1])] for p in node]
                
                layer_name = current_key.capitalize()
                if layer_name not in layers_dict:
                    # Assign a random color 1-7
                    layers_dict[layer_name] = random.randint(1, 7)
                    
                entities.append({
                    "type": "polygon",
                    "layer": layer_name,
                    "points": pts,
                    "closed": True,  # Assume closed for generic polygons
                    "auto_dimension": True
                })
                
                # Add an inferred label based on the dictionary key
                if current_key and current_key.lower() not in ["generic", "polygon", "points", "boundary"]:
                    min_x = min(p[0] for p in pts)
                    max_x = max(p[0] for p in pts)
                    min_y = min(p[1] for p in pts)
                    max_y = max(p[1] for p in pts)
                    cx = (min_x + max_x) / 2
                    cy = (min_y + max_y) / 2
                    
                    entities.append({
                        "type": "label",
                        "layer": layer_name,
                        "text": current_key.replace("_", " ").title(),
                        "position": [cx, cy],
                        "height": 0.8,
                        "rotation": 0.0
                    })
            else:
                for item in node:
                    traverse(item, current_key)
                    
    traverse(data)
    
    if not entities:
        raise ValueError("Unrecognized JSON format. Could not find any geometric data (lists of 2D points).")
        
    layers = [{"name": name, "color": color} for name, color in layers_dict.items()]
    
    return {
        "metadata": {"type": "converted_generic_json"},
        "views": [
            {
                "view_id": "generic_view",
                "type": "generic",
                "layers": layers,
                "entities": entities
            }
        ]
    }


def _convert_floor_plan_to_ir(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts a structured floor plan JSON into an Intermediate Representation (IR).
    Extracts rooms, boundaries, doors, and windows, assigning predefined colors.

    Args:
        data (Dict[str, Any]): Floor plan JSON data.

    Returns:
        Dict[str, Any]: A structured Intermediate Representation (IR) format.
    """
    room_color_map = {
        "kitchen": 1,     # Red
        "dining": 2,      # Yellow
        "living_room": 3, # Green
        "bedroom": 4,     # Cyan
        "bathroom": 5,    # Blue
        "corridor": 6,    # Magenta
        "balcony": 8,     # Gray
        "entrance": 9,    # Light Gray
        "default": 7      # Black
    }
    
    layers = [
        {"name": "Boundary", "color": 7},
        {"name": "Labels", "color": 7},
        {"name": "Doors", "color": 2},
        {"name": "Windows", "color": 4}
    ]
    
    if "rooms" in data:
        added_room_types = set()
        for room in data["rooms"]:
            rtype = room.get("type", "default")
            layer_name = f"Room_{rtype.title()}"
            if layer_name not in added_room_types:
                layers.append({"name": layer_name, "color": room_color_map.get(rtype, 7)})
                added_room_types.add(layer_name)

    entities = []
    
    # Boundary
    if "boundary" in data:
        entities.append({
            "type": "polygon",
            "layer": "Boundary",
            "points": data["boundary"],
            "closed": True,
            "auto_dimension": True
        })
        
    # Rooms
    if "rooms" in data:
        for room in data["rooms"]:
            if "polygon" in room:
                rtype = room.get("type", "default")
                layer_name = f"Room_{rtype.title()}"
                
                entities.append({
                    "type": "polygon",
                    "layer": layer_name,
                    "points": room["polygon"],
                    "closed": True,
                    "auto_dimension": True
                })
                pts = room["polygon"]
                min_x = min(p[0] for p in pts)
                max_x = max(p[0] for p in pts)
                min_y = min(p[1] for p in pts)
                max_y = max(p[1] for p in pts)
                
                # Calculate true polygon area and centroid
                signed_area = 0.0
                cx = 0.0
                cy = 0.0
                for i in range(len(pts)):
                    x0, y0 = pts[i]
                    x1, y1 = pts[(i + 1) % len(pts)]
                    a = (x0 * y1) - (x1 * y0)
                    signed_area += a
                    cx += (x0 + x1) * a
                    cy += (y0 + y1) * a
                    
                signed_area *= 0.5
                if signed_area != 0:
                    cx = cx / (6.0 * signed_area)
                    cy = cy / (6.0 * signed_area)
                else:
                    # Fallback to bounding box center if area is 0
                    cx = (min_x + max_x) / 2
                    cy = (min_y + max_y) / 2
                
                width = max_x - min_x
                height = max_y - min_y
                # Absolute area for the label
                area = room.get("area", abs(signed_area))
                
                from .dimensioning import format_feet_inches
                
                name = room.get("name", "").replace("_", " ").title()
                label_text = f"{name}\n{format_feet_inches(width)} x {format_feet_inches(height)}\nArea: {area:.1f} sqft"
                
                # Make rotation heuristic much stricter (only for very narrow corridors)
                rotation = 90.0 if height > width * 2.0 else 0.0
                
                entities.append({
                    "type": "label",
                    "layer": "Labels",
                    "text": label_text,
                    "position": [cx, cy],
                    "height": 0.8,
                    "rotation": rotation
                })
                
    # Doors
    if "doors" in data:
        for door in data["doors"]:
            if "polygon" in door:
                entities.append({
                    "type": "polygon",
                    "layer": "Doors",
                    "points": door["polygon"],
                    "closed": True
                })
                
    # Windows
    if "windows" in data:
        for window in data["windows"]:
            if "polygon" in window:
                entities.append({
                    "type": "polygon",
                    "layer": "Windows",
                    "points": window["polygon"],
                    "closed": True
                })

    return {
        "metadata": {"type": "converted_floor_plan"},
        "views": [
            {
                "view_id": data.get("job_id", "floor_plan"),
                "type": "floor_plan",
                "layers": layers,
                "entities": entities
            }
        ]
    }


def _convert_site_plan_to_ir(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts a basic site plan (final_shell) JSON into an Intermediate Representation (IR).

    Args:
        data (Dict[str, Any]): Site plan JSON data containing a final_shell polygon.

    Returns:
        Dict[str, Any]: A structured Intermediate Representation (IR) format.
    """
    layers = [
        {"name": "Site_Boundary", "color": 1}
    ]
    entities = []
    
    if "final_shell" in data:
        entities.append({
            "type": "polygon",
            "layer": "Site_Boundary",
            "points": data["final_shell"],
            "closed": True,
            "auto_dimension": True
        })
        
    return {
        "metadata": {"type": "converted_site_plan"},
        "views": [
            {
                "view_id": "site_plan",
                "type": "site_plan",
                "layers": layers,
                "entities": entities
            }
        ]
    }

def parse_input_json(filepath: str) -> Dict[str, Any]:
    """
    Reads a JSON file from disk, unwraps envelope structures if present,
    and returns a standardized Intermediate Representation (IR) for rendering.
    Uses heuristics to determine if the input is an IR, a floor plan, a site plan,
    or unstructured generic data.

    Args:
        filepath (str): The absolute or relative path to the input JSON file.

    Returns:
        Dict[str, Any]: A standardized Intermediate Representation (IR).

    Raises:
        Exception: If the file cannot be read, contains invalid JSON, or lacks geometry.
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            


        # Check if universal contract
        if "views" in data:
            return data
            
        # Heuristics for old formats
        if "rooms" in data and "boundary" in data:
            return _convert_floor_plan_to_ir(data)
            
        if "final_shell" in data:
            return _convert_site_plan_to_ir(data)
            
        # Ultimate fallback: recursively hunt for anything that looks like a polygon
        return _convert_generic_json_to_ir(data)

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error parsing input JSON '{filepath}': {e}", exc_info=True)
        raise
