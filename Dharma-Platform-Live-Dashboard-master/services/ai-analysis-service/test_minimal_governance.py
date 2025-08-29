"""Minimal test for model governance - checking dependencies."""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Test individual imports
print("Testing individual imports...")

try:
    from enum import Enum
    print("✓ enum imported")
except ImportError as e:
    print(f"✗ enum failed: {e}")

try:
    from dataclasses import dataclass
    print("✓ dataclasses imported")
except ImportError as e:
    print(f"✗ dataclasses failed: {e}")

try:
    from datetime import datetime, timedelta
    print("✓ datetime imported")
except ImportError as e:
    print(f"✗ datetime failed: {e}")

try:
    import numpy as np
    print("✓ numpy imported")
except ImportError as e:
    print(f"✗ numpy failed: {e}")

try:
    from sklearn.metrics import accuracy_score
    print("✓ sklearn imported")
except ImportError as e:
    print(f"✗ sklearn failed: {e}")

try:
    import joblib
    print("✓ joblib imported")
except ImportError as e:
    print(f"✗ joblib failed: {e}")

try:
    import mlflow
    print("✓ mlflow imported")
except ImportError as e:
    print(f"✗ mlflow failed: {e}")

# Now try to import the file directly
print("\nTesting file import...")
try:
    import core.model_registry
    print("✓ core.model_registry module imported")
    
    # Check what's actually in the module
    print("Module contents:", dir(core.model_registry))
    
except ImportError as e:
    print(f"✗ core.model_registry failed: {e}")
except Exception as e:
    print(f"✗ Unexpected error: {e}")

print("\nDone.")