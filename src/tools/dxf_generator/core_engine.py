import ezdxf
from ezdxf import new as dxf_new  # type: ignore[attr-defined]
from ezdxf.gfxattribs import GfxAttribs
from ezdxf.lldxf.const import MTEXT_MIDDLE_CENTER  # type: ignore[import]
from typing import List, Tuple, Dict, Any
from .dimensioning import add_aligned_dimension

class DXFEngine:
    def __init__(self, version="R2010"):
        self.doc = dxf_new(version)
        self.msp = self.doc.modelspace()
        self.layers: Dict[str, Any] = {}
        
    def add_layer(self, name: str, color: int = 7):
        """Adds a layer with standard AutoCAD color if it doesn't exist."""
        if name not in self.layers:
            self.doc.layers.add(name=name, color=color)
            self.layers[name] = True
            
    def draw_polygon(self, points: List[Tuple[float, ...]], layer: str, closed: bool = True, color: int | None = None):
        if not points:
            return
        self.add_layer(layer)
        attribs = GfxAttribs(layer=layer)
        if color is not None:
            attribs.color = color
            
        # Detect if points are 3D (X, Y, Z)
        is_3d = False
        if points and len(points[0]) >= 3:
            is_3d = True
            
        if is_3d:
            # Polyline3D supports true 3D spatial lines
            pline = self.msp.add_polyline3d(points, dxfattribs=attribs)
            pline.close(closed)
        else:
            # LightWeight Polyline is more efficient for pure 2D
            pline = self.msp.add_lwpolyline(points, dxfattribs=attribs)
            pline.close(closed)

    def draw_line(self, start: Tuple[float, float], end: Tuple[float, float], layer: str, color: int | None = None):
        self.add_layer(layer)
        attribs = GfxAttribs(layer=layer)
        if color is not None:
            attribs.color = color
        self.msp.add_line(start, end, dxfattribs=attribs)

    def draw_text(self, text: str, position: Tuple[float, float], layer: str, height: float = 1.0, color: int | None = None, rotation: float = 0.0):
        self.add_layer(layer)
        attribs = GfxAttribs(layer=layer)
        if color is not None:
            attribs.color = color
        mtext = self.msp.add_mtext(text, dxfattribs=attribs)
        mtext.dxf.char_height = height
        mtext.dxf.insert = position
        mtext.dxf.attachment_point = MTEXT_MIDDLE_CENTER
        if rotation:
            mtext.dxf.rotation = rotation

    def draw_dimension(self, p1: Tuple[float, float], p2: Tuple[float, float], offset: float, layer: str):
        self.add_layer(layer)
        add_aligned_dimension(self.msp, p1, p2, offset, layer)

    def save(self, filepath: str):
        self.doc.saveas(filepath)
