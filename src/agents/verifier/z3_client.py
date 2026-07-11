import os
import sys
import logging
from contracts import VerificationRequest, ViolationDetail, Severity

logger = logging.getLogger(__name__)

# Add z3_verifier_tool to path
z3_tool_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools', 'z3_verifier'))
if z3_tool_path not in sys.path:
    sys.path.append(z3_tool_path)

import verifier_tool as vz  # type: ignore

def get_bounds(polygon):
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)

def adapt_shell_request(request: VerificationRequest) -> dict:
    house_dict = {"corners": [], "door": []}
    for entity in request.entities:
        if entity.type == "shell":
            house_dict["corners"] = entity.polygon
        elif entity.type == "door":
            house_dict["door"] = entity.polygon[0]
            
    if not house_dict["door"] and house_dict["corners"]:
        x_min, y_min, w, h = get_bounds(house_dict["corners"])
        house_dict["door"] = [x_min + w / 2, y_min]
    return house_dict

def adapt_room_request(request: VerificationRequest) -> dict:
    layout_dict = {"footprint": [], "door": [], "rooms": []}
    for entity in request.entities:
        if entity.type == "shell":
            x, y, w, h = get_bounds(entity.polygon)
            layout_dict["footprint"] = [x, y, x + w, y + h]
        elif entity.type == "door":
            layout_dict["door"] = entity.polygon[0]
        elif entity.type in ["room", "bedroom", "bathroom", "kitchen", "living", "dining", "corridor"]:
            x, y, w, h = get_bounds(entity.polygon)
            layout_dict["rooms"].append([entity.id, entity.type, x, y, x + w, y + h])
            
    if not layout_dict["door"] and layout_dict["footprint"]:
        layout_dict["door"] = [
            (layout_dict["footprint"][0] + layout_dict["footprint"][2]) / 2, 
            layout_dict["footprint"][1]
        ]
        
    return layout_dict

def verify(request: VerificationRequest) -> tuple[list[ViolationDetail], list[ViolationDetail]]:
    hard_violations = []
    soft_violations = []
    
    city_string = request.jurisdiction.split(",")[0].strip().lower()

    # Extract dynamic constraints if provided
    sbc_obj = None
    if request.constraints:
        try:
            from constraints import SBCConstraints  # type: ignore
            from dataclasses import fields
            valid_keys = {f.name for f in fields(SBCConstraints)}
            
            kwargs = {}
            for c in request.constraints:
                if "value" in c.params and c.id in valid_keys:
                    kwargs[c.id] = c.params["value"]
            sbc_obj = SBCConstraints(**kwargs)
        except ImportError:
            logger.warning("Could not import SBCConstraints")
        except TypeError as e:
            logger.warning(f"Failed to build SBCConstraints from request: {e}")

    if request.stage.value == "shell":
        house_dict = adapt_shell_request(request)
        
        if sbc_obj:
            res = vz.verify_site(house_dict, sbc=sbc_obj)
        else:
            res = vz.verify_site(house_dict, city_string)
        
        if not res.get("ok"):
            for constraint in res.get("constraints", []):
                if not constraint["pass"]:
                    measured = constraint.get("measured")
                    required = constraint.get("required")
                    
                    hard_violations.append(ViolationDetail(
                        constraint_id=constraint["rule"],
                        entity_id="exterior_shell",
                        severity=Severity.hard,
                        message=constraint["message"],
                        current_value=measured,
                        required_value=required,
                        delta=(measured - required) if measured is not None and required is not None else None
                    ))
                    
    elif request.stage.value == "room":
        layout_dict = adapt_room_request(request)
        
        if sbc_obj:
            res = vz.verify_interior(layout_dict, sbc=sbc_obj, interior_rules=request.interior_rules)
        else:
            res = vz.verify_interior(layout_dict, city_string, interior_rules=request.interior_rules)
        
        if not res.get("ok"):
            for violation in res.get("violations", []):
                measured = violation.get("measured")
                required = violation.get("required")
                
                hard_violations.append(ViolationDetail(
                    constraint_id=violation["rule"],
                    entity_id="interior",
                    severity=Severity.hard,
                    message=violation["message"],
                    current_value=measured,
                    required_value=required,
                    delta=(measured - required) if measured is not None and required is not None else None
                ))
    
    return hard_violations, soft_violations
