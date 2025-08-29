"""
Simple test for data governance system
"""

import asyncio
from datetime import datetime, timedelta

from shared.governance.data_anonymizer import (
    DataAnonymizer, AnonymizationConfig, AnonymizationRule, 
    AnonymizationMethod, PersonalDataDetector
)
from shared.governance.data_classifier import DataClassifier, SensitivityLevel
from shared.governance.config import GovernanceConfig


async def test_data_anonymization():
    """Test basic data anonymization"""
    print("Testing Data Anonymization...")
    
    # Create anonymization configuration
    config = AnonymizationConfig(
        rules=[
            AnonymizationRule("email", AnonymizationMethod.REDACTION, "[EMAIL_REDACTED]"),
            AnonymizationRule("user_id", AnonymizationMethod.PSEUDONYMIZATION)
        ]
    )
    
    anonymizer = DataAnonymizer(config)
    
    # Test document
    document = {
        "_id": "test_doc",
        "email": "user@example.com",
        "user_id": "user123",
        "content": "Contact me at john@test.com or call 9876543210"
    }
    
    # Anonymize document
    result = await anonymizer.anonymize_document(document)
    
    # Verify anonymization
    assert result["email"] == "[EMAIL_REDACTED]"
    assert result["user_id"].startswith("USER_")
    assert "[EMAIL]" in result["content"]
    assert "[PHONE]" in result["content"]
    assert "_anonymization_audit" in result
    
    print("✓ Data anonymization test passed")


async def test_data_classification():
    """Test basic data classification"""
    print("Testing Data Classification...")
    
    classifier = DataClassifier()
    
    # Test documents
    documents = [
        {
            "_id": "doc1",
            "content": "This is public information"
        },
        {
            "_id": "doc2", 
            "content": "Email: user@test.com, Phone: 9876543210"
        },
        {
            "_id": "doc3",
            "content": "Aadhaar: 1234 5678 9012, PAN: ABCDE1234F"
        }
    ]
    
    # Classify documents
    for doc in documents:
        result = await classifier.classify_document(doc)
        
        print(f"Document {doc['_id']}: {result.sensitivity_level.value} "
              f"(confidence: {result.confidence_score:.2f})")
        
        # Verify classification logic
        if "public information" in doc["content"]:
            assert result.sensitivity_level == SensitivityLevel.PUBLIC
        elif "Aadhaar" in doc["content"] or "PAN" in doc["content"]:
            assert result.sensitivity_level == SensitivityLevel.RESTRICTED
        elif "Email" in doc["content"] or "Phone" in doc["content"]:
            assert result.sensitivity_level in [SensitivityLevel.CONFIDENTIAL, SensitivityLevel.RESTRICTED]
    
    print("✓ Data classification test passed")


def test_personal_data_detection():
    """Test personal data detection"""
    print("Testing Personal Data Detection...")
    
    detector = PersonalDataDetector()
    
    test_content = """
    Contact information:
    Email: john.doe@example.com
    Phone: +91-9876543210
    Aadhaar: 1234 5678 9012
    PAN: ABCDE1234F
    Credit Card: 1234 5678 9012 3456
    """
    
    detected = detector.detect_personal_data(test_content)
    sensitivity_score = detector.calculate_sensitivity_score(test_content)
    
    # Verify detection
    assert len(detected['high_sensitivity']) > 0  # Should detect Aadhaar, PAN, Credit Card
    assert len(detected['medium_sensitivity']) > 0  # Should detect Email, Phone
    assert sensitivity_score > 0.0  # Should have some sensitivity score
    
    print(f"Detected patterns: {detected}")
    print(f"Sensitivity score: {sensitivity_score:.2f}")
    print("✓ Personal data detection test passed")


def test_governance_config():
    """Test governance configuration"""
    print("Testing Governance Configuration...")
    
    config = GovernanceConfig()
    
    # Test default values
    assert config.anonymization.enabled is True
    assert config.classification.enabled is True
    assert config.retention.enabled is True
    
    # Test configuration validation
    issues = config.validate_configuration()
    print(f"Configuration issues: {issues}")
    
    # Test export/import
    exported = config.export_configuration()
    assert 'mode' in exported
    assert 'anonymization' in exported
    assert 'classification' in exported
    
    print("✓ Governance configuration test passed")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("DATA GOVERNANCE SYSTEM - SIMPLE TESTS")
    print("=" * 60)
    
    try:
        await test_data_anonymization()
        await test_data_classification()
        test_personal_data_detection()
        test_governance_config()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED SUCCESSFULLY!")
        print("✓ Data Anonymization")
        print("✓ Data Classification") 
        print("✓ Personal Data Detection")
        print("✓ Governance Configuration")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())