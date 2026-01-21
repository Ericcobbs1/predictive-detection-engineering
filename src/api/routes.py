from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

from src.baselines.rolling import compute_host_baseline_stats, apply_baseline_to_observation
from src.engine.evaluator import evaluate_ns_p2_001
from src.engine.evaluator_auth import compute_auth_baseline_stats, evaluate_pde_spl_0402
from src.engine.evaluator_persistence import compute_persistence_baseline_stats, evaluate_pde_spl_0403
from src.engine.evaluator_staging import compute_staging_baseline_stats, evaluate_pde_spl_0404
from src.engine.evaluator_admin_tooling import compute_admin_tooling_baseline_stats, evaluate_pde_spl_0405

from src.features.network_fanout import FanoutBucketFeatures
from src.features.auth_drift import AuthBucketFeatures
from src.features.persistence_drift import PersistenceBucketFeatures
from src.features.data_staging_drift import StagingBucketFeatures
from src.features.admin_tooling_drift import AdminToolingBucketFeatures


router = APIRouter(prefix="/evaluate", tags=["evaluate"])


# ------------------------
# Shared request models
# ------------------------

class EvalParams(BaseModel):
    drift_ratio_threshold: float = 2.5
    sustained_buckets: int = 3
    min_unique: int = 2
    min_baseline_buckets: int = 24
    expected_baseline_buckets: int = 30 * 24  # default for 1h buckets


# ------------------------
# 0401 Fan-out drift
# ------------------------

class Eval0401Request(BaseModel):
    baseline: List[FanoutBucketFeatures] = Field(default_factory=list)
    observation: List[FanoutBucketFeatures] = Field(default_factory=list)
    deviation_ratio_threshold: float = 2.5
    sustained_buckets: int = 3
    min_new_targets: int = 3
    expected_baseline_buckets: int = 30 * 24


@router.post("/0401")
def eval_0401(req: Eval0401Request) -> dict:
    baselines = compute_host_baseline_stats(req.baseline)
    obs_with_ratio = apply_baseline_to_observation(req.observation, baselines, min_baseline_buckets=1)

    signals = evaluate_ns_p2_001(
        obs_with_ratio,
        baselines,
        deviation_ratio_threshold=req.deviation_ratio_threshold,
        sustained_buckets=req.sustained_buckets,
        min_new_targets=req.min_new_targets,
        expected_baseline_buckets=req.expected_baseline_buckets,
    )
    return {"count": len(signals), "signals": [s.__dict__ for s in signals]}


# ------------------------
# 0402 Password spray drift
# ------------------------

class Eval0402Request(BaseModel):
    baseline: List[AuthBucketFeatures] = Field(default_factory=list)
    observation: List[AuthBucketFeatures] = Field(default_factory=list)
    drift_ratio_threshold: float = 2.5
    sustained_buckets: int = 3
    min_users: int = 10
    expected_baseline_buckets: int = 30 * 24 * 4  # 30d @ 15m
    min_baseline_buckets: int = 24


@router.post("/0402")
def eval_0402(req: Eval0402Request) -> dict:
    baselines = compute_auth_baseline_stats(req.baseline)
    signals = evaluate_pde_spl_0402(
        req.observation,
        baselines,
        drift_ratio_threshold=req.drift_ratio_threshold,
        sustained_buckets=req.sustained_buckets,
        min_users=req.min_users,
        expected_baseline_buckets=req.expected_baseline_buckets,
        min_baseline_buckets=req.min_baseline_buckets,
    )
    return {"count": len(signals), "signals": [s.__dict__ for s in signals]}


# ------------------------
# 0403 Persistence drift
# ------------------------

class Eval0403Request(BaseModel):
    baseline: List[PersistenceBucketFeatures] = Field(default_factory=list)
    observation: List[PersistenceBucketFeatures] = Field(default_factory=list)
    drift_ratio_threshold: float = 2.5
    sustained_buckets: int = 3
    min_unique_artifacts: int = 2
    expected_baseline_buckets: int = 30 * 24
    min_baseline_buckets: int = 24


@router.post("/0403")
def eval_0403(req: Eval0403Request) -> dict:
    baselines = compute_persistence_baseline_stats(req.baseline)
    signals = evaluate_pde_spl_0403(
        req.observation,
        baselines,
        drift_ratio_threshold=req.drift_ratio_threshold,
        sustained_buckets=req.sustained_buckets,
        min_unique_artifacts=req.min_unique_artifacts,
        expected_baseline_buckets=req.expected_baseline_buckets,
        min_baseline_buckets=req.min_baseline_buckets,
    )
    return {"count": len(signals), "signals": [s.__dict__ for s in signals]}


# ------------------------
# 0404 Data staging drift
# ------------------------

class Eval0404Request(BaseModel):
    baseline: List[StagingBucketFeatures] = Field(default_factory=list)
    observation: List[StagingBucketFeatures] = Field(default_factory=list)
    drift_ratio_threshold: float = 2.5
    sustained_buckets: int = 3
    min_unique_artifacts: int = 2
    expected_baseline_buckets: int = 30 * 24
    min_baseline_buckets: int = 24


@router.post("/0404")
def eval_0404(req: Eval0404Request) -> dict:
    baselines = compute_staging_baseline_stats(req.baseline)
    signals = evaluate_pde_spl_0404(
        req.observation,
        baselines,
        drift_ratio_threshold=req.drift_ratio_threshold,
        sustained_buckets=req.sustained_buckets,
        min_unique_artifacts=req.min_unique_artifacts,
        expected_baseline_buckets=req.expected_baseline_buckets,
        min_baseline_buckets=req.min_baseline_buckets,
    )
    return {"count": len(signals), "signals": [s.__dict__ for s in signals]}


# ------------------------
# 0405 Admin tooling drift
# ------------------------

class Eval0405Request(BaseModel):
    baseline: List[AdminToolingBucketFeatures] = Field(default_factory=list)
    observation: List[AdminToolingBucketFeatures] = Field(default_factory=list)
    drift_ratio_threshold: float = 2.5
    sustained_buckets: int = 3
    min_unique_tools: int = 2
    expected_baseline_buckets: int = 30 * 24
    min_baseline_buckets: int = 24


@router.post("/0405")
def eval_0405(req: Eval0405Request) -> dict:
    baselines = compute_admin_tooling_baseline_stats(req.baseline)
    signals = evaluate_pde_spl_0405(
        req.observation,
        baselines,
        drift_ratio_threshold=req.drift_ratio_threshold,
        sustained_buckets=req.sustained_buckets,
        min_unique_tools=req.min_unique_tools,
        expected_baseline_buckets=req.expected_baseline_buckets,
        min_baseline_buckets=req.min_baseline_buckets,
    )
    return {"count": len(signals), "signals": [s.__dict__ for s in signals]}
