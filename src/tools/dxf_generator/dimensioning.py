import ezdxf
import math
from typing import Tuple, Any

def add_aligned_dimension(msp: Any, p1: Tuple[float, float], p2: Tuple[float, float], offset: float, layer: str) -> None:
    """
    Adds an aligned dimension between p1 and p2, shifted by `offset`.
    Uses ezdxf's linear dimension.

    Args:
        msp (Any): The ezdxf modelspace object.
        p1 (Tuple[float, float]): Starting point coordinates (X, Y).
        p2 (Tuple[float, float]): Ending point coordinates (X, Y).
        offset (float): Orthogonal offset distance for the dimension line.
        layer (str): The name of the layer to draw the dimension on.
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return
        
    # Calculate normal vector for offset
    nx = -dy / length
    ny = dx / length
    
    # Base point for dimension line
    base_x = p1[0] + nx * offset
    base_y = p1[1] + ny * offset
    
    # Angle in degrees
    angle_rad = math.atan2(dy, dx)
    angle_deg = math.degrees(angle_rad)
    
    dim_text = format_feet_inches(length)
    
    dim = msp.add_linear_dim(
        base=(base_x, base_y),
        p1=p1,
        p2=p2,
        angle=angle_deg,
        text=dim_text,
        override={
            "dimasz": 0.3,   # Arrow size (middle ground)
            "dimtxt": 0.6,   # Text size (middle ground)
            "dimexe": 0.1,   # Extension line extension
            "dimexo": 0.1,   # Extension line offset
            "dimtad": 1      # Text above dimension line
        },
        dxfattribs={"layer": layer}
    )
    dim.render()

def format_feet_inches(decimal_feet: float) -> str:
    """
    Converts decimal feet to a formatted feet-inches string (e.g. 24.67 -> 24'8").

    Args:
        decimal_feet (float): The length in decimal feet.

    Returns:
        str: The formatted dimension string.
    """
    f = int(decimal_feet)
    i = round((decimal_feet - f) * 12)
    if i == 12:
        f += 1
        i = 0
    return f"{f}'{i}\"" if i else f"{f}'"
