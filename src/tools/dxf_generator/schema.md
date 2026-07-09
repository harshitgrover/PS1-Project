<!-- NOTE: This file ONLY mentions the specific required inputs and outputs for this agent's `Properties` payload. For the generic envelope structure (session_id, file_refs, status), see input_output.txt. -->

# DXF Generator Schema

## Expected Input
The DXF Generator expects to receive the final generated geometric layout from the Layout Agent.

```json
"Properties": {
  // Required: The geometric definition of the floor plan
  "layout_output": {
    "job_id": "string (unique identifier for the layout job)",
    
    // The outer shell polygon of the building
    "boundary": [ 
      [ "number (x)", "number (y)" ], 
      [ "number (x)", "number (y)" ],
      "..."
    ],
    
    // The individual rooms instantiated within the building
    "rooms": [
      {
        "name": "string (e.g., 'bedroom_1')",
        "type": "string (e.g., 'bedroom')",
        "polygon": [
          [ "number (x)", "number (y)" ],
          "..."
        ],
        "area": "number (optional, square feet)"
      }
    ],
    
    // Optional architectural elements
    "doors": [
      {
        "rooms": ["string", "string"], // The two rooms this door connects
        "center": ["number (x)", "number (y)"],
        "orientation": "string ('vertical' or 'horizontal')",
        "polygon": [ ["number (x)", "number (y)"] ]
      }
    ],
    
    "windows": [
      {
        "room": "string (The room this window belongs to)",
        "center": ["number (x)", "number (y)"],
        "orientation": "string ('vertical' or 'horizontal')",
        "polygon": [ ["number (x)", "number (y)"] ]
      }
    ]
  },
  
  // Optional: Tell the generator to also produce a visual PNG preview
  "render_preview": "boolean (Defaults to false)"
}
```

## Output Provided
The DXF Generator does not return a JSON schema body. Instead, it generates a `.dxf` file (and optionally a `.png` file) and returns the standard S3 Bucket paths for other agents to download.

```json
"Properties": {}
// Note: You must retrieve the uploaded files from the outer `file_refs` envelope.
// "file_refs": [
//   { "type": "dxf", "bucket": "shared-bucket-name", "key": "dxf_generator/session_id/1_output.dxf" },
//   { "type": "png", "bucket": "shared-bucket-name", "key": "dxf_generator/session_id/1_preview.png" }
// ]
```
