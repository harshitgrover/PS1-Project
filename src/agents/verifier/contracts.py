from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator

class AckResponse(BaseModel):
    status: str = "started"

class Stage(str, Enum):
    shell = "shell"
    room = "room"

class Severity(str, Enum):
    hard = "hard"
    soft = "soft"

class GeometryEntity(BaseModel):
    id: str
    type: str
    polygon: List[List[float]]
    area_sqft: Optional[float] = None

    @field_validator('polygon')
    def validate_polygon(cls, v):
        if len(v) < 3:
            raise ValueError('Polygon must have at least 3 vertices')
        return v

class Constraint(BaseModel):
    id: str
    type: str
    severity: Severity
    params: Dict[str, Any]
    # Intentionally omitted shapely/z3 tags as per specification

class VerificationRequest(BaseModel):
    session_id: str
    callback_url: Optional[str] = None
    stage: Stage
    entities: List[GeometryEntity]
    constraints: List[Constraint]
    envelope_polygon: List[List[float]]
    jurisdiction: str
    total_lot_area_sqft: float
    interior_rules: Optional[Dict[str, Any]] = None

class ViolationDetail(BaseModel):
    constraint_id: str
    entity_id: str
    severity: Severity
    message: str # Strictly adhering to the No-Leak rule
    current_value: Optional[float] = None
    required_value: Optional[float] = None
    delta: Optional[float] = None
    # Explicitly omitted 'suggestion' or 'corrected_coordinates' fields

class VerificationResponse(BaseModel):
    session_id: str
    result: str # "SAT" | "UNSAT"
    hard_violations: List[ViolationDetail]
    soft_violations: List[ViolationDetail]
