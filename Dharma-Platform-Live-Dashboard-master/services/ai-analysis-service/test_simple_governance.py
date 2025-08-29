"""Simple test for model governance functionality."""

import sys
import os
import tempfile
import asyncio

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from core.model_registry import ModelRegistry, ModelType, ModelStatus, ModelMetrics
    print("✓ Successfully imported model registry classes")
except ImportError as e:
    print(f"✗ Failed to import model registry: {e}")
    sys.exit(1)

try:
    from core.governance_config import ModelGovernanceConfig, load_governance_config
    print("✓ Successfully imported governance config")
except ImportError as e:
    print(f"✗ Failed to import governance config: {e}")
    sys.exit(1)

async def test_basic_functionality():
    """Test basic model registry functionality."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        # Test model registry creation
        try:
            registry = ModelRegistry(temp_dir)
            print("✓ Successfully created model registry")
        except Exception as e:
            print(f"✗ Failed to create model registry: {e}")
            return False
        
        # Test model metrics creation
        try:
            metrics = ModelMetrics(
                accuracy=0.85,
                precision=0.82,
                recall=0.88,
                f1_score=0.85
            )
            print("✓ Successfully created model metrics")
        except Exception as e:
            print(f"✗ Failed to create model metrics: {e}")
            return False
        
        # Test configuration loading
        try:
            config = load_governance_config()
            print("✓ Successfully loaded governance config")
        except Exception as e:
            print(f"✗ Failed to load governance config: {e}")
            return False
        
        print("✓ All basic tests passed!")
        return True

if __name__ == "__main__":
    success = asyncio.run(test_basic_functionality())
    if success:
        print("\n🎉 Model governance implementation is working correctly!")
    else:
        print("\n❌ Model governance implementation has issues")
        sys.exit(1)