"""
Data Classification and Sensitivity Labeling

Provides automated data classification based on content analysis
and sensitivity scoring for compliance and governance.
"""

import re
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SensitivityLevel(Enum):
    """Data sensitivity levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DataType(Enum):
    """Types of data for classification"""
    PERSONAL_IDENTIFIABLE = "personal_identifiable"
    FINANCIAL = "financial"
    HEALTH = "health"
    BIOMETRIC = "biometric"
    LOCATION = "location"
    COMMUNICATION = "communication"
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"


@dataclass
class ClassificationRule:
    """Rule for data classification"""
    name: str
    data_type: DataType
    sensitivity_level: SensitivityLevel
    patterns: List[str]
    keywords: List[str]
    weight: float = 1.0
    enabled: bool = True


@dataclass
class ClassificationResult:
    """Result of data classification"""
    sensitivity_level: SensitivityLevel
    data_types: List[DataType]
    confidence_score: float
    detected_patterns: Dict[str, List[str]]
    recommendations: List[str]
    classification_timestamp: datetime


class DataClassifier:
    """
    Automated data classification and sensitivity labeling system
    """
    
    def __init__(self):
        self.rules: List[ClassificationRule] = []
        self.patterns = self._compile_classification_patterns()
        self._initialize_default_rules()
    
    def _compile_classification_patterns(self) -> Dict[str, Dict[str, re.Pattern]]:
        """Compile regex patterns for data classification"""
        return {
            'personal_identifiable': {
                'aadhaar': re.compile(r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b'),
                'pan': re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b'),
                'passport': re.compile(r'\b[A-Z]\d{7}\b'),
                'voter_id': re.compile(r'\b[A-Z]{3}\d{7}\b'),
                'driving_license': re.compile(r'\b[A-Z]{2}\d{13}\b'),
                'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
                'phone': re.compile(r'\b(?:\+91|91)?[-.\s]?(?:\d{5}[-.\s]?\d{5}|\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b')
            },
            'financial': {
                'credit_card': re.compile(r'\b(?:\d{4}[-.\s]?){3}\d{4}\b'),
                'bank_account': re.compile(r'\b\d{9,18}\b'),
                'ifsc': re.compile(r'\b[A-Z]{4}0[A-Z0-9]{6}\b'),
                'upi_id': re.compile(r'\b[\w.-]+@[\w.-]+\b')
            },
            'location': {
                'coordinates': re.compile(r'\b-?\d{1,3}\.\d+,\s*-?\d{1,3}\.\d+\b'),
                'pincode': re.compile(r'\b\d{6}\b'),
                'ip_address': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
            },
            'technical': {
                'api_key': re.compile(r'\b[A-Za-z0-9]{32,}\b'),
                'token': re.compile(r'\b[A-Za-z0-9+/]{40,}={0,2}\b'),
                'hash': re.compile(r'\b[a-f0-9]{32,64}\b'),
                'url': re.compile(r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?')
            }
        }
    
    def _initialize_default_rules(self):
        """Initialize default classification rules"""
        default_rules = [
            # Personal Identifiable Information
            ClassificationRule(
                name="aadhaar_detection",
                data_type=DataType.PERSONAL_IDENTIFIABLE,
                sensitivity_level=SensitivityLevel.RESTRICTED,
                patterns=[r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b'],
                keywords=['aadhaar', 'aadhar', 'uid'],
                weight=2.0
            ),
            ClassificationRule(
                name="pan_detection",
                data_type=DataType.PERSONAL_IDENTIFIABLE,
                sensitivity_level=SensitivityLevel.RESTRICTED,
                patterns=[r'\b[A-Z]{5}\d{4}[A-Z]\b'],
                keywords=['pan', 'permanent account number'],
                weight=2.0
            ),
            ClassificationRule(
                name="email_detection",
                data_type=DataType.PERSONAL_IDENTIFIABLE,
                sensitivity_level=SensitivityLevel.CONFIDENTIAL,
                patterns=[r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'],
                keywords=['email', 'e-mail'],
                weight=1.5
            ),
            ClassificationRule(
                name="phone_detection",
                data_type=DataType.PERSONAL_IDENTIFIABLE,
                sensitivity_level=SensitivityLevel.CONFIDENTIAL,
                patterns=[r'\b(?:\+91|91)?[-.\s]?(?:\d{5}[-.\s]?\d{5}|\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b'],
                keywords=['phone', 'mobile', 'contact'],
                weight=1.5
            ),
            
            # Financial Information
            ClassificationRule(
                name="credit_card_detection",
                data_type=DataType.FINANCIAL,
                sensitivity_level=SensitivityLevel.RESTRICTED,
                patterns=[r'\b(?:\d{4}[-.\s]?){3}\d{4}\b'],
                keywords=['credit card', 'debit card', 'card number'],
                weight=2.0
            ),
            ClassificationRule(
                name="bank_account_detection",
                data_type=DataType.FINANCIAL,
                sensitivity_level=SensitivityLevel.RESTRICTED,
                patterns=[r'\b\d{9,18}\b'],
                keywords=['bank account', 'account number', 'savings account'],
                weight=1.8
            ),
            
            # Location Information
            ClassificationRule(
                name="coordinates_detection",
                data_type=DataType.LOCATION,
                sensitivity_level=SensitivityLevel.CONFIDENTIAL,
                patterns=[r'\b-?\d{1,3}\.\d+,\s*-?\d{1,3}\.\d+\b'],
                keywords=['coordinates', 'latitude', 'longitude', 'gps'],
                weight=1.5
            ),
            ClassificationRule(
                name="ip_address_detection",
                data_type=DataType.TECHNICAL,
                sensitivity_level=SensitivityLevel.INTERNAL,
                patterns=[r'\b(?:\d{1,3}\.){3}\d{1,3}\b'],
                keywords=['ip address', 'ip'],
                weight=1.0
            ),
            
            # Technical Information
            ClassificationRule(
                name="api_key_detection",
                data_type=DataType.TECHNICAL,
                sensitivity_level=SensitivityLevel.RESTRICTED,
                patterns=[r'\b[A-Za-z0-9]{32,}\b'],
                keywords=['api key', 'secret key', 'access token'],
                weight=2.0
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: ClassificationRule):
        """Add a classification rule"""
        self.rules.append(rule)
        logger.info(f"Added classification rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove a classification rule"""
        self.rules = [r for r in self.rules if r.name != rule_name]
        logger.info(f"Removed classification rule: {rule_name}")
    
    async def classify_document(self, document: Dict[str, Any]) -> ClassificationResult:
        """
        Classify a document and determine its sensitivity level
        
        Args:
            document: Document to classify
            
        Returns:
            Classification result with sensitivity level and recommendations
        """
        try:
            detected_patterns = {}
            data_types = set()
            total_score = 0.0
            max_sensitivity = SensitivityLevel.PUBLIC
            
            # Convert document to text for analysis
            text_content = self._extract_text_content(document)
            
            # Apply classification rules
            for rule in self.rules:
                if not rule.enabled:
                    continue
                
                rule_score = 0.0
                rule_patterns = []
                
                # Check patterns
                for pattern in rule.patterns:
                    matches = re.findall(pattern, text_content, re.IGNORECASE)
                    if matches:
                        rule_patterns.extend(matches)
                        rule_score += len(matches) * rule.weight
                
                # Check keywords
                for keyword in rule.keywords:
                    if keyword.lower() in text_content.lower():
                        rule_score += 0.5 * rule.weight
                
                if rule_score > 0:
                    detected_patterns[rule.name] = rule_patterns
                    data_types.add(rule.data_type)
                    total_score += rule_score
                    
                    # Update maximum sensitivity level
                    if self._is_higher_sensitivity(rule.sensitivity_level, max_sensitivity):
                        max_sensitivity = rule.sensitivity_level
            
            # Calculate confidence score
            confidence_score = min(total_score / 10.0, 1.0)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                max_sensitivity, list(data_types), confidence_score
            )
            
            result = ClassificationResult(
                sensitivity_level=max_sensitivity,
                data_types=list(data_types),
                confidence_score=confidence_score,
                detected_patterns=detected_patterns,
                recommendations=recommendations,
                classification_timestamp=datetime.utcnow()
            )
            
            logger.info(f"Document classified as {max_sensitivity.value} with confidence {confidence_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error classifying document: {e}")
            raise
    
    def _extract_text_content(self, document: Dict[str, Any]) -> str:
        """Extract text content from document for analysis"""
        text_parts = []
        
        def extract_recursive(obj):
            if isinstance(obj, str):
                text_parts.append(obj)
            elif isinstance(obj, dict):
                for value in obj.values():
                    extract_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_recursive(item)
        
        extract_recursive(document)
        return ' '.join(text_parts)
    
    def _is_higher_sensitivity(self, level1: SensitivityLevel, level2: SensitivityLevel) -> bool:
        """Check if level1 is higher sensitivity than level2"""
        sensitivity_order = {
            SensitivityLevel.PUBLIC: 0,
            SensitivityLevel.INTERNAL: 1,
            SensitivityLevel.CONFIDENTIAL: 2,
            SensitivityLevel.RESTRICTED: 3
        }
        return sensitivity_order[level1] > sensitivity_order[level2]
    
    def _generate_recommendations(self, sensitivity_level: SensitivityLevel, 
                                data_types: List[DataType], 
                                confidence_score: float) -> List[str]:
        """Generate recommendations based on classification results"""
        recommendations = []
        
        if sensitivity_level == SensitivityLevel.RESTRICTED:
            recommendations.extend([
                "Apply strict access controls and encryption",
                "Implement data masking for non-production environments",
                "Require approval for data access and sharing",
                "Enable comprehensive audit logging",
                "Consider data anonymization for analytics"
            ])
        elif sensitivity_level == SensitivityLevel.CONFIDENTIAL:
            recommendations.extend([
                "Apply role-based access controls",
                "Enable audit logging for data access",
                "Use encryption for data at rest and in transit",
                "Implement data retention policies"
            ])
        elif sensitivity_level == SensitivityLevel.INTERNAL:
            recommendations.extend([
                "Restrict access to authorized personnel",
                "Enable basic audit logging",
                "Apply standard data retention policies"
            ])
        
        if DataType.PERSONAL_IDENTIFIABLE in data_types:
            recommendations.append("Comply with data privacy regulations (GDPR, CCPA)")
            recommendations.append("Implement data subject rights (access, deletion)")
        
        if DataType.FINANCIAL in data_types:
            recommendations.append("Comply with financial data protection standards")
            recommendations.append("Implement additional fraud detection measures")
        
        if DataType.LOCATION in data_types:
            recommendations.append("Consider location privacy implications")
            recommendations.append("Implement location data anonymization")
        
        if confidence_score < 0.7:
            recommendations.append("Manual review recommended due to low confidence score")
        
        return recommendations
    
    async def classify_batch(self, documents: List[Dict[str, Any]]) -> List[ClassificationResult]:
        """
        Classify a batch of documents
        
        Args:
            documents: List of documents to classify
            
        Returns:
            List of classification results
        """
        results = []
        
        for doc in documents:
            try:
                result = await self.classify_document(doc)
                results.append(result)
            except Exception as e:
                logger.error(f"Error classifying document {doc.get('_id', 'unknown')}: {e}")
                # Create default result for failed classification
                results.append(ClassificationResult(
                    sensitivity_level=SensitivityLevel.INTERNAL,
                    data_types=[],
                    confidence_score=0.0,
                    detected_patterns={},
                    recommendations=["Manual classification required due to processing error"],
                    classification_timestamp=datetime.utcnow()
                ))
        
        logger.info(f"Batch classification completed: {len(results)} documents processed")
        return results
    
    def get_classification_statistics(self, results: List[ClassificationResult]) -> Dict[str, Any]:
        """Generate statistics from classification results"""
        if not results:
            return {}
        
        sensitivity_counts = {}
        data_type_counts = {}
        
        for result in results:
            # Count sensitivity levels
            level = result.sensitivity_level.value
            sensitivity_counts[level] = sensitivity_counts.get(level, 0) + 1
            
            # Count data types
            for data_type in result.data_types:
                type_name = data_type.value
                data_type_counts[type_name] = data_type_counts.get(type_name, 0) + 1
        
        avg_confidence = sum(r.confidence_score for r in results) / len(results)
        
        return {
            'total_documents': len(results),
            'sensitivity_distribution': sensitivity_counts,
            'data_type_distribution': data_type_counts,
            'average_confidence': avg_confidence,
            'high_confidence_count': len([r for r in results if r.confidence_score >= 0.8]),
            'low_confidence_count': len([r for r in results if r.confidence_score < 0.5])
        }
    
    def export_classification_rules(self) -> List[Dict[str, Any]]:
        """Export classification rules for backup or sharing"""
        return [
            {
                'name': rule.name,
                'data_type': rule.data_type.value,
                'sensitivity_level': rule.sensitivity_level.value,
                'patterns': rule.patterns,
                'keywords': rule.keywords,
                'weight': rule.weight,
                'enabled': rule.enabled
            }
            for rule in self.rules
        ]
    
    def import_classification_rules(self, rules_data: List[Dict[str, Any]]):
        """Import classification rules from exported data"""
        for rule_data in rules_data:
            rule = ClassificationRule(
                name=rule_data['name'],
                data_type=DataType(rule_data['data_type']),
                sensitivity_level=SensitivityLevel(rule_data['sensitivity_level']),
                patterns=rule_data['patterns'],
                keywords=rule_data['keywords'],
                weight=rule_data.get('weight', 1.0),
                enabled=rule_data.get('enabled', True)
            )
            self.add_rule(rule)