# backend/api/v1/registry.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
from backend.services.model_registry import model_registry, ModelMetadata
from backend.services.dataset_manager import dataset_manager
from backend.core.evolution.training_pipeline import training_pipeline
from backend.core.evolution.benchmark_engine import benchmark_engine
from backend.auth import get_current_user

router = APIRouter(tags=["Sovereign Graduation"])

@router.get("/models")
async def list_models(current_user = Depends(get_current_user)):
    """Lists all registered models and their versions."""
    return model_registry.manifest

@router.post("/evolution/trigger")
async def trigger_evolution(model_id: str, dataset_name: str, current_user = Depends(get_current_user)):
    """Triggers an autonomous evolution cycle."""
    if training_pipeline.is_running:
        raise HTTPException(status_code=400, detail="Evolution cycle already in progress")
    
    # Run in background
    import asyncio
    asyncio.create_task(training_pipeline.run_evolution_cycle(model_id, dataset_name))
    return {"message": f"Evolution cycle triggered for {model_id}"}

@router.get("/benchmark/{model_id}/{version}")
async def run_benchmark(model_id: str, version: str, current_user = Depends(get_current_user)):
    """Runs a deterministic fidelity benchmark on a specific model version."""
    results = await benchmark_engine.evaluate_model(model_id, version)
    return results

@router.post("/datasets/checkpoint")
async def checkpoint_dataset(name: str, path: str, current_user = Depends(get_current_user)):
    """Creates a versioned checkpoint of a dataset."""
    dataset_manager.checkpoint_current_data(name, path)
    return {"message": f"Dataset {name} checkpointed"}
