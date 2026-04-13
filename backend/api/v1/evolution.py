from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from backend.evolution import self_monitor, failure_analyzer, success_learner, parameter_optimizer, algorithm_mutator, strategy_mutator, discovery_engine
from backend.evaluation.benchmarks import LEVIBenchmarkSuite
from backend.evaluation.cost_analysis import analyzer as cost_analyzer
from backend.auth import get_current_user

from backend.evolution.impact import impact_tracker

router = APIRouter(tags=["Evolution"])

@router.get("/metrics")
async def get_evolution_metrics(current_user=Depends(get_current_user)):
    """Retrieve cumulative self-monitoring stats."""
    return self_monitor.get_summary_stats()

@router.get("/impact")
async def get_impact_report(current_user=Depends(get_current_user)):
    """Retrieve quantifiable world impact metrics (Phase 3)."""
    econ = await impact_tracker.get_economic_impact()
    sci = await impact_tracker.get_scientific_contribution()
    demo = await impact_tracker.get_democratization_stats()
    return {
        "economic": econ,
        "scientific": sci,
        "democratization": demo
    }

@router.get("/patterns/success")
async def get_success_patterns(current_user=Depends(get_current_user)):
    """Retrieve learned high-fidelity mission patterns."""
    return success_learner.pattern_store

@router.post("/benchmark/run")
async def run_benchmarks(current_user=Depends(get_current_user)):
    """Trigger a full comparative benchmarking suite."""
    suite = LEVIBenchmarkSuite()
    return await suite.run_full_suite()

@router.get("/mutations")
async def get_mutation_proposals(current_user=Depends(get_current_user)):
    """Get algorithm and strategy mutations proposed by the system."""
    algo = await algorithm_mutator.propose_mutation()
    strat = strategy_mutator.discover_archetypes()
    return {
        "algorithm_mutations": [algo],
        "strategy_innovations": strat
    }

@router.get("/roi")
async def get_roi_report(current_user=Depends(get_current_user)):
    """Generate an ROI and TCO report based on system data."""
    # Placeholder metrics for demonstration
    metrics = {"infra_annual": 1200.0, "dev_hours_annual": 500.0}
    return cost_analyzer.calculate_tco(metrics)
