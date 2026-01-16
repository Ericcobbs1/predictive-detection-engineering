#!/usr/bin/env python3
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "detection.schema.json"
DETECTIONS_DIR = REPO_ROOT / "detections"

def load_schema():
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def find_detection_files():
    if not DETECTIONS_DIR.exists():
        return []
    return sorted(list(DETECTIONS_DIR.rglob("*.yml")) + list(DETECTIONS_DIR.rglob("*.yaml")))

def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    if not SCHEMA_PATH.exists():
        print(f"ERROR: Schema not found: {SCHEMA_PATH}")
        return 2

    schema = load_schema()
    validator = Draft202012Validator(schema)

    files = find_detection_files()
    if not files:
        print("No detection YAML files found under detections/.")
        return 0

    errors_found = 0
    for fp in files:
        try:
            doc = load_yaml(fp)
        except Exception as e:
            errors_found += 1
            print(f"\n❌ YAML parse error: {fp}\n  {e}")
            continue

        # Basic sanity
        if not isinstance(doc, dict):
            errors_found += 1
            print(f"\n❌ Invalid YAML root (expected mapping/object): {fp}")
            continue

        # Schema validation
        schema_errors = sorted(validator.iter_errors(doc), key=lambda e: e.path)
        if schema_errors:
            errors_found += len(schema_errors)
            print(f"\n❌ Schema errors in: {fp}")
            for e in schema_errors[:50]:
                loc = ".".join([str(p) for p in e.path]) if e.path else "<root>"
                print(f"  - {loc}: {e.message}")
            if len(schema_errors) > 50:
                print(f"  ... {len(schema_errors)-50} more errors")
        else:
            print(f"✅ {fp.relative_to(REPO_ROOT)}")

    if errors_found:
        print(f"\nValidation failed with {errors_found} issue(s).")
        return 1

    print("\nAll detection YAML files validated successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
