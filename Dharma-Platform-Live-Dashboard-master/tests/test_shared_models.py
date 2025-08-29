"""Tests for shared models."""

import pytest
from datetime import datetime
from shared.models.base import BaseModel, TimestampMixin


class TestModel(BaseModel):
    """Test model for validation."""
    name: str
    value: int


class TestTimestampModel(TimestampMixin):
    """Test model with timestamps."""
    name: str


def test_base_model_creation():
    """Test base model creation and validation."""
    model = TestModel(name="test", value=42)
    assert model.name == "test"
    assert model.value == 42


def test_base_model_validation():
    """Test base model validation."""
    with pytest.raises(ValueError):
        TestModel(name="test", value="invalid")


def test_timestamp_mixin():
    """Test timestamp mixin functionality."""
    model = TestTimestampModel(name="test")
    assert model.created_at is not None
    assert isinstance(model.created_at, datetime)
    assert model.updated_at is None
    
    # Test update timestamp
    model.update_timestamp()
    assert model.updated_at is not None
    assert isinstance(model.updated_at, datetime)