"""
Integrated NLP service combining all multi-language capabilities
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import asyncio

from .language_detector import LanguageDetector, LanguageDetectionResult
from .translator import IndianLanguageTranslator, TranslationResult
from .sentiment_models import MultiLanguageSentimentAnalyzer, SentimentResult
from .quality_scorer import TranslationQualityScorer, QualityMetrics
from .config import NLPConfig, DEFAULT_NLP_CONFIG

logger = logging.getLogger(__name__)

@dataclass
class NLPAnalysisResult:
    """Comprehensive NLP analysis result"""
    text: str
    language_detection: LanguageDetectionResult
    translation: Optional[TranslationResult] = None
    sentiment: Optional[SentimentResult] = None
    quality_metrics: Optional[QualityMetrics] = None
    processing_time: float = 0.0
    success: bool = True
    error_message: Optional[str] = None

class MultiLanguageNLPService:
    """
    Integrated multi-language NLP service for Indian languages
    Combines language detection, translation, sentiment analysis, and quality scoring
    """
    
    def __init__(self, config: Optional[NLPConfig] = None):
        """Initialize NLP service with configuration"""
        self.config = config or DEFAULT_NLP_CONFIG
        
        # Initialize components
        self.language_detector = LanguageDetector()
        self.translator = IndianLanguageTranslator(
            cache_size=self.config.translation_cache_size,
            use_gpu=self.config.use_gpu
        )
        self.sentiment_analyzer = MultiLanguageSentimentAnalyzer(
            use_gpu=self.config.use_gpu,
            cache_models=self.config.cache_models
        )
        self.quality_scorer = TranslationQualityScorer()
        
        logger.info("Multi-language NLP service initialized")
    
    async def analyze_text(
        self, 
        text: str,
        target_language: str = 'en',
        include_translation: bool = True,
        include_sentiment: bool = True,
        include_quality_metrics: bool = False
    ) -> NLPAnalysisResult:
        """
        Comprehensive text analysis with language detection, translation, and sentiment
        
        Args:
            text: Input text to analyze
            target_language: Target language for translation
            include_translation: Whether to include translation
            include_sentiment: Whether to include sentiment analysis
            include_quality_metrics: Whether to include translation quality metrics
            
        Returns:
            NLPAnalysisResult with comprehensive analysis
        """
        import time
        start_time = time.time()
        
        try:
            # Step 1: Language Detection
            language_detection = self.language_detector.detect_language(text)
            
            if language_detection.confidence < self.config.language_detection_confidence_threshold:
                logger.warning(f"Low confidence language detection: {language_detection.confidence}")
            
            # Step 2: Translation (if needed and requested)
            translation_result = None
            if (include_translation and 
                language_detection.language != target_language and
                language_detection.confidence > 0.3):
                
                translation_result = await self.translator.translate(
                    text, 
                    language_detection.language, 
                    target_language
                )
            
            # Step 3: Sentiment Analysis (if requested)
            sentiment_result = None
            if include_sentiment:
                sentiment_result = await self.sentiment_analyzer.analyze_sentiment(
                    text,
                    language_detection.language,
                    translate_if_needed=True
                )
            
            # Step 4: Quality Metrics (if translation occurred and requested)
            quality_metrics = None
            if (include_quality_metrics and 
                translation_result and 
                translation_result.translated_text != text):
                
                quality_metrics = self.quality_scorer.score_translation(
                    text,
                    translation_result.translated_text,
                    language_detection.language,
                    target_language
                )
            
            processing_time = time.time() - start_time
            
            return NLPAnalysisResult(
                text=text,
                language_detection=language_detection,
                translation=translation_result,
                sentiment=sentiment_result,
                quality_metrics=quality_metrics,
                processing_time=processing_time,
                success=True
            )
            
        except Exception as e:
            logger.error(f"NLP analysis failed: {e}")
            processing_time = time.time() - start_time
            
            return NLPAnalysisResult(
                text=text,
                language_detection=LanguageDetectionResult(
                    language='unknown',
                    confidence=0.0
                ),
                processing_time=processing_time,
                success=False,
                error_message=str(e)
            )
    
    async def batch_analyze(
        self,
        texts: List[str],
        target_language: str = 'en',
        include_translation: bool = True,
        include_sentiment: bool = True,
        max_concurrent: int = 10
    ) -> List[NLPAnalysisResult]:
        """
        Analyze multiple texts in batch with concurrency control
        
        Args:
            texts: List of texts to analyze
            target_language: Target language for translation
            include_translation: Whether to include translation
            include_sentiment: Whether to include sentiment analysis
            max_concurrent: Maximum concurrent analyses
            
        Returns:
            List of NLPAnalysisResult objects
        """
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_semaphore(text: str) -> NLPAnalysisResult:
            async with semaphore:
                return await self.analyze_text(
                    text, 
                    target_language, 
                    include_translation, 
                    include_sentiment
                )
        
        # Execute analyses concurrently
        tasks = [analyze_with_semaphore(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch analysis failed for text {i}: {result}")
                final_results.append(NLPAnalysisResult(
                    text=texts[i],
                    language_detection=LanguageDetectionResult(
                        language='unknown',
                        confidence=0.0
                    ),
                    success=False,
                    error_message=str(result)
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    async def detect_and_translate(
        self, 
        text: str, 
        target_language: str = 'en'
    ) -> Tuple[LanguageDetectionResult, Optional[TranslationResult]]:
        """
        Detect language and translate if needed
        
        Args:
            text: Input text
            target_language: Target language for translation
            
        Returns:
            Tuple of (language_detection, translation_result)
        """
        
        # Detect language
        language_detection = self.language_detector.detect_language(text)
        
        # Translate if needed
        translation_result = None
        if language_detection.language != target_language:
            translation_result = await self.translator.translate(
                text, 
                language_detection.language, 
                target_language
            )
        
        return language_detection, translation_result
    
    async def analyze_sentiment_multilang(
        self, 
        text: str, 
        language: Optional[str] = None
    ) -> SentimentResult:
        """
        Analyze sentiment with automatic language detection
        
        Args:
            text: Input text
            language: Language code (auto-detect if None)
            
        Returns:
            SentimentResult with sentiment analysis
        """
        
        return await self.sentiment_analyzer.analyze_sentiment(
            text, 
            language, 
            translate_if_needed=True
        )
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get all supported languages across all services"""
        
        detector_langs = self.language_detector.INDIAN_LANGUAGES
        translator_langs = self.translator.get_supported_languages()
        sentiment_langs = self.sentiment_analyzer.get_supported_languages()
        
        # Combine all supported languages
        all_languages = {}
        all_languages.update(detector_langs)
        all_languages.update(translator_langs)
        all_languages.update(sentiment_langs)
        
        return all_languages
    
    def get_service_stats(self) -> Dict:
        """Get statistics about the NLP service"""
        
        return {
            'supported_languages': len(self.get_supported_languages()),
            'translation_cache_size': len(self.translator.translation_cache),
            'sentiment_models_loaded': len(self.sentiment_analyzer.pipelines),
            'gpu_available': self.config.use_gpu,
            'configuration': {
                'language_detection_threshold': self.config.language_detection_confidence_threshold,
                'translation_quality_threshold': self.config.translation_quality_threshold,
                'sentiment_confidence_threshold': self.config.sentiment_confidence_threshold
            }
        }
    
    async def health_check(self) -> Dict:
        """Perform health check on all NLP components"""
        
        health_status = {
            'overall': 'healthy',
            'components': {},
            'timestamp': None
        }
        
        import datetime
        health_status['timestamp'] = datetime.datetime.utcnow().isoformat()
        
        # Test language detection
        try:
            test_result = self.language_detector.detect_language("This is a test")
            health_status['components']['language_detector'] = {
                'status': 'healthy',
                'test_result': test_result.language
            }
        except Exception as e:
            health_status['components']['language_detector'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall'] = 'degraded'
        
        # Test translation
        try:
            test_translation = await self.translator.translate("test", "en", "hi")
            health_status['components']['translator'] = {
                'status': 'healthy',
                'test_result': len(test_translation.translated_text) > 0
            }
        except Exception as e:
            health_status['components']['translator'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall'] = 'degraded'
        
        # Test sentiment analysis
        try:
            test_sentiment = await self.sentiment_analyzer.analyze_sentiment("This is good")
            health_status['components']['sentiment_analyzer'] = {
                'status': 'healthy',
                'test_result': test_sentiment.sentiment
            }
        except Exception as e:
            health_status['components']['sentiment_analyzer'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall'] = 'degraded'
        
        return health_status
    
    def clear_caches(self):
        """Clear all caches to free memory"""
        self.translator.clear_cache()
        self.sentiment_analyzer.clear_cache()
        logger.info("All NLP caches cleared")

# Global service instance
_nlp_service_instance = None

def get_nlp_service(config: Optional[NLPConfig] = None) -> MultiLanguageNLPService:
    """Get singleton NLP service instance"""
    global _nlp_service_instance
    
    if _nlp_service_instance is None:
        _nlp_service_instance = MultiLanguageNLPService(config)
    
    return _nlp_service_instance