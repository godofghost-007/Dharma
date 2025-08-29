"""API endpoints for model governance and lifecycle management."""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field
from datetime import datetime

from ..core.model_governance_service import get_governance_service, ModelGovernanceService
from ..core.model_registry import ModelType, ModelStatus, ModelMetrics
from ..models.requests import BaseRequest

router = APIRouter(prefix="/governance", tags=["Model Governance"])


class ModelRegistrationRequest(BaseModel):
    """Request model for registering a new model."""
    model_type: str = Field(..., description="Type of model (sentiment_analysis, bot_detection, etc.)")
    model_path: str = Field(..., description="Path to model file")
    config_path: str = Field(..., description="Path to model configuration file")
    metrics: Dict[str, float] = Field(..., description="Model performance metrics")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    tags: Optional[List[str]] = Field(None, description="Model tags")
    description: str = Field("", description="Model description")


class ABTestRequest(BaseModel):
    """Request model for creating A/B test."""
    model_a_version: str = Field(..., description="Version ID of model A")
    model_b_version: str = Field(..., description="Version ID of model B")
    traffic_split: Optional[float] = Field(0.1, description="Traffic percentage for model B (0.0-1.0)")
    duration_hours: Optional[int] = Field(24, description="Test duration in hours")


class ModelPromotionRequest(BaseModel):
    """Request model for promoting a model."""
    version_id: str = Field(..., description="Model version ID to promote")
    skip_ab_test: bool = Field(False, description="Skip A/B testing and promote directly")


class MonitoringSetupRequest(BaseModel):
    """Request model for setting up model monitoring."""
    model_version: str = Field(..., description="Model version ID")
    feature_importance: Dict[str, float] = Field(..., description="Feature importance weights")


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_governance_dashboard(
    governance_service: ModelGovernanceService = Depends(get_governance_service)
):
    """Get governance dashboard data with model statistics and monitoring info."""
    try:
        dashboard_data = await governance_service.get_governance_dashboard()
        return dashboard_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard data: {str(e)}")


