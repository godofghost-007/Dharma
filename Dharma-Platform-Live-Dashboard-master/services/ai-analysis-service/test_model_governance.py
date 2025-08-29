"""Test suite for model governance and lifecycle management."""

import asyncio
import json
import os
import tempfile
import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification

from app.core.model_registry import (
    ModelRegistry, ABTestManager, ModelPerformanceMonitor, ModelGovernanceManager,
    ModelType, ModelStatus, ModelMetrics, ModelVersion
)


@pytest.fixture
def temp_registry_path():
    """Create temporary directory for model registry."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_model_metrics():
    """Sample model metrics for testing."""
    return ModelMetrics(
        accuracy=0.85,
        precision=0.82,
        recall=0.88,
        f1_score=0.85,
        auc_roc=0.90
    )


@pytest.fixture
def sample_trained_model(temp_registry_path):
    """Create a sample trained model for testing."""
    # Generate sample data
    X, y = make_classification(n_samples=1000, n_features=20, n_classes=2, random_state=42)
    
    # Train a simple model
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X, y)
    
    # Save model
    model_path = os.path.join(temp_registry_path, "test_model.pkl")
    joblib.dump(model, model_path)
    
    # Create config file
    config_path = os.path.join(temp_registry_path, "test_config.json")
    config = {
        "model_type": "sentiment_analysis",
        "hyperparameters": {
            "n_estimators": 10,
            "random_state": 42
        }
    }
    with open(config_path, 'w') as f:
        json.dump(config, f)
    
    return {
        "model_path": model_path,
        "config_path": config_path,
        "training_data": X,
        "model": model
    }


class TestModelRegistry:
    """Test model registry functionality."""
    
    @pytest.mark.asyncio
    async def test_register_model(self, temp_registry_path, sample_model_metrics, sample_trained_model):
        """Test model registration."""
        registry = ModelRegistry(temp_registry_path)
        
        version_id = await registry.register_model(
            model_type=ModelType.SENTIMENT_ANALYSIS,
            model_path=sample_trained_model["model_path"],
            config_path=sample_trained_model["config_path"],
            metrics=sample_model_metrics,
            training_data=sample_trained_model["training_data"],
            metadata={"experiment": "test"},
            tags=["test", "v1"],
            description="Test model registration"
        )
        
        assert version_id is not None
        
        # Verify model was registered
        model = await registry.get_model(version_id)
        assert model is not None
        assert model.model_type == ModelType.SENTIMENT_ANALYSIS
        assert model.status == ModelStatus.VALIDATION
        assert model.metrics.accuracy == 0.85
        assert "test" in model.tags
    
    @pytest.mark.asyncio
    async def test_get_latest_model(self, temp_registry_path, sample_model_metrics, sample_trained_model):
        """Test getting latest model."""
        registry = ModelRegistry(temp_registry_path)
        
        # Register first model
        version_id_1 = await registry.register_model(
            model_type=ModelType.SENTIMENT_ANALYSIS,
            model_path=sample_trained_model["model_path"],
            config_path=sample_trained_model["config_path"],
            metrics=sample_model_metrics,
            training_data=sample_trained_model["training_data"]
        )
        
        # Promote to production
        await registry.update_model_status(version_id_1, ModelStatus.PRODUCTION)
        
        # Register second model
        version_id_2 = await registry.register_model(
            model_type=ModelType.SENTIMENT_ANALYSIS,
            model_path=sample_trained_model["model_path"],
            config_path=sample_trained_model["config_path"],
            metrics=sample_model_metrics,
            training_data=sample_trained_model["training_data"]
        )
        
        # Get latest production model
        latest = await registry.get_latest_model(ModelType.SENTIMENT_ANALYSIS, ModelStatus.PRODUCTION)
        assert latest.version_id == version_id_1
        
        # Get latest validation model
        latest_val = await registry.get_latest_model(ModelType.SENTIMENT_ANALYSIS, ModelStatus.VALIDATION)
        assert latest_val.version_id == version_id_2
    
    @pytest.mark.asyncio
    async def test_promote_model(self, temp_registry_path, sample_model_metrics, sample_trained_model):
        """Test model promotion."""
        registry = ModelRegistry(temp_registry_path)
        
        # Register and promote first model
        version_id_1 = await registry.register_model(
            model_type=ModelType.SENTIMENT_ANALYSIS,
            model_path=sample_trained_model["model_path"],
            config_path=sample_trained_model["config_path"],
            metrics=sample_model_metrics,
            training_data=sample_trained_model["training_data"]
        )
        
        await registry.update_model_status(version_id_1, ModelStatus.STAGING)
        await registry.promote_model(version_id_1)
        
        model_1 = await registry.get_model(version_id_1)
        assert model_1.status == ModelStatus.PRODUCTION
        
        # Register and promote second model
        version_id_2 = await registry.register_model(
            model_type=ModelType.SENTIMENT_ANALYSIS,
            model_path=sample_trained_model["model_path"],
            config_path=sample_trained_model["config_path"],
            metrics=sample_model_metrics,
            training_data=sample_trained_model["training_data"]
        )
        
        await registry.update_model_status(version_id_2, ModelStatus.STAGING)
        await registry.promote_model(version_id_2)
        
        # Check that first model is deprecated and second is production
        model_1 = await registry.get_model(version_id_1)
        model_2 = await registry.get_model(version_id_2)
        
        assert model_1.status == ModelStatus.DEPRECATED
        assert model_2.status == ModelStatus.PRODUCTION
    
    @pytest.mark.asyncio
    async def test_rollback_model(self, temp_registry_path, sample_model_metrics, sample_trained_model):
        """Test model rollback."""
        registry = ModelRegistry(temp_registry_path)
        
        # Register and promote first model
        version_id_1 = await registry.register_model(
            model_type=ModelType.SENTIMENT_ANALYSIS,
            model_path=sample_trained_model["model_path"],
            config_path=sample_trained_model["config_path"],
            metrics=sample_model_metrics,
            training_data=sample_trained_model["training_data"]
        )
        
        await registry.update_model_status(version_id_1, ModelStatus.STAGING)
        await registry.promote_model(version_id_1)
        
        # Register and promote second model
        version_id_2 = await registry.register_model(
            model_type=ModelType.SENTIMENT_ANALYSIS,
            model_path=sample_trained_model["model_path"],
            config_path=sample_trained_model["config_path"],
            metrics=sample_model_metrics,
            training_data=sample_trained_model["training_data"]
        )
        
        await registry.update_model_status(version_id_2, ModelStatus.STAGING)
        await registry.promote_model(version_id_2)
        
        # Rollback to previous model
        success = await registry.rollback_model(ModelType.SENTIMENT_ANALYSIS)
        assert success
        
        # Check that first model is back in production
        model_1 = await registry.get_model(version_id_1)
        model_2 = await registry.get_model(version_id_2)
        
        assert model_1.status == ModelStatus.PRODUCTION
        assert model_2.status == ModelStatus.DEPRECATED


class TestABTestManager:
    """Test A/B testing functionality."""
    
    @pytest.mark.asyncio
    async def test_create_ab_test(self, temp_registry_path, sample_model_metrics, sample_trained_model):
        """Test A/B test creation."""
        registry = ModelRegistry(temp_registry_path)
        ab_manager = ABTestManager(registry)
        
        # Register two models
        version_id_1 = await registry.register_model(
            model_type=ModelType.SENTIMENT_ANALYSIS,
            model_path=sample_trained_model["model_path"],
            config_path=sample_trained_model["config_path"],
            metrics=sample_model_metrics,
            training_data=sample_trained_model["training_data"]
        )
        
        version_id_2 = await registry.register_model(
            model_type=ModelType.SENTIMENT_ANALYSIS,
            model_path=sample_trained_model["model_path"],
            config_path=sample_trained_model["config_path"],
            metrics=sample_model_metrics,
            training_data=sample_trained_model["training_data"]
        )
        
        # Create A/B test
        test_id = await ab_manager.create_ab_test(
            model_a_version=version_id_1,
            model_b_version=version_id_2,
            traffic_split=0.2,
            duration_hours=24
        )
        
        assert test_id is not None
        assert test_id in ab_manager._active_tests
        
        test_config = ab_manager._active_tests[test_id]
        assert test_config.model_a_version == version_id_1
        assert test_config.model_b_version == version_id_2
        assert test_config.traffic_split == 0.2
    
    @pytest.mark.asyncio
    async def test_get_model_for_request(self, temp_registry_path, sample_model_metrics, sample_trained_model):
        """Test model selection for requests during A/B test."""
        registry = ModelRegistry(temp_registry_path)
        ab_manager = ABTestManager(registry)
        
        # Register models
        version_id_1 = await registry.register_model(
            model_type=ModelType.SENTIMENT_ANALYSIS,
            model_path=sample_trained_model["model_path"],
            config_path=sample_trained_model["config_path"],
            metrics=sample_model_metrics,
            training_data=sample_trained_model["training_data"]
        )
        
        await registry.update_model_status(version_id_1, ModelStatus.PRODUCTION)
        
        version_id_2 = await registry.register_model(
            model_type=ModelType.SENTIMENT_ANALYSIS,
            model_path=sample_trained_model["model_path"],
            config_path=sample_trained_model["config_path"],
            metrics=sample_model_metrics,
            training_data=sample_trained_model["training_data"]
        )
        
        # Without A/B test, should return production model
        selected = await ab_manager.get_model_for_request(ModelType.SENTIMENT_ANALYSIS)
        assert selected == version_id_1
        
        # Create A/B test
        test_id = await ab_manager.create_ab_test(
            model_a_version=version_id_1,
            model_b_version=version_id_2,
            traffic_split=0.5
        )
        
        # With A/B test, should return either model
        selected = await ab_manager.get_model_for_request(ModelType.SENTIMENT_ANALYSIS, "test_request_1")
        assert selected in [version_id_1, version_id_2]
    
    @pytest.mark.asyncio
    async def test_record_test_result(self, temp_registry_path, sample_model_metrics, sample_trained_model):
        """Test recording A/B test results."""
        registry = ModelRegistry(temp_registry_path)
        ab_manager = ABTestManager(registry)
        
        # Register models and create test
        version_id_1 = await registry.register_model(
            model_type=ModelType.SENTIMENT_ANALYSIS,
            model_path=sample_trained_model["model_path"],
            config_path=sample_trained_model["config_path"],
            metrics=sample_model_metrics,
            training_data=sample_trained_model["training_data"]
        )
        
        version_id_2 = await registry.register_model(
            model_type=ModelType.SENTIMENT_ANALYSIS,
            model_path=sample_trained_model["model_path"],
            config_path=sample_trained_model["config_path"],
            metrics=sample_model_metrics,
            training_data=sample_trained_model["training_data"]
        )
        
        test_id = await ab_manager.create_ab_test(
            model_a_version=version_id_1,
            model_b_version=version_id_2,
            minimum_sample_size=10
        )
        
        # Record results for both models
        for i in range(15):
            await ab_manager.record_test_result(
                test_id=test_id,
                model_version=version_id_1,
                result={"accuracy": 0.8 + np.random.normal(0, 0.05)}
            )
            
            await ab_manager.record_test_result(
                test_id=test_id,
                model_version=version_id_2,
                result={"accuracy": 0.85 + np.random.normal(0, 0.05)}
            )
        
        # Check that results were recorded
        results = ab_manager._test_results[test_id]
        assert results["model_a_count"] == 15
        assert results["model_b_count"] == 15
        
        # Check if analysis was triggered
        test_config = ab_manager._active_tests[test_id]
        assert test_config.results is not None


class TestModelPerformanceMonitor:
    """Test model performance monitoring."""
    
    @pytest.mark.asyncio
    async def test_setup_drift_detection(self, temp_registry_path, sample_model_metrics, sample_trained_model):
        """Test drift detection setup."""
        registry = ModelRegistry(temp_registry_path)
        monitor = ModelPerformanceMonitor(registry)
        
        # Register model
        version_id = await registry.register_model(
            model_type=ModelType.SENTIMENT_ANALYSIS,
            model_path=sample_trained_model["model_path"],
            config_path=sample_trained_model["config_path"],
            metrics=sample_model_metrics,
            training_data=sample_trained_model["training_data"]
        )
        
        # Setup drift detection
        feature_importance = {"feature_1": 0.3, "feature_2": 0.7}
        await monitor.setup_drift_detection(
            model_version=version_id,
            reference_data=sample_trained_model["training_data"],
            feature_importance=feature_importance
        )
        
        assert version_id in monitor._drift_detectors
        drift_config = monitor._drift_detectors[version_id]
        assert drift_config.model_version == version_id
        assert drift_config.feature_importance == feature_importance
    
    @pytest.mark.asyncio
    async def test_record_prediction(self, temp_registry_path, sample_model_metrics, sample_trained_model):
        """Test prediction recording."""
        registry = ModelRegistry(temp_registry_path)
        monitor = ModelPerformanceMonitor(registry)
        
        # Register model
        version_id = await registry.register_model(
            model_type=ModelType.SENTIMENT_ANALYSIS,
            model_path=sample_trained_model["model_path"],
            config_path=sample_trained_model["config_path"],
            metrics=sample_model_metrics,
            training_data=sample_trained_model["training_data"]
        )
        
        # Record predictions
        for i in range(10):
            await monitor.record_prediction(
                model_version=version_id,
                input_data={"feature_1": i, "feature_2": i * 2},
                prediction="positive",
                actual="positive" if i % 2 == 0 else "negative",
                latency_ms=50.0 + i
            )
        
        assert version_id in monitor._performance_history
        assert len(monitor._performance_history[version_id]) == 10
    
    @pytest.mark.asyncio
    async def test_get_performance_summary(self, temp_registry_path, sample_model_metrics, sample_trained_model):
        """Test performance summary generation."""
        registry = ModelRegistry(temp_registry_path)
        monitor = ModelPerformanceMonitor(registry)
        
        # Register model
        version_id = await registry.register_model(
            model_type=ModelType.SENTIMENT_ANALYSIS,
            model_path=sample_trained_model["model_path"],
            config_path=sample_trained_model["config_path"],
            metrics=sample_model_metrics,
            training_data=sample_trained_model["training_data"]
        )
        
        # Record predictions with ground truth
        predictions = ["positive", "negative", "positive", "positive", "negative"]
        actuals = ["positive", "negative", "negative", "positive", "negative"]
        
        for i, (pred, actual) in enumerate(zip(predictions, actuals)):
            await monitor.record_prediction(
                model_version=version_id,
                input_data={"feature_1": i},
                prediction=pred,
                actual=actual,
                latency_ms=50.0 + i * 10
            )
        
        # Get performance summary
        summary = await monitor.get_performance_summary(version_id)
        
        assert summary["total_predictions"] == 5
        assert summary["predictions_with_ground_truth"] == 5
        assert "accuracy" in summary
        assert "average_latency_ms" in summary
        assert summary["average_latency_ms"] == 70.0  # (50+60+70+80+90)/5


class TestModelGovernanceManager:
    """Test overall model governance manager."""
    
    @pytest.mark.asyncio
    async def test_governance_dashboard_data(self, temp_registry_path, sample_model_metrics, sample_trained_model):
        """Test governance dashboard data generation."""
        governance = ModelGovernanceManager(temp_registry_path)
        
        # Register some models
        version_id_1 = await governance.model_registry.register_model(
            model_type=ModelType.SENTIMENT_ANALYSIS,
            model_path=sample_trained_model["model_path"],
            config_path=sample_trained_model["config_path"],
            metrics=sample_model_metrics,
            training_data=sample_trained_model["training_data"]
        )
        
        await governance.model_registry.update_model_status(version_id_1, ModelStatus.PRODUCTION)
        
        version_id_2 = await governance.model_registry.register_model(
            model_type=ModelType.BOT_DETECTION,
            model_path=sample_trained_model["model_path"],
            config_path=sample_trained_model["config_path"],
            metrics=sample_model_metrics,
            training_data=sample_trained_model["training_data"]
        )
        
        # Create A/B test
        await governance.ab_test_manager.create_ab_test(
            model_a_version=version_id_1,
            model_b_version=version_id_2,
            traffic_split=0.1
        )
        
        # Get dashboard data
        dashboard_data = await governance.get_governance_dashboard_data()
        
        assert "model_statistics" in dashboard_data
        assert "ab_test_statistics" in dashboard_data
        assert "performance_summaries" in dashboard_data
        
        model_stats = dashboard_data["model_statistics"]
        assert model_stats["total_models"] == 2
        assert model_stats["production_models"] == 1
        
        ab_stats = dashboard_data["ab_test_statistics"]
        assert ab_stats["active_tests"] == 1


@pytest.mark.asyncio
async def test_integration_workflow(temp_registry_path, sample_model_metrics, sample_trained_model):
    """Test complete model governance workflow."""
    governance = ModelGovernanceManager(temp_registry_path)
    
    # 1. Register initial model
    version_id_1 = await governance.model_registry.register_model(
        model_type=ModelType.SENTIMENT_ANALYSIS,
        model_path=sample_trained_model["model_path"],
        config_path=sample_trained_model["config_path"],
        metrics=sample_model_metrics,
        training_data=sample_trained_model["training_data"],
        description="Initial sentiment analysis model"
    )
    
    # 2. Promote to production
    await governance.model_registry.update_model_status(version_id_1, ModelStatus.STAGING)
    await governance.model_registry.promote_model(version_id_1)
    
    # 3. Register improved model
    improved_metrics = ModelMetrics(
        accuracy=0.90,
        precision=0.88,
        recall=0.92,
        f1_score=0.90,
        auc_roc=0.95
    )
    
    version_id_2 = await governance.model_registry.register_model(
        model_type=ModelType.SENTIMENT_ANALYSIS,
        model_path=sample_trained_model["model_path"],
        config_path=sample_trained_model["config_path"],
        metrics=improved_metrics,
        training_data=sample_trained_model["training_data"],
        description="Improved sentiment analysis model"
    )
    
    # 4. Start A/B test
    test_id = await governance.ab_test_manager.create_ab_test(
        model_a_version=version_id_1,
        model_b_version=version_id_2,
        traffic_split=0.2,
        minimum_sample_size=20
    )
    
    # 5. Simulate traffic and record results
    for i in range(25):
        # Model A results (baseline)
        await governance.ab_test_manager.record_test_result(
            test_id=test_id,
            model_version=version_id_1,
            result={"accuracy": 0.85 + np.random.normal(0, 0.02)}
        )
        
        # Model B results (improved)
        await governance.ab_test_manager.record_test_result(
            test_id=test_id,
            model_version=version_id_2,
            result={"accuracy": 0.90 + np.random.normal(0, 0.02)}
        )
    
    # 6. Check test results
    test_config = governance.ab_test_manager._active_tests[test_id]
    assert test_config.results is not None
    assert test_config.results["winner"] == "model_b"
    
    # 7. Setup performance monitoring
    await governance.performance_monitor.setup_drift_detection(
        model_version=version_id_2,
        reference_data=sample_trained_model["training_data"],
        feature_importance={"feature_1": 0.4, "feature_2": 0.6}
    )
    
    # 8. Record some predictions
    for i in range(50):
        await governance.performance_monitor.record_prediction(
            model_version=version_id_2,
            input_data={"feature_1": i, "feature_2": i * 1.5},
            prediction="positive" if i % 2 == 0 else "negative",
            actual="positive" if i % 3 == 0 else "negative",
            latency_ms=45.0 + np.random.normal(0, 5)
        )
    
    # 9. Get performance summary
    summary = await governance.performance_monitor.get_model_performance_summary(version_id_2)
    assert summary["total_predictions"] == 50
    assert "accuracy" in summary
    
    # 10. Get governance dashboard
    dashboard = await governance.get_governance_dashboard_data()
    assert dashboard["model_statistics"]["total_models"] == 2
    assert dashboard["ab_test_statistics"]["active_tests"] == 1


if __name__ == "__main__":
    # Run a simple test
    async def run_simple_test():
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sample model
            X, y = make_classification(n_samples=100, n_features=10, n_classes=2, random_state=42)
            model = RandomForestClassifier(n_estimators=5, random_state=42)
            model.fit(X, y)
            
            model_path = os.path.join(temp_dir, "test_model.pkl")
            joblib.dump(model, model_path)
            
            config_path = os.path.join(temp_dir, "test_config.json")
            with open(config_path, 'w') as f:
                json.dump({"test": True}, f)
            
            # Test model registry
            registry = ModelRegistry(temp_dir)
            metrics = ModelMetrics(accuracy=0.8, precision=0.75, recall=0.85, f1_score=0.8)
            
            version_id = await registry.register_model(
                model_type=ModelType.SENTIMENT_ANALYSIS,
                model_path=model_path,
                config_path=config_path,
                metrics=metrics,
                training_data=X,
                description="Test model"
            )
            
            print(f"Registered model with ID: {version_id}")
            
            # Test A/B testing
            ab_manager = ABTestManager(registry)
            
            version_id_2 = await registry.register_model(
                model_type=ModelType.SENTIMENT_ANALYSIS,
                model_path=model_path,
                config_path=config_path,
                metrics=metrics,
                training_data=X,
                description="Test model 2"
            )
            
            test_id = await ab_manager.create_ab_test(version_id, version_id_2)
            print(f"Created A/B test with ID: {test_id}")
            
            # Test performance monitoring
            monitor = ModelPerformanceMonitor(registry)
            await monitor.setup_drift_detection(
                model_version=version_id,
                reference_data=X,
                feature_importance={"feature_0": 0.5, "feature_1": 0.5}
            )
            
            await monitor.record_prediction(
                model_version=version_id,
                input_data={"feature_0": 1.0, "feature_1": 2.0},
                prediction="positive",
                actual="positive",
                latency_ms=50.0
            )
            
            summary = await monitor.get_model_performance_summary(version_id)
            print(f"Performance summary: {summary}")
            
            print("All tests passed!")
    
    asyncio.run(run_simple_test())