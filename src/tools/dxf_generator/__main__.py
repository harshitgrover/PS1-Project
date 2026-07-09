import argparse
import os
from .dxf_generator import generate_dxf

def main():
    parser = argparse.ArgumentParser(description="DXF Generator")
    parser.add_argument("input_jsons", nargs='+', help="Path to one or more input JSON files")
    parser.add_argument("output_dxf", help="Path to output DXF file")
    parser.add_argument("--render", action="store_true", help="Generate matplotlib preview images")
    parser.add_argument("--img-prefix", default="", help="Prefix for rendered images")
    
    args = parser.parse_args()
    
    out_dxf = args.output_dxf
    img_prefix = args.img_prefix
    
    # If the user just specified a filename, route it to demo_outputs
    base_dir = os.path.dirname(os.path.abspath(__file__))
    gen_dir = os.path.join(base_dir, "demo_outputs")
    
    # If the user just specified a filename, route it to demo_outputs
    if not os.path.dirname(out_dxf):
        os.makedirs(gen_dir, exist_ok=True)
        out_dxf = os.path.join(gen_dir, out_dxf)
        
    # If they specified a custom image prefix without a path, route it as well
    if img_prefix and not os.path.dirname(img_prefix):
        os.makedirs(gen_dir, exist_ok=True)
        img_prefix = os.path.join(gen_dir, img_prefix)
        
    generate_dxf(args.input_jsons, out_dxf, args.render, img_prefix)

if __name__ == "__main__":
    main()