@router.get("/models", response_model=List[Dict[str, Any]])
async def list_models(
    model_type: Optional[str] = Query(None, description="Filter by model type"),
    status: Optional[str] = Query(None, description="Filter by model status"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    governance_service: ModelGovernanceService = Depends(get_governance_service)
):
    """List models with optional filtering."""
    try:
        # Parse parameters
        model_type_enum = ModelType(model_type) if model_type else None
        status_enum = ModelStatus(status) if status else None
        tags_list = tags.split(",") if tags else None
        
        models = await governance_service.list_models(
            model_type=model_type_enum,
            status=status_enum,
            tags=tags_list
        )
        
        return models
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


@router.post("/models/register", response_model=Dict[str, str])
async def register_model(
    request: ModelRegistrationRequest,
    governance_service: ModelGovernanceService = Depends(get_governance_service)
):
    """Register a new model version."""
    try:
        # Convert metrics dict to ModelMetrics object
        metrics = ModelMetrics(
            accuracy=request.metrics.get("accuracy", 0.0),
            precision=request.metrics.get("precision", 0.0),
            recall=request.metrics.get("recall", 0.0),
            f1_score=request.metrics.get("f1_score", 0.0),
            auc_roc=request.metrics.get("auc_roc"),
            confusion_matrix=request.metrics.get("confusion_matrix"),
            custom_metrics=request.metrics.get("custom_metrics")
        )
        
        # For now, use dummy training data - in real implementation this would come from the request
        import numpy as np
        dummy_training_data = np.random.rand(100, 10)
        
        version_id = await governance_service.register_new_model(
            model_type=ModelType(request.model_type),
            model_path=request.model_path,
            config_path=request.config_path,
            metrics=metrics,
            training_data=dummy_training_data,
            metadata=request.metadata,
            tags=request.tags,
            description=request.description
        )
        
        return {"version_id": version_id, "status": "registered"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid model type: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register model: {str(e)}")


@router.post("/models/promote", response_model=Dict[str, Any])
async def promote_model(
    request: ModelPromotionRequest,
    governance_service: ModelGovernanceService = Depends(get_governance_service)
):
    """Promote model to production with optional A/B testing."""
    try:
        success = await governance_service.promote_model_to_production(
            version_id=request.version_id,
            skip_ab_test=request.skip_ab_test
        )
        
        return {
            "success": success,
            "version_id": request.version_id,
            "ab_test_created": success and not request.skip_ab_test
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to promote model: {str(e)}")


@router.post("/models/{model_type}/rollback", response_model=Dict[str, Any])
async def rollback_model(
    model_type: str,
    governance_service: ModelGovernanceService = Depends(get_governance_service)
):
    """Rollback to previous production model."""
    try:
        model_type_enum = ModelType(model_type)
        success = await governance_service.rollback_model(model_type_enum)
        
        return {
            "success": success,
            "model_type": model_type,
            "message": "Rolled back to previous production model" if success else "Rollback failed"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid model type: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rollback model: {str(e)}")


@router.get("/models/{version_id}/validate", response_model=Dict[str, Any])
async def validate_model(
    version_id: str,
    governance_service: ModelGovernanceService = Depends(get_governance_service)
):
    """Validate model for production deployment."""
    try:
        validation_result = await governance_service.validate_model_for_production(version_id)
        return validation_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate model: {str(e)}")


@router.get("/models/{version_id}/performance", response_model=Dict[str, Any])
async def get_model_performance(
    version_id: str,
    days: int = Query(7, description="Number of days to include in summary"),
    governance_service: ModelGovernanceService = Depends(get_governance_service)
):
    """Get model performance summary."""
    try:
        performance_summary = await governance_service.get_model_performance_summary(
            model_version=version_id,
            days=days
        )
        
        return {
            "version_id": version_id,
            "days": days,
            "summary": performance_summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance summary: {str(e)}")


@router.post("/models/{version_id}/monitoring", response_model=Dict[str, str])
async def setup_model_monitoring(
    version_id: str,
    request: MonitoringSetupRequest,
    governance_service: ModelGovernanceService = Depends(get_governance_service)
):
    """Setup drift detection and monitoring for a model."""
    try:
        # For now, use dummy reference data - in real implementation this would be provided
        import numpy as np
        dummy_reference_data = np.random.rand(1000, len(request.feature_importance))
        
        await governance_service.setup_model_monitoring(
            model_version=version_id,
            reference_data=dummy_reference_data,
            feature_importance=request.feature_importance
        )
        
        return {
            "status": "monitoring_setup",
            "version_id": version_id,
            "message": "Drift detection and monitoring configured"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to setup monitoring: {str(e)}")


@router.get("/ab-tests", response_model=List[Dict[str, Any]])
async def get_active_ab_tests(
    governance_service: ModelGovernanceService = Depends(get_governance_service)
):
    """Get all active A/B tests."""
    try:
        tests = await governance_service.get_active_ab_tests()
        return tests
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get A/B tests: {str(e)}")


@router.post("/ab-tests", response_model=Dict[str, str])
async def create_ab_test(
    request: ABTestRequest,
    governance_service: ModelGovernanceService = Depends(get_governance_service)
):
    """Create A/B test between two models."""
    try:
        test_id = await governance_service.create_ab_test(
            model_a_version=request.model_a_version,
            model_b_version=request.model_b_version,
            traffic_split=request.traffic_split,
            duration_hours=request.duration_hours
        )
        
        return {
            "test_id": test_id,
            "status": "created",
            "message": "A/B test created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create A/B test: {str(e)}")


@router.post("/ab-tests/{test_id}/stop", response_model=Dict[str, Any])
async def stop_ab_test(
    test_id: str,
    governance_service: ModelGovernanceService = Depends(get_governance_service)
):
    """Stop A/B test and get results."""
    try:
        results = await governance_service.stop_ab_test(test_id)
        
        return {
            "test_id": test_id,
            "status": "stopped",
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop A/B test: {str(e)}")


@router.get("/health", response_model=Dict[str, str])
async def governance_health_check():
    """Health check endpoint for governance service."""
    try:
        governance_service = get_governance_service()
        
        return {
            "status": "healthy" if governance_service._is_running else "stopped",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "model_governance"
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "service": "model_governance"
        }


@router.get("/config", response_model=Dict[str, Any])
async def get_governance_config(
    governance_service: ModelGovernanceService = Depends(get_governance_service)
):
    """Get current governance configuration."""
    try:
        from dataclasses import asdict
        config_dict = asdict(governance_service.config)
        
        return {
            "config": config_dict,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}")


# Inference integration endpoints
@router.post("/inference/record", response_model=Dict[str, str])
async def record_inference_result(
    model_version: str = Body(..., description="Model version ID"),
    input_data: Dict[str, Any] = Body(..., description="Input data used for inference"),
    prediction: Any = Body(..., description="Model prediction"),
    actual: Optional[Any] = Body(None, description="Actual/ground truth value"),
    latency_ms: Optional[float] = Body(None, description="Inference latency in milliseconds"),
    confidence: Optional[float] = Body(None, description="Prediction confidence score"),
    request_id: Optional[str] = Body(None, description="Request ID for A/B testing"),
    governance_service: ModelGovernanceService = Depends(get_governance_service)
):
    """Record inference result for monitoring and A/B testing."""
    try:
        await governance_service.record_inference_result(
            model_version=model_version,
            input_data=input_data,
            prediction=prediction,
            actual=actual,
            latency_ms=latency_ms,
            confidence=confidence,
            request_id=request_id
        )
        
        return {
            "status": "recorded",
            "model_version": model_version,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record inference result: {str(e)}")


@router.get("/inference/model/{model_type}", response_model=Dict[str, str])
async def get_model_for_inference(
    model_type: str,
    request_id: Optional[str] = Query(None, description="Request ID for consistent A/B testing"),
    governance_service: ModelGovernanceService = Depends(get_governance_service)
):
    """Get appropriate model version for inference (considering A/B tests)."""
    try:
        model_type_enum = ModelType(model_type)
        model_version = await governance_service.get_model_for_inference(
            model_type=model_type_enum,
            request_id=request_id
        )
        
        if not model_version:
            raise HTTPException(
                status_code=404,
                detail=f"No model available for type {model_type}"
            )
        
        return {
            "model_version": model_version,
            "model_type": model_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid model type: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get model for inference: {str(e)}")