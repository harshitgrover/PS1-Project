import ezdxf
from ezdxf import new as dxf_new  # type: ignore[attr-defined]
from ezdxf.gfxattribs import GfxAttribs
from ezdxf.lldxf.const import MTEXT_MIDDLE_CENTER  # type: ignore[import]
from typing import List, Tuple, Dict, Any
from .dimensioning import add_aligned_dimension

class DXFEngine:
    """
    A core engine for generating DXF files using ezdxf.
    Provides simplified methods for drawing basic geometric shapes and annotations.
    """
    
    def __init__(self, version="R2010"):
        """
        Initializes a new DXF document.

        Args:
            version (str): The AutoCAD DXF version format to use. Defaults to "R2010".
        """
        self.doc = dxf_new(version)
        self.msp = self.doc.modelspace()
        self.layers: Dict[str, Any] = {}
        
    def add_layer(self, name: str, color: int = 7) -> None:
        """
        Adds a layer with standard AutoCAD color if it doesn't exist.

        Args:
            name (str): The name of the layer.
            color (int): AutoCAD Color Index (ACI). Defaults to 7 (black/white).
        """
        if name not in self.layers:
            self.doc.layers.add(name=name, color=color)
            self.layers[name] = True
            
    def draw_polygon(self, points: List[Tuple[float, ...]], layer: str, closed: bool = True, color: int | None = None) -> None:
        """
        Draws a 2D or 3D polygon/polyline.

        Args:
            points (List[Tuple[float, ...]]): A list of (X, Y) or (X, Y, Z) coordinate tuples.
            layer (str): The layer name to draw on.
            closed (bool): Whether the polygon should automatically close back to the start. Defaults to True.
            color (int | None): Optional color override. Defaults to None (layer color).
        """
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

    def draw_line(self, start: Tuple[float, float], end: Tuple[float, float], layer: str, color: int | None = None) -> None:
        """
        Draws a single straight line.

        Args:
            start (Tuple[float, float]): Starting (X, Y) coordinates.
            end (Tuple[float, float]): Ending (X, Y) coordinates.
            layer (str): The layer name to draw on.
            color (int | None): Optional color override. Defaults to None (layer color).
        """
        self.add_layer(layer)
        attribs = GfxAttribs(layer=layer)
        if color is not None:
            attribs.color = color
        self.msp.add_line(start, end, dxfattribs=attribs)

    def draw_text(self, text: str, position: Tuple[float, float], layer: str, height: float = 1.0, color: int | None = None, rotation: float = 0.0) -> None:
        """
        Draws MTEXT (multiline text) centered at the given position.

        Args:
            text (str): The text content to display.
            position (Tuple[float, float]): The (X, Y) center position.
            layer (str): The layer name to draw on.
            height (float): Text height. Defaults to 1.0.
            color (int | None): Optional color override. Defaults to None (layer color).
            rotation (float): Text rotation angle in degrees. Defaults to 0.0.
        """
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

    def draw_dimension(self, p1: Tuple[float, float], p2: Tuple[float, float], offset: float, layer: str) -> None:
        """
        Draws an aligned linear dimension between two points.

        Args:
            p1 (Tuple[float, float]): Starting point (X, Y).
            p2 (Tuple[float, float]): Ending point (X, Y).
            offset (float): Offset distance from the line being measured.
            layer (str): The layer name to draw on.
        """
        self.add_layer(layer)
        add_aligned_dimension(self.msp, p1, p2, offset, layer)

    def save(self, filepath: str) -> None:
        """
        Saves the DXF document to the local filesystem.

        Args:
            filepath (str): The full path where the .dxf file will be saved.
        """
        self.doc.saveas(filepath)
