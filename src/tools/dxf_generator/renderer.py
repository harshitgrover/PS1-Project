import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math
from typing import Dict, Any

# AutoCAD ACI to Hex Map
ACI_COLORS = {
    1: "#FF0000", # Red
    2: "#FFFF00", # Yellow
    3: "#00FF00", # Green
    4: "#00FFFF", # Cyan
    5: "#0000FF", # Blue
    6: "#FF00FF", # Magenta
    7: "#000000", # Black/White
    8: "#808080", # Gray
    9: "#C0C0C0", # Light Gray
}

def render_preview(ir_data: Dict[str, Any], output_prefix: str):
    views = ir_data.get("views", [])
    
    fig, ax = plt.subplots(figsize=(12, 12))
    
    for view in views:
        entities = view.get("entities", [])
        
        # Build layer to color map
        layer_colors = {}
        for layer in view.get("layers", []):
            color_idx = layer.get("color", 7)
            layer_colors[layer["name"]] = ACI_COLORS.get(color_idx, "#000000")
            
        for ent in entities:
            ent_type = ent.get("type")
            pts = ent.get("points", [])
            
            # Determine color from entity or layer
            ent_color_idx = ent.get("color")
            layer_name = ent.get("layer", "")
            if ent_color_idx is not None:
                edgecolor = ACI_COLORS.get(ent_color_idx, "#000000")
            else:
                edgecolor = layer_colors.get(layer_name, "#000000")
                
            if ent_type == "polygon" and pts:
                # Facecolor is a highly transparent version of edgecolor for rich formatting
                facecolor = edgecolor + "1A" # 10% opacity
                
                closed = ent.get("closed", True)
                
                # Matplotlib requires strictly 2D points (x, y). 
                # If a 3D point (x, y, z) is passed, we slice off the Z axis to plot a top-down view.
                pts_2d = [p[:2] for p in pts]
                
                poly = patches.Polygon(pts_2d, closed=closed, facecolor=facecolor, edgecolor=edgecolor, linewidth=2.0)
                ax.add_patch(poly)
                
                # Auto Dimensioning Drawing logic
                if ent.get("auto_dimension", False) and len(pts) >= 2:
                    n = len(pts) if closed else len(pts) - 1
                    for i in range(n):
                        p1 = pts[i]
                        p2 = pts[(i+1) % len(pts)]
                        if p1 == p2:
                            continue
                            
                        dx = p2[0] - p1[0]
                        dy = p2[1] - p1[1]
                        length = math.hypot(dx, dy)
                        
                        if length < 0.1:
                            continue
                            
                        # Normal vector for offset
                        nx = -dy / length
                        ny = dx / length
                        
                        # Hardcoded offset for display
                        offset = 1.0
                        cx = (p1[0] + p2[0]) / 2 + nx * offset
                        cy = (p1[1] + p2[1]) / 2 + ny * offset
                        
                        # Draw dimension text
                        angle_deg = math.degrees(math.atan2(dy, dx))
                        # Keep text upright
                        if angle_deg > 90:
                            angle_deg -= 180
                        elif angle_deg < -90:
                            angle_deg += 180
                            
                        from .dimensioning import format_feet_inches
                        dim_text = format_feet_inches(length)
                            
                        ax.text(cx, cy, dim_text, ha='center', va='center', 
                                fontsize=8, color=edgecolor, rotation=angle_deg,
                                bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=0.5))
                        
                        # Draw dimension lines (simplified for plot)
                        ax.plot([p1[0] + nx*offset, p2[0] + nx*offset], [p1[1] + ny*offset, p2[1] + ny*offset], 
                                color=edgecolor, linewidth=0.5, linestyle='--')
                
            elif ent_type == "label":
                pos = ent.get("position", [0, 0])
                rotation = ent.get("rotation", 0.0)
                ax.text(pos[0], pos[1], ent.get("text", ""), ha='center', va='center', 
                        fontsize=10, fontweight='bold', color=edgecolor, rotation=rotation,
                        bbox=dict(facecolor='white', edgecolor=edgecolor, alpha=0.8, pad=2.0))
                
    ax.autoscale_view()
    ax.set_aspect('equal')
    plt.axis('off')
    
    out_path = f"{output_prefix}_preview.png"
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
