#!/usr/bin/env python3
"""Unit test runner for Project Dharma."""

import sys
import os
import pytest
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "shared"))

def run_unit_tests():
    """Run all unit tests with proper configuration."""
    
    # Test configuration
    test_args = [
        str(Path(__file__).parent / "unit"),  # Test directory
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--strict-markers",  # Strict marker checking
        "--disable-warnings",  # Disable warnings for cleaner output
        "-x",  # Stop on first failure
        "--asyncio-mode=auto",  # Auto async mode
    ]
    
    # Add coverage if available
    try:
        import pytest_cov
        test_args.extend([
            "--cov=shared",
            "--cov=services",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-fail-under=80"
        ])
        print("Running tests with coverage...")
    except ImportError:
        print("Running tests without coverage (install pytest-cov for coverage reports)...")
    
    # Run tests
    print("=" * 60)
    print("Running Project Dharma Unit Tests")
    print("=" * 60)
    
    exit_code = pytest.main(test_args)
    
    if exit_code == 0:
        print("\n" + "=" * 60)
        print("✅ All unit tests passed!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Some unit tests failed!")
        print("=" * 60)
    
    return exit_code


def run_specific_test_module(module_name):
    """Run tests for a specific module."""
    
    test_file = Path(__file__).parent / "unit" / f"test_{module_name}.py"
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return 1
    
    test_args = [
        str(test_file),
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ]
    
    print(f"Running tests for module: {module_name}")
    print("=" * 60)
    
    return pytest.main(test_args)


def run_test_categories():
    """Run tests by category."""
    
    categories = {
        "data_models": "test_data_models.py",
        "ai_analysis": "test_ai_analysis.py", 
        "alert_management": "test_alert_management.py",
        "authentication": "test_authentication.py"
    }
    
    print("Available test categories:")
    for i, (category, filename) in enumerate(categories.items(), 1):
        print(f"  {i}. {category} ({filename})")
    
    try:
        choice = input("\nEnter category number (or 'all' for all tests): ").strip()
        
        if choice.lower() == 'all':
            return run_unit_tests()
        
        choice_num = int(choice)
        if 1 <= choice_num <= len(categories):
            category_name = list(categories.keys())[choice_num - 1]
            return run_specific_test_module(category_name)
        else:
            print("❌ Invalid choice!")
            return 1
            
    except (ValueError, KeyboardInterrupt):
        print("\n❌ Invalid input or cancelled!")
        return 1


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test module
        module_name = sys.argv[1]
        exit_code = run_specific_test_module(module_name)
    else:
        # Interactive mode or run all tests
        if sys.stdin.isatty():  # Interactive terminal
            exit_code = run_test_categories()
        else:  # Non-interactive (CI/CD)
            exit_code = run_unit_tests()
    
    sys.exit(exit_code)