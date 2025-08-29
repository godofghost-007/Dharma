"""
Data Anonymization Utilities

Provides comprehensive data anonymization and pseudonymization capabilities
for protecting sensitive information while maintaining data utility.
"""

import re
import hashlib
import secrets
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AnonymizationMethod(Enum):
    """Available anonymization methods"""
    REDACTION = "redaction"
    PSEUDONYMIZATION = "pseudonymization"
    GENERALIZATION = "generalization"
    SUPPRESSION = "suppression"
    NOISE_ADDITION = "noise_addition"


@dataclass
class AnonymizationRule:
    """Configuration for field anonymization"""
    field_name: str
    method: AnonymizationMethod
    replacement_value: Optional[str] = None
    preserve_format: bool = False
    salt: Optional[str] = None


@dataclass
class AnonymizationConfig:
    """Configuration for data anonymization"""
    rules: List[AnonymizationRule]
    preserve_structure: bool = True
    audit_trail: bool = True
    reversible: bool = False


class DataAnonymizer:
    """
    Comprehensive data anonymization utility for protecting sensitive information
    """
    
    def __init__(self, config: AnonymizationConfig):
        self.config = config
        self.patterns = self._compile_patterns()
        self.pseudonym_cache = {}
        
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for common sensitive data types"""
        return {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone': re.compile(r'\b(?:\+91|91)?[-.\s]?(?:\d{5}[-.\s]?\d{5}|\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b'),
            'aadhaar': re.compile(r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b'),
            'pan': re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b'),
            'ip_address': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
            'url': re.compile(r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'),
            'credit_card': re.compile(r'\b(?:\d{4}[-.\s]?){3}\d{4}\b')
        }
    
    async def anonymize_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize a document based on configured rules
        
        Args:
            document: Document to anonymize
            
        Returns:
            Anonymized document
        """
        try:
            anonymized = document.copy() if self.config.preserve_structure else {}
            audit_info = {
                'original_id': document.get('_id'),
                'anonymized_at': datetime.utcnow(),
                'fields_processed': []
            }
            
            for rule in self.config.rules:
                if rule.field_name in document:
                    original_value = document[rule.field_name]
                    anonymized_value = await self._apply_anonymization_rule(
                        original_value, rule
                    )
                    anonymized[rule.field_name] = anonymized_value
                    audit_info['fields_processed'].append(rule.field_name)
            
            # Apply automatic pattern-based anonymization
            anonymized = await self._apply_pattern_anonymization(anonymized)
            
            if self.config.audit_trail:
                anonymized['_anonymization_audit'] = audit_info
                
            logger.info(f"Document anonymized: {len(audit_info['fields_processed'])} fields processed")
            return anonymized
            
        except Exception as e:
            logger.error(f"Error anonymizing document: {e}")
            raise
    
    async def _apply_anonymization_rule(self, value: Any, rule: AnonymizationRule) -> Any:
        """Apply specific anonymization rule to a value"""
        if value is None:
            return None
            
        if rule.method == AnonymizationMethod.REDACTION:
            return rule.replacement_value or "[REDACTED]"
            
        elif rule.method == AnonymizationMethod.PSEUDONYMIZATION:
            return await self._pseudonymize_value(value, rule.salt)
            
        elif rule.method == AnonymizationMethod.GENERALIZATION:
            return await self._generalize_value(value)
            
        elif rule.method == AnonymizationMethod.SUPPRESSION:
            return None
            
        elif rule.method == AnonymizationMethod.NOISE_ADDITION:
            return await self._add_noise(value)
            
        return value
    
    async def _pseudonymize_value(self, value: str, salt: Optional[str] = None) -> str:
        """Create consistent pseudonym for a value"""
        if value in self.pseudonym_cache:
            return self.pseudonym_cache[value]
            
        # Create deterministic hash for consistency
        hash_input = f"{value}{salt or 'default_salt'}"
        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
        pseudonym = f"USER_{hash_value.upper()}"
        
        self.pseudonym_cache[value] = pseudonym
        return pseudonym
    
    async def _generalize_value(self, value: Any) -> Any:
        """Generalize value to reduce specificity"""
        if isinstance(value, str):
            # Generalize dates to year only
            date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
            if date_pattern.match(value):
                return value[:4] + "-XX-XX"
                
            # Generalize locations to region level
            if len(value) > 10:
                return value[:5] + "..."
                
        elif isinstance(value, (int, float)):
            # Round numbers to reduce precision
            if isinstance(value, float):
                return round(value, 1)
            else:
                return (value // 10) * 10
                
        return value
    
    async def _add_noise(self, value: Any) -> Any:
        """Add statistical noise to numerical values"""
        if isinstance(value, (int, float)):
            noise = secrets.randbelow(10) - 5  # Random noise between -5 and 5
            return value + noise
        return value
    
    async def _apply_pattern_anonymization(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Apply pattern-based anonymization to text fields"""
        for key, value in document.items():
            if isinstance(value, str):
                # Anonymize emails
                value = self.patterns['email'].sub('[EMAIL]', value)
                
                # Anonymize phone numbers
                value = self.patterns['phone'].sub('[PHONE]', value)
                
                # Anonymize Aadhaar numbers
                value = self.patterns['aadhaar'].sub('[AADHAAR]', value)
                
                # Anonymize PAN numbers
                value = self.patterns['pan'].sub('[PAN]', value)
                
                # Anonymize IP addresses
                value = self.patterns['ip_address'].sub('[IP_ADDRESS]', value)
                
                # Anonymize URLs
                value = self.patterns['url'].sub('[URL]', value)
                
                document[key] = value
                
        return document
    
    async def anonymize_batch(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Anonymize a batch of documents
        
        Args:
            documents: List of documents to anonymize
            
        Returns:
            List of anonymized documents
        """
        anonymized_docs = []
        
        for doc in documents:
            try:
                anonymized_doc = await self.anonymize_document(doc)
                anonymized_docs.append(anonymized_doc)
            except Exception as e:
                logger.error(f"Error anonymizing document {doc.get('_id', 'unknown')}: {e}")
                # Continue with other documents
                
        logger.info(f"Batch anonymization completed: {len(anonymized_docs)}/{len(documents)} documents processed")
        return anonymized_docs
    
    def create_anonymization_report(self, original_count: int, anonymized_count: int) -> Dict[str, Any]:
        """Create anonymization process report"""
        return {
            'timestamp': datetime.utcnow(),
            'original_documents': original_count,
            'anonymized_documents': anonymized_count,
            'success_rate': (anonymized_count / original_count) * 100 if original_count > 0 else 0,
            'rules_applied': len(self.config.rules),
            'methods_used': [rule.method.value for rule in self.config.rules]
        }


class PersonalDataDetector:
    """Detect personal data in content for classification"""
    
    def __init__(self):
        self.patterns = {
            'high_sensitivity': [
                r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b',  # Aadhaar
                r'\b[A-Z]{5}\d{4}[A-Z]\b',  # PAN
                r'\b(?:\d{4}[-.\s]?){3}\d{4}\b'  # Credit card
            ],
            'medium_sensitivity': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
                r'\b(?:\+91|91)?[-.\s]?(?:\d{5}[-.\s]?\d{5}|\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b'  # Phone
            ],
            'low_sensitivity': [
                r'\b(?:\d{1,3}\.){3}\d{1,3}\b',  # IP address
                r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'  # URL
            ]
        }
        
        self.compiled_patterns = {
            level: [re.compile(pattern) for pattern in patterns]
            for level, patterns in self.patterns.items()
        }
    
    def detect_personal_data(self, content: str) -> Dict[str, List[str]]:
        """
        Detect personal data in content
        
        Args:
            content: Text content to analyze
            
        Returns:
            Dictionary with sensitivity levels and detected patterns
        """
        detected = {
            'high_sensitivity': [],
            'medium_sensitivity': [],
            'low_sensitivity': []
        }
        
        for level, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(content)
                if matches:
                    detected[level].extend(matches)
        
        return detected
    
    def calculate_sensitivity_score(self, content: str) -> float:
        """
        Calculate overall sensitivity score for content
        
        Args:
            content: Text content to analyze
            
        Returns:
            Sensitivity score between 0 and 1
        """
        detected = self.detect_personal_data(content)
        
        score = 0.0
        score += len(detected['high_sensitivity']) * 0.8
        score += len(detected['medium_sensitivity']) * 0.5
        score += len(detected['low_sensitivity']) * 0.2
        
        # Normalize to 0-1 range
        return min(score / 10.0, 1.0)