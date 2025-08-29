"""Basic test for model governance functionality without complex dependencies."""

import asyncio
import json
import os
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification


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


class SimpleModelRegistry:
    """Simplified model registry for testing."""
    
    def __init__(self, registry_path: str = "models"):
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(exist_ok=True)
        self._model_cache: Dict[str, ModelVersion] = {}
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
                    
                print(f"Loaded {len(self._model_cache)} models from registry")
            except Exception as e:
                print(f"Failed to load model registry: {e}")
    
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
            print(f"Failed to save model registry: {e}")
    
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
        
        print(f"Registered model {model_type.value} version {version_number} with ID {version_id}")
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
    
    async def get_model(self, version_id: str) -> Optional[ModelVersion]:
        """Get model version by ID."""
        return self._model_cache.get(version_id)
    
    async def list_models(
        self,
        model_type: Optional[ModelType] = None,
        status: Optional[ModelStatus] = None
    ) -> List[ModelVersion]:
        """List models with optional filtering."""
        models = list(self._model_cache.values())
        
        if model_type:
            models = [m for m in models if m.model_type == model_type]
        
        if status:
            models = [m for m in models if m.status == status]
        
        return sorted(models, key=lambda m: m.created_at, reverse=True)
    
    async def update_model_status(self, version_id: str, status: ModelStatus) -> bool:
        """Update model status."""
        if version_id not in self._model_cache:
            return False
        
        model = self._model_cache[version_id]
        model.status = status
        model.updated_at = datetime.utcnow()
        
        self._save_registry()
        print(f"Updated model {version_id} status to {status.value}")
        return True


async def test_model_governance():
    """Test basic model governance functionality."""
    
    print("🚀 Starting Model Governance Test")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        # Create sample model
        print("\n1. Creating sample model...")
        X, y = make_classification(n_samples=1000, n_features=20, n_classes=2, random_state=42)
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)
        
        # Save model
        model_path = os.path.join(temp_dir, "sentiment_model.pkl")
        joblib.dump(model, model_path)
        
        # Create config
        config_path = os.path.join(temp_dir, "sentiment_config.json")
        config = {
            "model_type": "sentiment_analysis",
            "hyperparameters": {
                "n_estimators": 10,
                "random_state": 42
            },
            "training_info": {
                "samples": 1000,
                "features": 20,
                "classes": 2
            }
        }
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print("✓ Sample model created and saved")
        
        # Test model registry
        print("\n2. Testing model registry...")
        registry = SimpleModelRegistry(temp_dir)
        
        # Calculate metrics
        y_pred = model.predict(X)
        metrics = ModelMetrics(
            accuracy=accuracy_score(y, y_pred),
            precision=precision_score(y, y_pred, average='weighted'),
            recall=recall_score(y, y_pred, average='weighted'),
            f1_score=f1_score(y, y_pred, average='weighted')
        )
        
        print(f"Model metrics: Accuracy={metrics.accuracy:.3f}, F1={metrics.f1_score:.3f}")
        
        # Register model
        version_id = await registry.register_model(
            model_type=ModelType.SENTIMENT_ANALYSIS,
            model_path=model_path,
            config_path=config_path,
            metrics=metrics,
            training_data=X,
            metadata={"experiment": "test_governance", "framework": "sklearn"},
            tags=["test", "sentiment", "v1"],
            description="Test sentiment analysis model for governance testing"
        )
        
        print(f"✓ Model registered with version ID: {version_id}")
        
        # Test model retrieval
        print("\n3. Testing model retrieval...")
        retrieved_model = await registry.get_model(version_id)
        assert retrieved_model is not None
        assert retrieved_model.model_type == ModelType.SENTIMENT_ANALYSIS
        assert retrieved_model.status == ModelStatus.VALIDATION
        print(f"✓ Retrieved model: {retrieved_model.version_number} ({retrieved_model.status.value})")
        
        # Test model status update
        print("\n4. Testing model status updates...")
        success = await registry.update_model_status(version_id, ModelStatus.STAGING)
        assert success
        
        updated_model = await registry.get_model(version_id)
        assert updated_model.status == ModelStatus.STAGING
        print("✓ Model status updated to staging")
        
        # Test model listing
        print("\n5. Testing model listing...")
        all_models = await registry.list_models()
        assert len(all_models) == 1
        
        sentiment_models = await registry.list_models(model_type=ModelType.SENTIMENT_ANALYSIS)
        assert len(sentiment_models) == 1
        
        staging_models = await registry.list_models(status=ModelStatus.STAGING)
        assert len(staging_models) == 1
        print(f"✓ Model listing works: {len(all_models)} total, {len(sentiment_models)} sentiment, {len(staging_models)} staging")
        
        # Register another model
        print("\n6. Testing multiple model versions...")
        
        # Create improved model
        improved_model = RandomForestClassifier(n_estimators=20, random_state=42)
        improved_model.fit(X, y)
        
        improved_model_path = os.path.join(temp_dir, "sentiment_model_v2.pkl")
        joblib.dump(improved_model, improved_model_path)
        
        # Calculate improved metrics
        y_pred_improved = improved_model.predict(X)
        improved_metrics = ModelMetrics(
            accuracy=accuracy_score(y, y_pred_improved),
            precision=precision_score(y, y_pred_improved, average='weighted'),
            recall=recall_score(y, y_pred_improved, average='weighted'),
            f1_score=f1_score(y, y_pred_improved, average='weighted')
        )
        
        version_id_2 = await registry.register_model(
            model_type=ModelType.SENTIMENT_ANALYSIS,
            model_path=improved_model_path,
            config_path=config_path,
            metrics=improved_metrics,
            training_data=X,
            metadata={"experiment": "test_governance_v2", "framework": "sklearn"},
            tags=["test", "sentiment", "v2", "improved"],
            description="Improved sentiment analysis model with more estimators"
        )
        
        print(f"✓ Second model registered with version ID: {version_id_2}")
        
        # Check version numbering
        model_v1 = await registry.get_model(version_id)
        model_v2 = await registry.get_model(version_id_2)
        
        print(f"Model versions: {model_v1.version_number} -> {model_v2.version_number}")
        assert model_v1.version_number == "1.0.0"
        assert model_v2.version_number == "1.0.1"
        
        # Test registry persistence
        print("\n7. Testing registry persistence...")
        registry_2 = SimpleModelRegistry(temp_dir)
        loaded_models = await registry_2.list_models()
        assert len(loaded_models) == 2
        print(f"✓ Registry persistence works: loaded {len(loaded_models)} models")
        
        print("\n🎉 All model governance tests passed!")
        
        # Print summary
        print("\n📊 Test Summary:")
        print(f"- Created {len(loaded_models)} model versions")
        print(f"- Tested model registration, retrieval, and status updates")
        print(f"- Verified version numbering and persistence")
        print(f"- Model metrics: Accuracy {metrics.accuracy:.3f} -> {improved_metrics.accuracy:.3f}")
        
        return True


if __name__ == "__main__":
    success = asyncio.run(test_model_governance())
    if success:
        print("\n✅ Model governance implementation is working correctly!")
    else:
        print("\n❌ Model governance implementation has issues")
        exit(1)