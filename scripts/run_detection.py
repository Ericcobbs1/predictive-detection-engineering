from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

import yaml

from src.renderers.splunk_spl import SplunkSPLRenderer


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Detection file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("Detection YAML must parse to a dictionary/object.")
    return data


def validate_minimum_detection_fields(det: Dict[str, Any]) -> None:
    """
    Lightweight validation (schema validation can be added later with jsonschema).
    This ensures we don't run with missing critical fields.
    """
    required_top = ["id", "title", "type", "entity", "windows", "features", "conditions", "outputs"]
    missing = [k for k in required_top if k not in det]
    if missing:
        raise ValueError(f"Detection YAML missing required fields: {missing}")

    if not isinstance(det.get("entity"), dict) or "type" not in det["entity"] or "field" not in det["entity"]:
        raise ValueError("Detection YAML 'entity' must include 'type' and 'field'.")

    if not isinstance(det.get("windows"), dict) or not all(k in det["windows"] for k in ["baseline", "observation", "bucket"]):
        raise ValueError("Detection YAML 'windows' must include baseline, observation, bucket.")

    if det.get("id") != "NS-P2-001":
        raise ValueError("Runner currently supports only NS-P2-001 (MVP).")

    if det.get("type") != "predictive":
        raise ValueError("NS-P2-001 must have type: predictive.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NextSigma detection artifacts (MVP runner).")
    parser.add_argument(
        "--detection",
        required=True,
        help="Path to detection YAML (e.g., detections/p2/ns-p2-001-lateral-fanout.yml)",
    )
    parser.add_argument("--index", default=None, help="Splunk index (optional). If omitted, SPL will not include index=")

    # Optional tunables
    parser.add_argument("--earliest-baseline", default="-30d@d", help="Baseline earliest (default: -30d@d)")
    parser.add_argument("--earliest-obs", default="-72h@h", help="Observation earliest (default: -72h@h)")
    parser.add_argument("--bucket-span", default="1h", help="Bucket span (default: 1h)")
    parser.add_argument("--deviation-ratio", type=float, default=2.5, help="Deviation ratio threshold (default: 2.5)")
    parser.add_argument("--min-new-targets", type=int, default=3, help="Min new targets threshold (default: 3)")
    parser.add_argument("--sustained-buckets", type=int, default=3, help="Sustained growth buckets (default: 3)")

    args = parser.parse_args()

    det = load_yaml(Path(args.detection))
    validate_minimum_detection_fields(det)

    renderer = SplunkSPLRenderer()
    result = renderer.render_ns_p2_001(
        detection=det,
        params={
            "index": args.index,
            "earliest_baseline": args.earliest_baseline,
            "earliest_obs": args.earliest_obs,
            "bucket_span": args.bucket_span,
            "deviation_ratio": args.deviation_ratio,
            "min_new_targets": args.min_new_targets,
            "sustained_buckets": args.sustained_buckets,
        },
    )

    print("\n=== Detection ===\n")
    print(f"ID: {det.get('id')}")
    print(f"Title: {det.get('title')}")
    print(f"Type: {det.get('type')}")
    print(f"Entity: {det.get('entity', {}).get('type')} (field={det.get('entity', {}).get('field')})")
    print(f"Windows: baseline={det.get('windows', {}).get('baseline')} obs={det.get('windows', {}).get('observation')} bucket={det.get('windows', {}).get('bucket')}")

    print("\n=== Generated SPL ===\n")
    print(result.search)

    print("\n=== Notes ===\n")
    print(result.notes)


if __name__ == "__main__":
    main()
