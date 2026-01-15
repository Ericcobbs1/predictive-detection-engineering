# How to Apply Predictive Readiness Classification

## When
Apply during ingestion and inventory creation for each source.

## What to store per detection inventory record
- predictive_readiness (label)
- predictive_readiness_score (integer)
- predictive_readiness_factors (list of rule ids that fired)

## Where
- Inventory records: `inventory/detections.<source>.yml` (or CSV later)
- Converted detections: `detections/splunk/<reactive|predictive_adjacent|predictive>/...`
