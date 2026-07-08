import argparse
import sys
import os
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DXF Generator")
    parser.add_argument("input_jsons", nargs='+', help="Path to one or more input JSON files")
    parser.add_argument("output_dxf", help="Path to output DXF file")
    parser.add_argument("--render", action="store_true", help="Generate matplotlib preview images")
    parser.add_argument("--img-prefix", default="", help="Prefix for rendered images")
    
    args = parser.parse_args()
    
    out_dxf = args.output_dxf
    img_prefix = args.img_prefix
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    gen_dir = os.path.join(base_dir, "generated_files")
    
    # If the user just specified a filename, route it to generated_files
    if not os.path.dirname(out_dxf):
        os.makedirs(gen_dir, exist_ok=True)
        out_dxf = os.path.join(gen_dir, out_dxf)
        
    # If they specified a custom image prefix without a path, route it as well
    if img_prefix and not os.path.dirname(img_prefix):
        os.makedirs(gen_dir, exist_ok=True)
        img_prefix = os.path.join(gen_dir, img_prefix)
        
    generate_dxf(args.input_jsons, out_dxf, args.render, img_prefix)
