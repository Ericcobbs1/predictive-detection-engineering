#!/usr/bin/env python3
import re
import sys
import json
from pathlib import Path
from datetime import datetime

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SIGMA_ROOT = REPO_ROOT / "external" / "sigma"
CLASSIFIER_PATH = REPO_ROOT / "classifier" / "predictive_readiness_rules.yml"
OUT_PATH = REPO_ROOT / "inventory" / "detections.sigma.index.yml"

SIGMA_RULE_DIR_GLOB = "rules*"
SIGMA_YAML_EXTS = (".yml", ".yaml")

TECHNIQUE_RE = re.compile(r"^attack\.(t\d{4}(?:\.\d{3})?)$", re.IGNORECASE)
TACTIC_RE = re.compile(r"^attack\.([a-z_]+)$", re.IGNORECASE)

def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def safe_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]

def normalize_text(*parts) -> str:
    joined = " ".join([p for p in parts if isinstance(p, str) and p.strip()])
    return joined.lower()

def stringify_detection_block(det) -> str:
    try:
        return json.dumps(det, ensure_ascii=False, sort_keys=True).lower()
    except Exception:
        return str(det).lower()

def load_classifier():
    doc = load_yaml(CLASSIFIER_PATH)
    return doc["classifier"]

def apply_classifier(rule_text: str, rule_tags: list, classifier: dict):
    score = 0
    fired = []

    tags_text = " ".join([str(t).lower() for t in safe_list(rule_tags)])

    for r in classifier.get("rules", []):
        pts = int(r.get("points", 0))
        evidence = r.get("evidence", {}) or {}
        keywords = [k.lower() for k in evidence.get("keywords", [])]

        hit = False
        for kw in keywords:
            if kw and (kw in rule_text or kw in tags_text):
                hit = True
                break

        if hit:
            score += pts
            fired.append(r.get("id", "unknown_rule"))

    # Guardrails (best-effort)
    guardrails = classifier.get("guardrails", [])
    for g in guardrails:
        if g.get("id") == "ioc_only_cap":
            kw_list = [k.lower() for k in (g.get("evidence", {}) or {}).get("keywords", [])]
            ioc_hit = any(kw in rule_text or kw in tags_text for kw in kw_list)
            if ioc_hit and score <= 3:
                fired.append("guardrail:ioc_only_cap")

    # Score to label
    labels = classifier.get("labels", {})
    label = "reactive_only"
    for name, bounds in labels.items():
        min_s = int(bounds.get("min_score", 0))
        max_s = int(bounds.get("max_score", 999999))
        if min_s <= score <= max_s:
            label = name
            break

    return score, label, fired

def extract_mitre_from_sigma_tags(tags):
    tactics = []
    techniques = []
    for t in safe_list(tags):
        if not isinstance(t, str):
            continue
        s = t.strip().lower()

        m = TECHNIQUE_RE.match(s)
        if m:
            techniques.append(m.group(1).upper())
            continue

        m2 = TACTIC_RE.match(s)
        if m2:
            val = m2.group(1)
            if val.startswith("t") and any(ch.isdigit() for ch in val):
                continue
            tactics.append(val.replace("_", " ").title())

    return sorted(set(tactics)), sorted(set(techniques))

def discover_sigma_rule_files():
    if not SIGMA_ROOT.exists():
        print(f"ERROR: Sigma submodule not found at {SIGMA_ROOT}")
        print("Fix: git submodule update --init --recursive")
        return []

    rule_files = []
    for d in SIGMA_ROOT.glob(SIGMA_RULE_DIR_GLOB):
        if d.is_dir():
            for fp in d.rglob("*"):
                if fp.is_file() and fp.suffix.lower() in SIGMA_YAML_EXTS:
                    rule_files.append(fp)
    return sorted(rule_files)

def build_inventory_record(fp: Path, doc: dict, classifier: dict):
    rid = doc.get("id", "") or ""
    title = doc.get("title", "") or ""
    desc = doc.get("description", "") or ""
    status = doc.get("status", "") or ""
    level = doc.get("level", "") or ""
    tags = safe_list(doc.get("tags"))
    refs = safe_list(doc.get("references"))
    falsepos = safe_list(doc.get("falsepositives"))
    logsource = doc.get("logsource", {}) or {}

    detection_block = doc.get("detection", {}) or {}
    condition = detection_block.get("condition", "")
    detection_str = stringify_detection_block(detection_block)

    combined = normalize_text(
        title, desc, status, level, str(logsource), str(condition), detection_str, " ".join([str(t) for t in tags])
    )

    score, label, factors = apply_classifier(combined, tags, classifier)
    tactics, techniques = extract_mitre_from_sigma_tags(tags)

    sev_map = {
        "informational": "informational",
        "low": "low",
        "medium": "medium",
        "high": "high",
        "critical": "critical"
    }
    severity = sev_map.get(str(level).lower(), "medium")

    platform = str(logsource.get("product") or logsource.get("platform") or "").lower()
    product = str(logsource.get("service") or logsource.get("product") or "").lower()
    category = str(logsource.get("category") or "").lower()

    rel_path = fp.relative_to(REPO_ROOT).as_posix()

    return {
        "detection_id": rid if rid else f"SIGMA:{fp.stem}",
        "source_id": "sigmahq_sigma",
        "source_rule_path": rel_path,
        "name": title if title else fp.stem,
        "description": desc,
        "query_language": "sigma",
        "detection_type": "reactive",
        "predictive_readiness": label,
        "predictive_readiness_score": score,
        "predictive_readiness_factors": factors,
        "severity": severity,
        "status": status if status else "unknown",
        "platform": platform,
        "product": product,
        "category": category,
        "data_sources": [],
        "tactics": tactics,
        "techniques": techniques,
        "tags": tags,
        "time_window": "",
        "references": refs,
        "false_positives": falsepos,
        "notes": ""
    }

def main():
    if not CLASSIFIER_PATH.exists():
        print(f"ERROR: Classifier rules not found: {CLASSIFIER_PATH}")
        return 2

    classifier = load_classifier()
    files = discover_sigma_rule_files()
    if not files:
        print("No Sigma rule files discovered.")
        return 2

    records = []
    skipped = 0

    for fp in files:
        try:
            doc = load_yaml(fp)
            if not isinstance(doc, dict):
                skipped += 1
                continue
        except Exception:
            skipped += 1
            continue

        if not doc.get("title") and not doc.get("detection"):
            skipped += 1
            continue

        records.append(build_inventory_record(fp, doc, classifier))

    out = {
        "source_id": "sigmahq_sigma",
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts": {
            "total_rules_discovered": len(files),
            "records_written": len(records),
            "skipped": skipped
        },
        "records": records
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(out, f, sort_keys=False, allow_unicode=True)

    label_counts = {}
    for r in records:
        label_counts[r["predictive_readiness"]] = label_counts.get(r["predictive_readiness"], 0) + 1

    print(f"Wrote: {OUT_PATH}")
    print(f"Rules discovered: {len(files)} | Records: {len(records)} | Skipped: {skipped}")
    print("Predictive readiness distribution:")
    for k in sorted(label_counts.keys()):
        print(f"  - {k}: {label_counts[k]}")

    top = sorted(records, key=lambda x: x.get("predictive_readiness_score", 0), reverse=True)[:25]
    print("\nTop 25 Sigma candidates by readiness score:")
    for r in top:
        print(f"  {r['predictive_readiness_score']:>2}  {r['predictive_readiness']:<18}  {r['detection_id']}  {r['name']}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
