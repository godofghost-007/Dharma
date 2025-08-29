"""Enhanced sentiment analysis module with multi-language support for Indian languages."""

import asyncio
import time
import sys
import os
from typing import List, Optional, Dict, Any, Tuple
import logging
import numpy as np
import torch
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification,
    pipeline
)

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../shared'))

from nlp.nlp_service import MultiLanguageNLPService, get_nlp_service
from nlp.config import NLPConfig
from models.post import SentimentType, PropagandaTechnique
from ..core.config import settings
from ..models.requests import SentimentAnalysisResponse


logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Enhanced India-specific sentiment analysis with multi-language support."""
    
    def __init__(self, model_path: Optional[str] = None):
        """Initialize the sentiment analyzer.
        
        Args:
            model_path: Path to the model directory. If None, uses default from settings.
        """
        self.model_path = model_path or settings.sentiment_model_name
        self.confidence_threshold = settings.confidence_threshold
        self.max_length = settings.max_content_length
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Multi-language NLP service
        nlp_config = NLPConfig(
            use_gpu=torch.cuda.is_available(),
            cache_models=True,
            sentiment_confidence_threshold=self.confidence_threshold
        )
        self.nlp_service = get_nlp_service(nlp_config)
        
        # Legacy components for backward compatibility
        self.tokenizer = None
        self.model = None
        self.translator = None
        self.propaganda_detector = None
        
        # Model metadata
        self.model_version = "2.0.0"  # Updated version with multi-language support
        self.supported_languages = [
            'hi', 'bn', 'ta', 'ur', 'te', 'mr', 'gu', 'kn', 'ml', 'pa', 'en'
        ]
        
        # Performance tracking
        self.total_predictions = 0
        self.total_processing_time = 0.0
        
        # Sentiment label mapping
        self.label_mapping = {
            'pro_india': SentimentType.PRO_INDIA,
            'neutral': SentimentType.NEUTRAL,
            'anti_india': SentimentType.ANTI_INDIA
        }
        
        # Propaganda technique patterns (simplified rule-based approach)
        self.propaganda_patterns = {
            PropagandaTechnique.LOADED_LANGUAGE: [
                r'\b(terrorist|extremist|radical|fanatic)\b',
                r'\b(corrupt|evil|dangerous|threat)\b',
                r'\b(destroy|attack|invade|eliminate)\b'
            ],
            PropagandaTechnique.NAME_CALLING: [
                r'\b(traitor|enemy|puppet|slave)\b',
                r'\b(fake|fraud|liar|criminal)\b'
            ],
            PropagandaTechnique.APPEAL_TO_FEAR: [
                r'\b(danger|threat|risk|crisis|disaster)\b',
                r'\b(afraid|scared|terrified|panic)\b'
            ],
            PropagandaTechnique.REPETITION: [],  # Detected algorithmically
            PropagandaTechnique.BANDWAGON: [
                r'\b(everyone|everybody|all|most people)\b',
                r'\b(join us|follow|support|together)\b'
            ]
        }
    
    async def initialize(self) -> None:
        """Initialize the model and dependencies."""
        try:
            logger.info(f"Initializing enhanced sentiment analyzer with multi-language support")
            
            # Initialize multi-language NLP service
            # The service handles model loading internally
            
            # Initialize propaganda detector
            await self._initialize_propaganda_detector()
            
            # Perform health check on NLP service
            health_status = await self.nlp_service.health_check()
            if health_status['overall'] != 'healthy':
                logger.warning(f"NLP service health check: {health_status['overall']}")
            
            logger.info("Enhanced sentiment analyzer initialized successfully")
            logger.info(f"Supported languages: {', '.join(self.supported_languages)}")
            
        except Exception as e:
            logger.error(f"Failed to initialize sentiment analyzer: {e}")
            raise
    
    # Model loading now handled by multi-language NLP service
    
    async def _initialize_propaganda_detector(self) -> None:
        """Initialize propaganda technique detection."""
        try:
            # Compile regex patterns for propaganda detection
            import re
            self.compiled_patterns = {}
            
            for technique, patterns in self.propaganda_patterns.items():
                self.compiled_patterns[technique] = [
                    re.compile(pattern, re.IGNORECASE) for pattern in patterns
                ]
            
            logger.info("Propaganda detector initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize propaganda detector: {e}")
            raise
    
    async def analyze_sentiment(
        self, 
        text: str, 
        language: Optional[str] = None,
        translate: bool = True
    ) -> SentimentAnalysisResponse:
        """Analyze sentiment of a single text using multi-language NLP service.
        
        Args:
            text: Text to analyze
            language: Language code (auto-detect if None)
            translate: Whether to translate non-English text
            
        Returns:
            SentimentAnalysisResponse with analysis results
        """
        start_time = time.time()
        
        try:
            # Use multi-language NLP service for comprehensive analysis
            nlp_result = await self.nlp_service.analyze_text(
                text,
                target_language='en',
                include_translation=translate,
                include_sentiment=True,
                include_quality_metrics=False
            )
            
            if not nlp_result.success:
                raise Exception(f"NLP analysis failed: {nlp_result.error_message}")
            
            # Extract results
            detected_language = nlp_result.language_detection.language
            sentiment_result = nlp_result.sentiment
            translation_result = nlp_result.translation
            
            # Map sentiment to our enum
            sentiment = self.label_mapping.get(
                sentiment_result.sentiment, 
                SentimentType.NEUTRAL
            )
            confidence = sentiment_result.confidence
            
            # Extract translation info
            translated_text = None
            translation_confidence = None
            
            if translation_result:
                translated_text = translation_result.translated_text
                translation_confidence = translation_result.quality_score
            
            # Calculate risk score using the analysis text
            analysis_text = translated_text if translated_text else text
            risk_score = await self._calculate_risk_score(analysis_text, sentiment, confidence)
            
            # Detect propaganda techniques
            propaganda_techniques = await self._detect_propaganda_techniques(analysis_text)
            
            processing_time = (time.time() - start_time) * 1000
            
            # Update performance tracking
            self.total_predictions += 1
            self.total_processing_time += processing_time
            
            return SentimentAnalysisResponse(
                sentiment=sentiment,
                confidence=confidence,
                risk_score=risk_score,
                propaganda_techniques=propaganda_techniques,
                language_detected=detected_language,
                translation_confidence=translation_confidence,
                translated_text=translated_text,
                model_version=self.model_version,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            raise
    
    async def batch_analyze_sentiment(
        self,
        texts: List[str],
        language: Optional[str] = None,
        translate: bool = True
    ) -> List[SentimentAnalysisResponse]:
        """Analyze sentiment for multiple texts in batch using multi-language NLP service.
        
        Args:
            texts: List of texts to analyze
            language: Language code (auto-detect if None)
            translate: Whether to translate non-English text
            
        Returns:
            List of SentimentAnalysisResponse objects
        """
        start_time = time.time()
        
        try:
            # Use NLP service batch analysis for efficiency
            nlp_results = await self.nlp_service.batch_analyze(
                texts,
                target_language='en',
                include_translation=translate,
                include_sentiment=True,
                max_concurrent=min(settings.batch_size, 10)
            )
            
            # Convert NLP results to SentimentAnalysisResponse
            results = []
            for i, nlp_result in enumerate(nlp_results):
                try:
                    if not nlp_result.success:
                        logger.warning(f"NLP analysis failed for text {i}: {nlp_result.error_message}")
                        # Create fallback response
                        results.append(SentimentAnalysisResponse(
                            sentiment=SentimentType.NEUTRAL,
                            confidence=0.0,
                            risk_score=0.5,
                            propaganda_techniques=[],
                            language_detected='unknown',
                            translation_confidence=None,
                            translated_text=None,
                            model_version=self.model_version,
                            processing_time_ms=0.0
                        ))
                        continue
                    
                    # Extract results
                    detected_language = nlp_result.language_detection.language
                    sentiment_result = nlp_result.sentiment
                    translation_result = nlp_result.translation
                    
                    # Map sentiment to our enum
                    sentiment = self.label_mapping.get(
                        sentiment_result.sentiment, 
                        SentimentType.NEUTRAL
                    )
                    confidence = sentiment_result.confidence
                    
                    # Extract translation info
                    translated_text = None
                    translation_confidence = None
                    
                    if translation_result:
                        translated_text = translation_result.translated_text
                        translation_confidence = translation_result.quality_score
                    
                    # Calculate risk score and detect propaganda
                    analysis_text = translated_text if translated_text else texts[i]
                    risk_score = await self._calculate_risk_score(analysis_text, sentiment, confidence)
                    propaganda_techniques = await self._detect_propaganda_techniques(analysis_text)
                    
                    results.append(SentimentAnalysisResponse(
                        sentiment=sentiment,
                        confidence=confidence,
                        risk_score=risk_score,
                        propaganda_techniques=propaganda_techniques,
                        language_detected=detected_language,
                        translation_confidence=translation_confidence,
                        translated_text=translated_text,
                        model_version=self.model_version,
                        processing_time_ms=nlp_result.processing_time * 1000
                    ))
                    
                except Exception as e:
                    logger.error(f"Error processing result {i}: {e}")
                    # Add fallback response
                    results.append(SentimentAnalysisResponse(
                        sentiment=SentimentType.NEUTRAL,
                        confidence=0.0,
                        risk_score=0.5,
                        propaganda_techniques=[],
                        language_detected='unknown',
                        translation_confidence=None,
                        translated_text=None,
                        model_version=self.model_version,
                        processing_time_ms=0.0
                    ))
            
            total_time = (time.time() - start_time) * 1000
            logger.info(f"Batch analysis completed: {len(texts)} texts in {total_time:.2f}ms")
            
            # Update performance tracking
            self.total_predictions += len(texts)
            self.total_processing_time += total_time
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch sentiment analysis: {e}")
            raise
    
    # Legacy methods removed - now using multi-language NLP service
    
    async def _calculate_risk_score(
        self, 
        text: str, 
        sentiment: SentimentType, 
        confidence: float
    ) -> float:
        """Calculate risk score based on sentiment and content analysis.
        
        Args:
            text: Analyzed text
            sentiment: Predicted sentiment
            confidence: Prediction confidence
            
        Returns:
            Risk score between 0.0 and 1.0
        """
        try:
            risk_score = 0.0
            
            # Base risk from sentiment
            if sentiment == SentimentType.ANTI_INDIA:
                risk_score += 0.6
            elif sentiment == SentimentType.PRO_INDIA:
                risk_score += 0.1
            else:  # Neutral
                risk_score += 0.2
            
            # Adjust based on confidence
            risk_score *= confidence
            
            # Check for high-risk keywords
            high_risk_keywords = [
                'terrorist', 'attack', 'bomb', 'kill', 'destroy',
                'hate', 'enemy', 'war', 'violence', 'threat'
            ]
            
            text_lower = text.lower()
            risk_keyword_count = sum(1 for keyword in high_risk_keywords if keyword in text_lower)
            risk_score += min(0.3, risk_keyword_count * 0.1)
            
            # Ensure score is within bounds
            return min(1.0, max(0.0, risk_score))
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return 0.5  # Default medium risk
    
    async def _detect_propaganda_techniques(self, text: str) -> List[PropagandaTechnique]:
        """Detect propaganda techniques in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of detected propaganda techniques
        """
        try:
            detected_techniques = []
            
            # Check each propaganda technique pattern
            for technique, patterns in self.compiled_patterns.items():
                for pattern in patterns:
                    if pattern.search(text):
                        detected_techniques.append(technique)
                        break  # Only add each technique once
            
            # Check for repetition (algorithmic detection)
            if self._detect_repetition(text):
                detected_techniques.append(PropagandaTechnique.REPETITION)
            
            return detected_techniques
            
        except Exception as e:
            logger.error(f"Error detecting propaganda techniques: {e}")
            return []
    
    def _detect_repetition(self, text: str) -> bool:
        """Detect repetitive patterns in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            True if repetitive patterns are detected
        """
        try:
            words = text.lower().split()
            if len(words) < 4:
                return False
            
            # Check for repeated phrases (3+ words)
            for i in range(len(words) - 2):
                phrase = ' '.join(words[i:i+3])
                remaining_text = ' '.join(words[i+3:])
                if phrase in remaining_text:
                    return True
            
            # Check for repeated words (more than 20% repetition)
            word_counts = {}
            for word in words:
                if len(word) > 3:  # Only count meaningful words
                    word_counts[word] = word_counts.get(word, 0) + 1
            
            if word_counts:
                max_count = max(word_counts.values())
                repetition_ratio = max_count / len(words)
                return repetition_ratio > 0.2
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting repetition: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information and performance metrics.
        
        Returns:
            Dictionary with model information
        """
        avg_processing_time = (
            self.total_processing_time / self.total_predictions
            if self.total_predictions > 0 else 0.0
        )
        
        # Get NLP service stats
        nlp_stats = self.nlp_service.get_service_stats()
        
        return {
            "model_name": self.model_path,
            "model_version": self.model_version,
            "device": str(self.device),
            "supported_languages": self.supported_languages,
            "total_predictions": self.total_predictions,
            "average_processing_time_ms": avg_processing_time,
            "confidence_threshold": self.confidence_threshold,
            "max_content_length": self.max_length,
            "nlp_service_stats": nlp_stats,
            "multi_language_support": True
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the sentiment analyzer.
        
        Returns:
            Health check results
        """
        try:
            # Test with multi-language samples
            test_texts = [
                "This is a test sentence for health check.",
                "भारत एक महान देश है।",  # Hindi
                "এটি একটি পরীক্ষা।"  # Bengali
            ]
            
            # Test sentiment analysis
            results = []
            for text in test_texts:
                try:
                    result = await self.analyze_sentiment(text, translate=True)
                    results.append(result is not None)
                except Exception as e:
                    logger.warning(f"Test failed for text: {e}")
                    results.append(False)
            
            # Get NLP service health
            nlp_health = await self.nlp_service.health_check()
            
            overall_status = "healthy" if all(results) and nlp_health['overall'] == 'healthy' else "degraded"
            
            return {
                "status": overall_status,
                "multi_language_support": True,
                "test_results": {
                    "english_test": results[0] if len(results) > 0 else False,
                    "hindi_test": results[1] if len(results) > 1 else False,
                    "bengali_test": results[2] if len(results) > 2 else False
                },
                "nlp_service_health": nlp_health,
                "supported_languages": len(self.supported_languages),
                "device": str(self.device),
                "model_version": self.model_version
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "multi_language_support": False,
                "model_version": self.model_version
            }