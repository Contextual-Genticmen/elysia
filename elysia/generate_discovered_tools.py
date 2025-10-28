#!/usr/bin/env python3
"""
Generate discovered_tools.yaml - Script to generate tool discovery configuration.
Run this after adding new tools to update the discovery YAML.
"""
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from elysia.util.tool_discovery import generate_tool_discovery_yaml

try:
    output_path = Path(__file__).parent / "config" / "discovered_tools.yaml"
    
    print(f"Generating tool discovery YAML at: {output_path}")
    yaml_content = generate_tool_discovery_yaml(output_path)
    print("✓ Successfully generated discovered_tools.yaml")
    print(f"\nDiscovered tools:")
    print(yaml_content)
    
except Exception as e:
    print(f"Error generating tool discovery YAML: {e}")
    sys.exit(1)

