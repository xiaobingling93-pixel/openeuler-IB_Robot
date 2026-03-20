#!/usr/bin/env python3
"""
JSON Field Migration Script

Migrates JSON files from camelCase to snake_case field names.

Usage:
    python3 migrate_json_fields.py <input.json> [output.json]

If output is not specified, overwrites the input file.
"""

import sys
import json
from pathlib import Path

FIELD_MAPPINGS = {
    "contextCode": "context_code",
    "fixCode": "fix_code",
    "fixExplanation": "fix_explanation",
    "filePath": "file_path",
    "deleteLines": "delete_lines",
    "fixDescription": "fix_description",
    "originalCode": "original_code",
    "fixedCode": "fixed_code",
}


def migrate_dict(data: dict) -> dict:
    """Recursively migrate dictionary keys from camelCase to snake_case"""
    if not isinstance(data, dict):
        return data

    result = {}
    for key, value in data.items():
        # Migrate key
        new_key = FIELD_MAPPINGS.get(key, key)

        # Recursively migrate value
        if isinstance(value, dict):
            new_value = migrate_dict(value)
        elif isinstance(value, list):
            new_value = [
                migrate_dict(item) if isinstance(item, dict) else item for item in value
            ]
        else:
            new_value = value

        result[new_key] = new_value

    return result


def migrate_json_file(input_path: str, output_path: str = None):
    """Migrate JSON file"""
    input_file = Path(input_path)

    if not input_file.exists():
        print(f"❌ Error: File not found: {input_path}")
        sys.exit(1)

    # Read input
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Migrate
    migrated_data = migrate_dict(data)

    # Determine output path
    if output_path is None:
        output_path = input_path

    # Write output
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(migrated_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Migrated: {input_path} → {output_path}")

    # Show changes
    changes = []
    for old_key, new_key in FIELD_MAPPINGS.items():
        if old_key in str(data):
            changes.append(f"  {old_key} → {new_key}")

    if changes:
        print("Changes:")
        for change in changes:
            print(change)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExample:")
        print("  python3 migrate_json_fields.py issues.json")
        print("  python3 migrate_json_fields.py issues.json issues_migrated.json")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    migrate_json_file(input_path, output_path)


if __name__ == "__main__":
    main()
