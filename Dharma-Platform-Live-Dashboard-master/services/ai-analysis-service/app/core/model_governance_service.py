"""Model governance service integration with the AI analysis service."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import HTTPException

from .model_registry import (
    ModelGovernanceManager, ModelType, ModelStatus, ModelMetrics
)
from .governance_config import (
    load_governance_config, get_model_type_config, ModelGovernanceConfig
)
from ..models.requests import SentimentRequest, BotDetectionRequest, CampaignDetectionRequest

logger = logging.getLogger(__name__)


class ModelGovernanceService:
    """Service that integrates model governance with AI analysis operations."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = load_governance_config(config_path)
        self.governance_manager = ModelGovernanceManager(
            registry_path=self.config.registry_path,
            mlflow_tracking_uri=self.config.mlflow_tracking_uri
        )
        self._is_running = False
    
    async def start(self):
        """Start the model governance service."""
        if self._is_running:
            return
        
        await self.governance_manager.start_monitoring()
        self._is_running = True
        logger.info("Model governance service started")
    
    async def stop(self):
        """Stop the model governance service."""
        if not self._is_running:
            return
        
        await self.governance_manager.stop_monitoring()
        self._is_running = False
        logger.info("Model governance service stopped")
    
    async def get_model_for_inference(
        self,
        model_type: ModelType,
        request_id: Optional[str] = None
    ) -> Optional[str]:
        """Get the appropriate model version for inference."""
        
        # Check if A/B testing is enabled and get model accordingly
        if self.config.ab_testing_enabled:
            model_version = await self.governance_manager.ab_test_manager.get_model_for_request(
                model_type, request_id
            )
        else:
            # Get latest production model
            model = await self.governance_manager.model_registry.get_latest_model(
                model_type, ModelStatus.PRODUCTION
            )
            model_version = model.version_id if model else None
        
        if not model_version:
            logger.warning(f"No model available for type {model_type.value}")
            return None
        
        return model_version
    
    async def record_inference_result(
        self,
        model_version: str,
        input_data: Dict[str, Any],
        prediction: Any,
        actual: Optional[Any] = None,
        latency_ms: Optional[float] = None,
        confidence: Optional[float] = None,
        request_id: Optional[str] = None
    ):
        """Record inference result for monitoring and A/B testing."""
        
        if not self.config.performance_monitoring_enabled:
            return
        
        # Record for performance monitoring
        await self.governance_manager.performance_monitor.record_prediction(
            model_version=model_version,
            input_data=input_data,
            prediction=prediction,
            actual=actual,
            latency_ms=latency_ms
        )
        
        # Record for A/B testing if applicable
        if self.config.ab_testing_enabled and request_id:
            # Find active A/B test for this model
            active_tests = await self.governance_manager.ab_test_manager.get_active_tests()
            
            for test in active_tests:
                if model_version in [test.model_a_version, test.model_b_version]:
                    result = {
                        "accuracy": 1.0 if prediction == actual else 0.0 if actual else None,
                        "confidence": confidence,
                        "latency_ms": latency_ms
                    }
                    
                    # Filter out None values
                    result = {k: v for k, v in result.items() if v is not None}
                    
                    if result:
                        await self.governance_manager.ab_test_manager.record_test_result(
                            test_id=test.test_id,
                            model_version=model_version,
                            result=result
                        )
                    break
    
    async def register_new_model(
        self,
        model_type: ModelType,
        model_path: str,
        config_path: str,
        metrics: ModelMetrics,
        training_data: Any,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        description: str = ""
    ) -> str:
        """Register a new model with governance checks."""
        
        # Validate model meets minimum requirements
        model_config = get_model_type_config(model_type.value)
        
        if metrics.accuracy < model_config.accuracy_threshold:
            raise HTTPException(
                status_code=400,
                detail=f"Model accuracy {metrics.accuracy} below threshold {model_config.accuracy_threshold}"
            )
        
        if metrics.precision < model_config.precision_threshold:
            raise HTTPException(
                status_code=400,
                detail=f"Model precision {metrics.precision} below threshold {model_config.precision_threshold}"
            )
        
        if metrics.recall < model_config.recall_threshold:
            raise HTTPException(
                status_code=400,
                detail=f"Model recall {metrics.recall} below threshold {model_config.recall_threshold}"
            )
        
        # Register the model
        version_id = await self.governance_manager.model_registry.register_model(
            model_type=model_type,
            model_path=model_path,
            config_path=config_path,
            metrics=metrics,
            training_data=training_data,
            metadata=metadata,
            tags=tags,
            description=description
        )
        
        logger.info(f"Registered new model {model_type.value} with version ID {version_id}")
        return version_id
    
    async def promote_model_to_production(
        self,
        version_id: str,
        skip_ab_test: bool = False
    ) -> bool:
        """Promote model to production with optional A/B testing."""
        
        model = await self.governance_manager.model_registry.get_model(version_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        if model.status != ModelStatus.STAGING:
            raise HTTPException(
                status_code=400,
                detail="Model must be in staging status to promote to production"
            )
        
        # If A/B testing is enabled and not skipped, create A/B test
        if self.config.ab_testing_enabled and not skip_ab_test:
            current_prod = await self.governance_manager.model_registry.get_latest_model(
                model.model_type, ModelStatus.PRODUCTION
            )
            
            if current_prod:
                # Create A/B test between current production and new model
                test_id = await self.governance_manager.ab_test_manager.create_ab_test(
                    model_a_version=current_prod.version_id,
                    model_b_version=version_id,
                    traffic_split=self.config.default_traffic_split,
                    duration_hours=self.config.default_test_duration_hours
                )
                
                logger.info(f"Created A/B test {test_id} for model promotion")
                return True
        
        # Direct promotion without A/B testing
        success = await self.governance_manager.model_registry.promote_model(version_id)
        if success:
            logger.info(f"Promoted model {version_id} to production")
        
        return success
    
    async def rollback_model(self, model_type: ModelType) -> bool:
        """Rollback to previous production model."""
        
        success = await self.governance_manager.model_registry.rollback_model(model_type)
        if success:
            logger.info(f"Rolled back {model_type.value} model to previous version")
        
        return success
    
    async def create_ab_test(
        self,
        model_a_version: str,
        model_b_version: str,
        traffic_split: float = None,
        duration_hours: int = None
    ) -> str:
        """Create A/B test between two models."""
        
        if not self.config.ab_testing_enabled:
            raise HTTPException(status_code=400, detail="A/B testing is disabled")
        
        # Check if we're at the limit of concurrent tests
        active_tests = await self.governance_manager.ab_test_manager.get_active_tests()
        if len(active_tests) >= self.config.max_concurrent_ab_tests:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum concurrent A/B tests ({self.config.max_concurrent_ab_tests}) reached"
            )
        
        test_id = await self.governance_manager.ab_test_manager.create_ab_test(
            model_a_version=model_a_version,
            model_b_version=model_b_version,
            traffic_split=traffic_split or self.config.default_traffic_split,
            duration_hours=duration_hours or self.config.default_test_duration_hours,
            minimum_sample_size=self.config.minimum_sample_size,
            confidence_level=self.config.confidence_level
        )
        
        logger.info(f"Created A/B test {test_id}")
        return test_id
    
    async def stop_ab_test(self, test_id: str) -> Dict[str, Any]:
        """Stop A/B test and get results."""
        
        results = await self.governance_manager.ab_test_manager.stop_ab_test(test_id)
        logger.info(f"Stopped A/B test {test_id}")
        return results
    
    async def setup_model_monitoring(
        self,
        model_version: str,
        reference_data: Any,
        feature_importance: Dict[str, float]
    ):
        """Setup drift detection and monitoring for a model."""
        
        if not self.config.drift_detection_enabled:
            return
        
        await self.governance_manager.performance_monitor.setup_drift_detection(
            model_version=model_version,
            reference_data=reference_data,
            feature_importance=feature_importance,
            drift_threshold=self.config.drift_threshold
        )
        
        logger.info(f"Setup monitoring for model {model_version}")
    
    async def get_model_performance_summary(
        self,
        model_version: str,
        days: int = None
    ) -> Dict[str, Any]:
        """Get performance summary for a model."""
        
        days = days or self.config.performance_summary_days
        
        return await self.governance_manager.performance_monitor.get_model_performance_summary(
            model_version, days
        )
    
    async def get_governance_dashboard(self) -> Dict[str, Any]:
        """Get governance dashboard data."""
        
        return await self.governance_manager.get_governance_dashboard_data()
    
    async def list_models(
        self,
        model_type: Optional[ModelType] = None,
        status: Optional[ModelStatus] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """List models with optional filtering."""
        
        models = await self.governance_manager.model_registry.list_models(
            model_type=model_type,
            status=status,
            tags=tags
        )
        
        return [model.to_dict() for model in models]
    
    async def get_active_ab_tests(self) -> List[Dict[str, Any]]:
        """Get all active A/B tests."""
        
        tests = await self.governance_manager.ab_test_manager.get_active_tests()
        return [
            {
                "test_id": test.test_id,
                "model_a_version": test.model_a_version,
                "model_b_version": test.model_b_version,
                "traffic_split": test.traffic_split,
                "start_time": test.start_time.isoformat(),
                "end_time": test.end_time.isoformat(),
                "status": test.status,
                "results": test.results
            }
            for test in tests
        ]
    
    async def validate_model_for_production(self, version_id: str) -> Dict[str, Any]:
        """Validate model meets production requirements."""
        
        model = await self.governance_manager.model_registry.get_model(version_id)
        if not model:
            return {"valid": False, "errors": ["Model not found"]}
        
        errors = []
        warnings = []
        
        # Check model type configuration
        model_config = get_model_type_config(model.model_type.value)
        
        if model.metrics.accuracy < model_config.accuracy_threshold:
            errors.append(f"Accuracy {model.metrics.accuracy} below threshold {model_config.accuracy_threshold}")
        
        if model.metrics.precision < model_config.precision_threshold:
            errors.append(f"Precision {model.metrics.precision} below threshold {model_config.precision_threshold}")
        
        if model.metrics.recall < model_config.recall_threshold:
            errors.append(f"Recall {model.metrics.recall} below threshold {model_config.recall_threshold}")
        
        # Check if model file exists and is valid
        import os
        if not os.path.exists(model.model_path):
            errors.append("Model file not found")
        
        if not os.path.exists(model.config_path):
            warnings.append("Config file not found")
        
        # Check model status
        if model.status not in [ModelStatus.STAGING, ModelStatus.VALIDATION]:
            errors.append(f"Model status {model.status.value} not suitable for production")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "model_info": {
                "version_id": model.version_id,
                "model_type": model.model_type.value,
                "version_number": model.version_number,
                "status": model.status.value,
                "metrics": model.metrics.to_dict()
            }
        }


# Global instance
_governance_service: Optional[ModelGovernanceService] = None


def get_governance_service() -> ModelGovernanceService:
    """Get global governance service instance."""
    global _governance_service
    
    if _governance_service is None:
        _governance_service = ModelGovernanceService()
    
    return _governance_service


async def initialize_governance_service(config_path: Optional[str] = None):
    """Initialize and start the governance service."""
    global _governance_service
    
    _governance_service = ModelGovernanceService(config_path)
    await _governance_service.start()
    
    logger.info("Model governance service initialized")


async def shutdown_governance_service():
    """Shutdown the governance service."""
    global _governance_service
    
    if _governance_service:
        await _governance_service.stop()
        _governance_service = None
    
    logger.info("Model governance service shutdown")