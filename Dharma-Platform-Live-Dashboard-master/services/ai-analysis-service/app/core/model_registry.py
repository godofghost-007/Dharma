"""Model registry and lifecycle management system."""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import pickle
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib
import mlflow
import mlflow.sklearn
import mlflow.pytorch
from mlflow.tracking import MlflowClient

logger = logging.getLogger(__name__)


class ModelStatus(Enum):
    """Model deployment status."""
    TRAINING = "training"
    VALIDATION = "validation"
    STAGING = "staging"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    FAILED = "failed"


class ModelType(Enum):
    """Types of models in the system."""
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    BOT_DETECTION = "bot_detection"
    CAMPAIGN_DETECTION = "campaign_detection"
    LANGUAGE_DETECTION = "language_detection"


@dataclass
class ModelMetrics:
    """Model performance metrics."""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: Optional[float] = None
    confusion_matrix: Optional[List[List[int]]] = None
    custom_metrics: Optional[Dict[str, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ModelVersion:
    """Model version information."""
    version_id: str
    model_type: ModelType
    version_number: str
    status: ModelStatus
    created_at: datetime
    updated_at: datetime
    model_path: str
    config_path: str
    metrics: ModelMetrics
    metadata: Dict[str, Any]
    training_data_hash: str
    model_hash: str
    tags: List[str]
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        data['model_type'] = self.model_type.value
        data['status'] = self.status.value
        return data


@dataclass
class ABTestConfig:
    """A/B testing configuration."""
    test_id: str
    model_a_version: str
    model_b_version: str
    traffic_split: float  # Percentage for model B (0.0 to 1.0)
    start_time: datetime
    end_time: datetime
    success_metric: str
    minimum_sample_size: int
    confidence_level: float
    status: str
    results: Optional[Dict[str, Any]] = None


@dataclass
class DriftDetectionConfig:
    """Model drift detection configuration."""
    model_version: str
    drift_threshold: float
    monitoring_window: timedelta
    reference_data_hash: str
    feature_importance: Dict[str, float]
    statistical_tests: List[str]
    alert_threshold: float


class ModelRegistry:
    """Centralized model registry with versioning and lifecycle management."""
    
    def __init__(self, registry_path: str = "models", mlflow_tracking_uri: str = "sqlite:///mlflow.db"):
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(exist_ok=True)
        
        # Initialize MLflow
        mlflow.set_tracking_uri(mlflow_tracking_uri)
        self.mlflow_client = MlflowClient()
        
        # In-memory cache for quick access
        self._model_cache: Dict[str, ModelVersion] = {}
        self._ab_tests: Dict[str, ABTestConfig] = {}
        self._drift_configs: Dict[str, DriftDetectionConfig] = {}
        
        # Load existing models
        self._load_registry()
    
    def _load_registry(self):
        """Load existing model registry from disk."""
        registry_file = self.registry_path / "registry.json"
        if registry_file.exists():
            try:
                with open(registry_file, 'r') as f:
                    data = json.load(f)
                    
                for model_data in data.get('models', []):
                    model_version = ModelVersion(
                        version_id=model_data['version_id'],
                        model_type=ModelType(model_data['model_type']),
                        version_number=model_data['version_number'],
                        status=ModelStatus(model_data['status']),
                        created_at=datetime.fromisoformat(model_data['created_at']),
                        updated_at=datetime.fromisoformat(model_data['updated_at']),
                        model_path=model_data['model_path'],
                        config_path=model_data['config_path'],
                        metrics=ModelMetrics(**model_data['metrics']),
                        metadata=model_data['metadata'],
                        training_data_hash=model_data['training_data_hash'],
                        model_hash=model_data['model_hash'],
                        tags=model_data['tags'],
                        description=model_data['description']
                    )
                    self._model_cache[model_version.version_id] = model_version
                    
                logger.info(f"Loaded {len(self._model_cache)} models from registry")
            except Exception as e:
                logger.error(f"Failed to load model registry: {e}")
    
    def _save_registry(self):
        """Save model registry to disk."""
        registry_file = self.registry_path / "registry.json"
        try:
            data = {
                'models': [model.to_dict() for model in self._model_cache.values()],
                'updated_at': datetime.utcnow().isoformat()
            }
            
            with open(registry_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save model registry: {e}")
    
    def _calculate_model_hash(self, model_path: str) -> str:
        """Calculate hash of model file for integrity checking."""
        hasher = hashlib.sha256()
        with open(model_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _calculate_data_hash(self, data: Any) -> str:
        """Calculate hash of training data."""
        if hasattr(data, 'values'):  # pandas DataFrame
            data_bytes = data.values.tobytes()
        elif isinstance(data, np.ndarray):
            data_bytes = data.tobytes()
        else:
            data_bytes = str(data).encode()
        
        return hashlib.sha256(data_bytes).hexdigest()
    
    async def register_model(
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
        """Register a new model version."""
        
        version_id = str(uuid.uuid4())
        version_number = self._generate_version_number(model_type)
        
        # Calculate hashes
        model_hash = self._calculate_model_hash(model_path)
        training_data_hash = self._calculate_data_hash(training_data)
        
        # Create model version
        model_version = ModelVersion(
            version_id=version_id,
            model_type=model_type,
            version_number=version_number,
            status=ModelStatus.VALIDATION,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            model_path=model_path,
            config_path=config_path,
            metrics=metrics,
            metadata=metadata or {},
            training_data_hash=training_data_hash,
            model_hash=model_hash,
            tags=tags or [],
            description=description
        )
        
        # Store in cache and save to disk
        self._model_cache[version_id] = model_version
        self._save_registry()
        
        # Log to MLflow
        await self._log_to_mlflow(model_version)
        
        logger.info(f"Registered model {model_type.value} version {version_number} with ID {version_id}")
        return version_id
    
    def _generate_version_number(self, model_type: ModelType) -> str:
        """Generate next version number for model type."""
        existing_versions = [
            model.version_number for model in self._model_cache.values()
            if model.model_type == model_type
        ]
        
        if not existing_versions:
            return "1.0.0"
        
        # Parse semantic versions and increment
        versions = []
        for v in existing_versions:
            try:
                major, minor, patch = map(int, v.split('.'))
                versions.append((major, minor, patch))
            except ValueError:
                continue
        
        if not versions:
            return "1.0.0"
        
        latest = max(versions)
        return f"{latest[0]}.{latest[1]}.{latest[2] + 1}"
    
    async def _log_to_mlflow(self, model_version: ModelVersion):
        """Log model to MLflow tracking."""
        try:
            with mlflow.start_run(run_name=f"{model_version.model_type.value}_{model_version.version_number}"):
                # Log parameters
                mlflow.log_params(model_version.metadata)
                
                # Log metrics
                mlflow.log_metrics(model_version.metrics.to_dict())
                
                # Log model artifact
                if model_version.model_path.endswith('.pkl'):
                    model = joblib.load(model_version.model_path)
                    mlflow.sklearn.log_model(model, "model")
                
                # Log tags
                for tag in model_version.tags:
                    mlflow.set_tag(tag, "true")
                
                mlflow.set_tag("version_id", model_version.version_id)
                mlflow.set_tag("model_type", model_version.model_type.value)
                
        except Exception as e:
            logger.error(f"Failed to log model to MLflow: {e}")
    
    async def get_model(self, version_id: str) -> Optional[ModelVersion]:
        """Get model version by ID."""
        return self._model_cache.get(version_id)
    
    async def get_latest_model(self, model_type: ModelType, status: ModelStatus = ModelStatus.PRODUCTION) -> Optional[ModelVersion]:
        """Get latest model version of specified type and status."""
        models = [
            model for model in self._model_cache.values()
            if model.model_type == model_type and model.status == status
        ]
        
        if not models:
            return None
        
        return max(models, key=lambda m: m.created_at)
    
    async def list_models(
        self,
        model_type: Optional[ModelType] = None,
        status: Optional[ModelStatus] = None,
        tags: Optional[List[str]] = None
    ) -> List[ModelVersion]:
        """List models with optional filtering."""
        models = list(self._model_cache.values())
        
        if model_type:
            models = [m for m in models if m.model_type == model_type]
        
        if status:
            models = [m for m in models if m.status == status]
        
        if tags:
            models = [m for m in models if any(tag in m.tags for tag in tags)]
        
        return sorted(models, key=lambda m: m.created_at, reverse=True)
    
    async def update_model_status(self, version_id: str, status: ModelStatus) -> bool:
        """Update model status."""
        if version_id not in self._model_cache:
            return False
        
        model = self._model_cache[version_id]
        model.status = status
        model.updated_at = datetime.utcnow()
        
        self._save_registry()
        logger.info(f"Updated model {version_id} status to {status.value}")
        return True
    
    async def promote_model(self, version_id: str) -> bool:
        """Promote model from staging to production."""
        if version_id not in self._model_cache:
            return False
        
        model = self._model_cache[version_id]
        if model.status != ModelStatus.STAGING:
            logger.warning(f"Cannot promote model {version_id} - not in staging status")
            return False
        
        # Demote current production model
        current_prod = await self.get_latest_model(model.model_type, ModelStatus.PRODUCTION)
        if current_prod:
            await self.update_model_status(current_prod.version_id, ModelStatus.DEPRECATED)
        
        # Promote new model
        await self.update_model_status(version_id, ModelStatus.PRODUCTION)
        
        logger.info(f"Promoted model {version_id} to production")
        return True
    
    async def rollback_model(self, model_type: ModelType) -> bool:
        """Rollback to previous production model."""
        # Get current production model
        current_prod = await self.get_latest_model(model_type, ModelStatus.PRODUCTION)
        if not current_prod:
            logger.warning(f"No production model found for {model_type.value}")
            return False
        
        # Find previous production model (now deprecated)
        deprecated_models = [
            model for model in self._model_cache.values()
            if (model.model_type == model_type and 
                model.status == ModelStatus.DEPRECATED and
                model.created_at < current_prod.created_at)
        ]
        
        if not deprecated_models:
            logger.warning(f"No previous model found for rollback of {model_type.value}")
            return False
        
        # Get most recent deprecated model
        previous_model = max(deprecated_models, key=lambda m: m.created_at)
        
        # Perform rollback
        await self.update_model_status(current_prod.version_id, ModelStatus.DEPRECATED)
        await self.update_model_status(previous_model.version_id, ModelStatus.PRODUCTION)
        
        logger.info(f"Rolled back {model_type.value} from {current_prod.version_number} to {previous_model.version_number}")
        return True
    
    async def delete_model(self, version_id: str) -> bool:
        """Delete model version (only if not in production)."""
        if version_id not in self._model_cache:
            return False
        
        model = self._model_cache[version_id]
        if model.status == ModelStatus.PRODUCTION:
            logger.warning(f"Cannot delete production model {version_id}")
            return False
        
        # Remove from cache and save
        del self._model_cache[version_id]
        self._save_registry()
        
        # Clean up files
        try:
            if os.path.exists(model.model_path):
                os.remove(model.model_path)
            if os.path.exists(model.config_path):
                os.remove(model.config_path)
        except Exception as e:
            logger.error(f"Failed to clean up model files: {e}")
        
        logger.info(f"Deleted model {version_id}")
        return True


class ABTestManager:
    """Manages A/B testing for model deployments."""
    
    def __init__(self, model_registry: ModelRegistry):
        self.model_registry = model_registry
        self._active_tests: Dict[str, ABTestConfig] = {}
        self._test_results: Dict[str, Dict[str, Any]] = {}
    
    async def create_ab_test(
        self,
        model_a_version: str,
        model_b_version: str,
        traffic_split: float = 0.1,
        duration_hours: int = 24,
        success_metric: str = "accuracy",
        minimum_sample_size: int = 1000,
        confidence_level: float = 0.95
    ) -> str:
        """Create new A/B test configuration."""
        
        # Validate models exist
        model_a = await self.model_registry.get_model(model_a_version)
        model_b = await self.model_registry.get_model(model_b_version)
        
        if not model_a or not model_b:
            raise ValueError("Both models must exist in registry")
        
        if model_a.model_type != model_b.model_type:
            raise ValueError("Models must be of same type for A/B testing")
        
        test_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=duration_hours)
        
        ab_test = ABTestConfig(
            test_id=test_id,
            model_a_version=model_a_version,
            model_b_version=model_b_version,
            traffic_split=traffic_split,
            start_time=start_time,
            end_time=end_time,
            success_metric=success_metric,
            minimum_sample_size=minimum_sample_size,
            confidence_level=confidence_level,
            status="active"
        )
        
        self._active_tests[test_id] = ab_test
        self._test_results[test_id] = {
            "model_a_results": [],
            "model_b_results": [],
            "model_a_count": 0,
            "model_b_count": 0
        }
        
        logger.info(f"Created A/B test {test_id} between {model_a.version_number} and {model_b.version_number}")
        return test_id
    
    async def get_model_for_request(self, model_type: ModelType, request_id: str = None) -> str:
        """Get model version for request based on active A/B tests."""
        
        # Find active test for this model type
        active_test = None
        for test in self._active_tests.values():
            if test.status == "active" and datetime.utcnow() < test.end_time:
                model_a = await self.model_registry.get_model(test.model_a_version)
                if model_a and model_a.model_type == model_type:
                    active_test = test
                    break
        
        if not active_test:
            # No active test, return production model
            prod_model = await self.model_registry.get_latest_model(model_type, ModelStatus.PRODUCTION)
            return prod_model.version_id if prod_model else None
        
        # Determine which model to use based on traffic split
        import random
        if request_id:
            # Use deterministic routing based on request ID for consistency
            hash_val = int(hashlib.md5(request_id.encode()).hexdigest(), 16)
            use_model_b = (hash_val % 100) < (active_test.traffic_split * 100)
        else:
            # Random routing
            use_model_b = random.random() < active_test.traffic_split
        
        return active_test.model_b_version if use_model_b else active_test.model_a_version
    
    async def record_test_result(self, test_id: str, model_version: str, result: Dict[str, Any]):
        """Record result for A/B test analysis."""
        if test_id not in self._test_results:
            return
        
        test_config = self._active_tests[test_id]
        results = self._test_results[test_id]
        
        if model_version == test_config.model_a_version:
            results["model_a_results"].append(result)
            results["model_a_count"] += 1
        elif model_version == test_config.model_b_version:
            results["model_b_results"].append(result)
            results["model_b_count"] += 1
        
        # Check if we have enough samples to analyze
        total_samples = results["model_a_count"] + results["model_b_count"]
        if total_samples >= test_config.minimum_sample_size:
            await self._analyze_test_results(test_id)
    
    async def _analyze_test_results(self, test_id: str):
        """Analyze A/B test results for statistical significance."""
        test_config = self._active_tests[test_id]
        results = self._test_results[test_id]
        
        if not results["model_a_results"] or not results["model_b_results"]:
            return
        
        # Extract success metric values
        metric_name = test_config.success_metric
        
        model_a_values = [r.get(metric_name, 0) for r in results["model_a_results"]]
        model_b_values = [r.get(metric_name, 0) for r in results["model_b_results"]]
        
        # Calculate basic statistics
        model_a_mean = np.mean(model_a_values)
        model_b_mean = np.mean(model_b_values)
        model_a_std = np.std(model_a_values)
        model_b_std = np.std(model_b_values)
        
        # Perform t-test for statistical significance
        from scipy import stats
        t_stat, p_value = stats.ttest_ind(model_a_values, model_b_values)
        
        # Calculate confidence interval
        alpha = 1 - test_config.confidence_level
        is_significant = p_value < alpha
        
        # Determine winner
        winner = "model_b" if model_b_mean > model_a_mean else "model_a"
        improvement = abs(model_b_mean - model_a_mean) / model_a_mean * 100
        
        test_results = {
            "model_a_mean": model_a_mean,
            "model_b_mean": model_b_mean,
            "model_a_std": model_a_std,
            "model_b_std": model_b_std,
            "t_statistic": t_stat,
            "p_value": p_value,
            "is_significant": is_significant,
            "winner": winner,
            "improvement_percent": improvement,
            "sample_size_a": len(model_a_values),
            "sample_size_b": len(model_b_values),
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
        test_config.results = test_results
        
        logger.info(f"A/B test {test_id} analysis: {winner} wins with {improvement:.2f}% improvement (p={p_value:.4f})")
        
        # Auto-promote if significant improvement
        if is_significant and winner == "model_b" and improvement > 5:
            await self._auto_promote_winner(test_id)
    
    async def _auto_promote_winner(self, test_id: str):
        """Automatically promote winning model if configured."""
        test_config = self._active_tests[test_id]
        
        if test_config.results and test_config.results["winner"] == "model_b":
            # Promote model B to production
            await self.model_registry.update_model_status(test_config.model_b_version, ModelStatus.PRODUCTION)
            await self.model_registry.update_model_status(test_config.model_a_version, ModelStatus.DEPRECATED)
            
            test_config.status = "completed_auto_promoted"
            logger.info(f"Auto-promoted model {test_config.model_b_version} to production")
    
    async def stop_ab_test(self, test_id: str) -> Dict[str, Any]:
        """Stop A/B test and return results."""
        if test_id not in self._active_tests:
            return {}
        
        test_config = self._active_tests[test_id]
        test_config.status = "stopped"
        
        await self._analyze_test_results(test_id)
        
        return test_config.results or {}
    
    async def get_active_tests(self) -> List[ABTestConfig]:
        """Get all active A/B tests."""
        return [test for test in self._active_tests.values() if test.status == "active"]


class ModelPerformanceMonitor:
    """Monitors model performance and detects drift."""
    
    def __init__(self, model_registry: ModelRegistry):
        self.model_registry = model_registry
        self._performance_history: Dict[str, List[Dict[str, Any]]] = {}
        self._drift_detectors: Dict[str, DriftDetectionConfig] = {}
        self._alert_thresholds = {
            "accuracy_drop": 0.05,  # 5% drop in accuracy
            "latency_increase": 2.0,  # 2x increase in latency
            "error_rate_increase": 0.1  # 10% increase in error rate
        }
    
    async def setup_drift_detection(
        self,
        model_version: str,
        reference_data: Any,
        feature_importance: Dict[str, float],
        drift_threshold: float = 0.1,
        monitoring_window: timedelta = timedelta(hours=24)
    ):
        """Setup drift detection for a model."""
        
        reference_data_hash = self.model_registry._calculate_data_hash(reference_data)
        
        drift_config = DriftDetectionConfig(
            model_version=model_version,
            drift_threshold=drift_threshold,
            monitoring_window=monitoring_window,
            reference_data_hash=reference_data_hash,
            feature_importance=feature_importance,
            statistical_tests=["ks_test", "chi2_test", "psi"],
            alert_threshold=0.05
        )
        
        self._drift_detectors[model_version] = drift_config
        logger.info(f"Setup drift detection for model {model_version}")
    
    async def record_prediction(
        self,
        model_version: str,
        input_data: Dict[str, Any],
        prediction: Any,
        actual: Any = None,
        latency_ms: float = None,
        timestamp: datetime = None
    ):
        """Record model prediction for monitoring."""
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        record = {
            "timestamp": timestamp.isoformat(),
            "input_data": input_data,
            "prediction": prediction,
            "actual": actual,
            "latency_ms": latency_ms,
            "model_version": model_version
        }
        
        if model_version not in self._performance_history:
            self._performance_history[model_version] = []
        
        self._performance_history[model_version].append(record)
        
        # Check for drift if we have enough data
        if len(self._performance_history[model_version]) % 100 == 0:
            await self._check_model_drift(model_version)
    
    async def _check_model_drift(self, model_version: str):
        """Check for model drift using statistical tests."""
        
        if model_version not in self._drift_detectors:
            return
        
        drift_config = self._drift_detectors[model_version]
        recent_data = self._get_recent_data(model_version, drift_config.monitoring_window)
        
        if len(recent_data) < 100:  # Need minimum samples
            return
        
        # Extract features for drift detection
        recent_features = [record["input_data"] for record in recent_data]
        
        # Perform statistical tests
        drift_scores = await self._calculate_drift_scores(recent_features, drift_config)
        
        # Check if drift exceeds threshold
        max_drift = max(drift_scores.values())
        if max_drift > drift_config.drift_threshold:
            await self._trigger_drift_alert(model_version, drift_scores)
    
    def _get_recent_data(self, model_version: str, window: timedelta) -> List[Dict[str, Any]]:
        """Get recent prediction data within time window."""
        if model_version not in self._performance_history:
            return []
        
        cutoff_time = datetime.utcnow() - window
        recent_data = []
        
        for record in self._performance_history[model_version]:
            record_time = datetime.fromisoformat(record["timestamp"])
            if record_time >= cutoff_time:
                recent_data.append(record)
        
        return recent_data
    
    async def _calculate_drift_scores(
        self,
        recent_features: List[Dict[str, Any]],
        drift_config: DriftDetectionConfig
    ) -> Dict[str, float]:
        """Calculate drift scores using various statistical tests."""
        
        drift_scores = {}
        
        # For each feature, calculate drift score
        for feature_name, importance in drift_config.feature_importance.items():
            if not recent_features or feature_name not in recent_features[0]:
                continue
            
            recent_values = [f.get(feature_name) for f in recent_features if feature_name in f]
            
            if not recent_values:
                continue
            
            # Calculate Population Stability Index (PSI)
            psi_score = self._calculate_psi(recent_values, feature_name)
            drift_scores[f"{feature_name}_psi"] = psi_score * importance
        
        return drift_scores
    
    def _calculate_psi(self, recent_values: List[Any], feature_name: str) -> float:
        """Calculate Population Stability Index."""
        # Simplified PSI calculation
        # In practice, you'd compare against reference distribution
        
        if not recent_values:
            return 0.0
        
        # For numerical features, use binning
        if isinstance(recent_values[0], (int, float)):
            # Create bins and calculate PSI
            hist, _ = np.histogram(recent_values, bins=10)
            expected = np.full_like(hist, len(recent_values) / 10, dtype=float)
            
            # Avoid division by zero
            hist = np.where(hist == 0, 1, hist)
            expected = np.where(expected == 0, 1, expected)
            
            psi = np.sum((hist - expected) * np.log(hist / expected))
            return abs(psi)
        
        return 0.0
    
    async def _trigger_drift_alert(self, model_version: str, drift_scores: Dict[str, float]):
        """Trigger alert for model drift."""
        
        model = await self.model_registry.get_model(model_version)
        if not model:
            return
        
        alert_data = {
            "type": "model_drift",
            "model_version": model_version,
            "model_type": model.model_type.value,
            "drift_scores": drift_scores,
            "max_drift": max(drift_scores.values()),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.warning(f"Model drift detected for {model_version}: {drift_scores}")
        
        # In a real system, this would trigger retraining pipeline
        await self._trigger_retraining_pipeline(model_version, alert_data)
    
    async def _trigger_retraining_pipeline(self, model_version: str, drift_data: Dict[str, Any]):
        """Trigger automated model retraining pipeline."""
        
        logger.info(f"Triggering retraining pipeline for model {model_version}")
        
        # This would integrate with workflow orchestration system
        # For now, just log the event
        retraining_config = {
            "model_version": model_version,
            "trigger_reason": "drift_detection",
            "drift_data": drift_data,
            "scheduled_at": datetime.utcnow().isoformat()
        }
        
        # Save retraining request
        retraining_file = self.model_registry.registry_path / f"retraining_{model_version}_{int(time.time())}.json"
        with open(retraining_file, 'w') as f:
            json.dump(retraining_config, f, indent=2)
    
    async def get_model_performance_summary(self, model_version: str, days: int = 7) -> Dict[str, Any]:
        """Get performance summary for a model."""
        
        if model_version not in self._performance_history:
            return {}
        
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        recent_records = []
        
        for record in self._performance_history[model_version]:
            record_time = datetime.fromisoformat(record["timestamp"])
            if record_time >= cutoff_time:
                recent_records.append(record)
        
        if not recent_records:
            return {}
        
        # Calculate performance metrics
        predictions = [r["prediction"] for r in recent_records if r.get("actual") is not None]
        actuals = [r["actual"] for r in recent_records if r.get("actual") is not None]
        latencies = [r["latency_ms"] for r in recent_records if r.get("latency_ms") is not None]
        
        summary = {
            "total_predictions": len(recent_records),
            "predictions_with_ground_truth": len(predictions),
            "average_latency_ms": np.mean(latencies) if latencies else None,
            "p95_latency_ms": np.percentile(latencies, 95) if latencies else None,
            "error_rate": 0.0  # Would calculate based on actual errors
        }
        
        # Calculate accuracy if we have ground truth
        if predictions and actuals:
            if isinstance(predictions[0], (int, float)):
                # Regression metrics
                mse = np.mean([(p - a) ** 2 for p, a in zip(predictions, actuals)])
                summary["mse"] = mse
                summary["rmse"] = np.sqrt(mse)
            else:
                # Classification metrics
                accuracy = accuracy_score(actuals, predictions)
                summary["accuracy"] = accuracy
        
        return summary


class ModelGovernanceManager:
    """Main class that orchestrates model governance and lifecycle management."""
    
    def __init__(self, registry_path: str = "models", mlflow_tracking_uri: str = "sqlite:///mlflow.db"):
        self.model_registry = ModelRegistry(registry_path, mlflow_tracking_uri)
        self.ab_test_manager = ABTestManager(self.model_registry)
        self.performance_monitor = ModelPerformanceMonitor(self.model_registry)
        
        # Background tasks
        self._monitoring_tasks = []
        self._is_running = False
    
    async def start_monitoring(self):
        """Start background monitoring tasks."""
        if self._is_running:
            return
        
        self._is_running = True
        
        # Start periodic tasks
        self._monitoring_tasks = [
            asyncio.create_task(self._periodic_health_check()),
            asyncio.create_task(self._periodic_ab_test_analysis()),
            asyncio.create_task(self._periodic_performance_analysis())
        ]
        
        logger.info("Started model governance monitoring")
    
    async def stop_monitoring(self):
        """Stop background monitoring tasks."""
        self._is_running = False
        
        for task in self._monitoring_tasks:
            task.cancel()
        
        await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        logger.info("Stopped model governance monitoring")
    
    async def _periodic_health_check(self):
        """Periodic health check for all production models."""
        while self._is_running:
            try:
                production_models = await self.model_registry.list_models(status=ModelStatus.PRODUCTION)
                
                for model in production_models:
                    # Check model file integrity
                    if not os.path.exists(model.model_path):
                        logger.error(f"Production model file missing: {model.model_path}")
                        await self.model_registry.update_model_status(model.version_id, ModelStatus.FAILED)
                    
                    # Verify model hash
                    current_hash = self.model_registry._calculate_model_hash(model.model_path)
                    if current_hash != model.model_hash:
                        logger.error(f"Model file corrupted: {model.model_path}")
                        await self.model_registry.update_model_status(model.version_id, ModelStatus.FAILED)
                
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                logger.error(f"Error in health check: {e}")
                await asyncio.sleep(300)  # Retry in 5 minutes
    
    async def _periodic_ab_test_analysis(self):
        """Periodic analysis of active A/B tests."""
        while self._is_running:
            try:
                active_tests = await self.ab_test_manager.get_active_tests()
                
                for test in active_tests:
                    # Check if test should end
                    if datetime.utcnow() >= test.end_time:
                        await self.ab_test_manager.stop_ab_test(test.test_id)
                
                await asyncio.sleep(1800)  # Check every 30 minutes
                
            except Exception as e:
                logger.error(f"Error in A/B test analysis: {e}")
                await asyncio.sleep(300)
    
    async def _periodic_performance_analysis(self):
        """Periodic performance analysis for all models."""
        while self._is_running:
            try:
                all_models = await self.model_registry.list_models()
                
                for model in all_models:
                    if model.status in [ModelStatus.PRODUCTION, ModelStatus.STAGING]:
                        summary = await self.performance_monitor.get_model_performance_summary(model.version_id)
                        
                        # Check for performance degradation
                        if summary.get("accuracy") and summary["accuracy"] < model.metrics.accuracy - 0.05:
                            logger.warning(f"Performance degradation detected for model {model.version_id}")
                
                await asyncio.sleep(7200)  # Check every 2 hours
                
            except Exception as e:
                logger.error(f"Error in performance analysis: {e}")
                await asyncio.sleep(300)
    
    async def get_governance_dashboard_data(self) -> Dict[str, Any]:
        """Get data for governance dashboard."""
        
        # Model statistics
        all_models = await self.model_registry.list_models()
        model_stats = {
            "total_models": len(all_models),
            "production_models": len([m for m in all_models if m.status == ModelStatus.PRODUCTION]),
            "staging_models": len([m for m in all_models if m.status == ModelStatus.STAGING]),
            "deprecated_models": len([m for m in all_models if m.status == ModelStatus.DEPRECATED])
        }
        
        # A/B test statistics
        active_tests = await self.ab_test_manager.get_active_tests()
        ab_test_stats = {
            "active_tests": len(active_tests),
            "tests_by_model_type": {}
        }
        
        for test in active_tests:
            model_a = await self.model_registry.get_model(test.model_a_version)
            if model_a:
                model_type = model_a.model_type.value
                ab_test_stats["tests_by_model_type"][model_type] = ab_test_stats["tests_by_model_type"].get(model_type, 0) + 1
        
        # Recent performance summaries
        production_models = await self.model_registry.list_models(status=ModelStatus.PRODUCTION)
        performance_summaries = {}
        
        for model in production_models[:5]:  # Top 5 production models
            summary = await self.performance_monitor.get_model_performance_summary(model.version_id)
            performance_summaries[model.version_id] = {
                "model_type": model.model_type.value,
                "version": model.version_number,
                "summary": summary
            }
        
        return {
            "model_statistics": model_stats,
            "ab_test_statistics": ab_test_stats,
            "performance_summaries": performance_summaries,
            "last_updated": datetime.utcnow().isoformat()
        }