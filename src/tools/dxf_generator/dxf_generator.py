import argparse
import sys
import os
import math
import logging
from .parser import parse_input_json
from .core_engine import DXFEngine
from .renderer import render_preview
from .dimensioning import format_feet_inches

logger = logging.getLogger(__name__)

def generate_dxf(json_paths: list, out_dxf: str, render: bool = False, out_img_prefix: str = "") -> None:
    """
    Generates a DXF file from one or more input JSON layout files.
    Optionally renders a PNG preview of the generated DXF.

    Args:
        json_paths (list): List of paths to input JSON files.
        out_dxf (str): Path to the output DXF file.
        render (bool): Whether to generate matplotlib preview images. Defaults to False.
        out_img_prefix (str): Prefix for the rendered preview image files. Defaults to "".

    Returns:
        None
    """
    engine = DXFEngine()
    logger.debug(f"Starting DXF generation for {len(json_paths)} input file(s). Output: {out_dxf}")

    combined_ir = {"metadata": {"type": "combined"}, "views": []}
    
    for json_path in json_paths:
        ir_data = parse_input_json(json_path)
        combined_ir["views"].extend(ir_data.get("views", []))
        
    for view in combined_ir["views"]:
        view_id = view.get("view_id", "default")
        
        # Load layers
        for layer in view.get("layers", []):
            engine.add_layer(f"{view_id}_{layer['name']}", layer.get("color", 7))
            
        # First Pass: Draw all polygons and hatches
        for ent in view.get("entities", []):
            ent_type = ent.get("type")
            layer_name = f"{view_id}_{ent.get('layer', '0')}"
            
            if ent_type == "polygon":
                pts = ent.get("points", [])
                engine.draw_polygon(pts, layer=layer_name, closed=ent.get("closed", True), color=ent.get("color"))
                
                if ent.get("auto_dimension", False) and len(pts) >= 2:
                    n = len(pts) if ent.get("closed", True) else len(pts) - 1
                    for i in range(n):
                        p1 = pts[i]
                        p2 = pts[(i+1) % len(pts)]
                        if p1 != p2:
                            dist = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
                            if dist >= 1.0:
                                engine.draw_dimension(p1, p2, offset=1.0, layer=f"{view_id}_Dimensions")
                            
        # Second Pass: Draw labels (so they are not occluded by solid hatches)
        for ent in view.get("entities", []):
            ent_type = ent.get("type")
            layer_name = f"{view_id}_{ent.get('layer', '0')}"
            
            if ent_type == "label":
                engine.draw_text(
                    text=ent.get("text", ""),
                    position=ent.get("position", [0,0]),
                    layer=layer_name,
                    height=ent.get("height", 0.5),
                    rotation=ent.get("rotation", 0.0)
                )
                
    engine.save(out_dxf)
    logger.info(f"DXF saved to {out_dxf}")
    
    if render:
        prefix = out_img_prefix if out_img_prefix else out_dxf.replace(".dxf", "")
        render_preview(combined_ir, prefix)
        logger.info(f"Rendered previews saved with prefix {prefix}")

