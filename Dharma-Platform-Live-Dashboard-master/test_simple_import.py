#!/usr/bin/env python3
"""Simple import test"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing imports...")

try:
    print("1. Testing basic module import...")
    import shared.tracing.correlation as corr_module
    print(f"   Module imported: {corr_module}")
    print(f"   Module attributes: {[attr for attr in dir(corr_module) if not attr.startswith('_')]}")
    
    print("2. Testing specific class import...")
    exec("from shared.tracing.correlation import CorrelationContext")
    print("   CorrelationContext imported successfully")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()