"""
Tests for multi-language NLP support
"""

import pytest
import asyncio
from unittest.mock import Mock, patch

from shared.nlp.language_detector import LanguageDetector, LanguageDetectionResult
from shared.nlp.translator import IndianLanguageTranslator, TranslationResult
from shared.nlp.sentiment_models import MultiLanguageSentimentAnalyzer, SentimentResult
from shared.nlp.quality_scorer import TranslationQualityScorer, QualityMetrics
from shared.nlp.nlp_service import MultiLanguageNLPService, NLPAnalysisResult
from shared.nlp.config import NLPConfig

class TestLanguageDetector:
    """Test language detection functionality"""
    
    def setup_method(self):
        self.detector = LanguageDetector()
    
    def test_detect_hindi_text(self):
        """Test Hindi text detection"""
        hindi_text = "यह एक हिंदी वाक्य है।"
        result = self.detector.detect_language(hindi_text)
        
        assert result.language == 'hi'
        assert result.confidence > 0.5
        assert result.script == 'devanagari'
    
    def test_detect_bengali_text(self):
        """Test Bengali text detection"""
        bengali_text = "এটি একটি বাংলা বাক্য।"
        result = self.detector.detect_language(bengali_text)
        
        assert result.language == 'bn'
        assert result.confidence > 0.5
        assert result.script == 'bengali'
    
    def test_detect_english_text(self):
        """Test English text detection"""
        english_text = "This is an English sentence."
        result = self.detector.detect_language(english_text)
        
        assert result.language == 'en'
        assert result.confidence > 0.7
    
    def test_detect_mixed_script(self):
        """Test mixed script detection"""
        mixed_text = "This is English with हिंदी mixed in."
        result = self.detector.detect_language(mixed_text)
        
        # Should detect based on dominant script/language
        assert result.language in ['en', 'hi']
        assert result.confidence > 0.3
    
    def test_empty_text(self):
        """Test empty text handling"""
        result = self.detector.detect_language("")
        
        assert result.language == 'unknown'
        assert result.confidence == 0.0
    
    def test_batch_detection(self):
        """Test batch language detection"""
        texts = [
            "This is English",
            "यह हिंदी है",
            "এটি বাংলা",
            ""
        ]
        
        results = self.detector.batch_detect(texts)
        
        assert len(results) == 4
        assert results[0].language == 'en'
        assert results[1].language == 'hi'
        assert results[2].language == 'bn'
        assert results[3].language == 'unknown'
    
    def test_is_indian_language(self):
        """Test Indian language identification"""
        assert self.detector.is_indian_language('hi') == True
        assert self.detector.is_indian_language('bn') == True
        assert self.detector.is_indian_language('en') == False
        assert self.detector.is_indian_language('fr') == False

class TestIndianLanguageTranslator:
    """Test translation functionality"""
    
    def setup_method(self):
        self.translator = IndianLanguageTranslator(cache_size=100, use_gpu=False)
    
    @pytest.mark.asyncio
    async def test_no_translation_needed(self):
        """Test when source and target languages are the same"""
        text = "This is a test"
        result = await self.translator.translate(text, 'en', 'en')
        
        assert result.original_text == text
        assert result.translated_text == text
        assert result.confidence == 1.0
        assert result.method == 'no_translation'
    
    @pytest.mark.asyncio
    async def test_translation_caching(self):
        """Test translation caching"""
        text = "Hello world"
        
        # First translation
        result1 = await self.translator.translate(text, 'en', 'hi')
        
        # Second translation (should use cache)
        result2 = await self.translator.translate(text, 'en', 'hi')
        
        assert result1.translated_text == result2.translated_text
        assert result2.processing_time < result1.processing_time  # Cache should be faster
    
    @pytest.mark.asyncio
    async def test_batch_translation(self):
        """Test batch translation"""
        texts = ["Hello", "World", "Test"]
        
        results = await self.translator.batch_translate(texts, 'en', 'hi')
        
        assert len(results) == 3
        for result in results:
            assert isinstance(result, TranslationResult)
            assert result.source_language == 'en'
            assert result.target_language == 'hi'
    
    def test_get_supported_languages(self):
        """Test getting supported languages"""
        languages = self.translator.get_supported_languages()
        
        assert 'hi' in languages
        assert 'bn' in languages
        assert 'en' in languages
        assert languages['hi'] == 'Hindi'
    
    def test_cache_management(self):
        """Test cache management"""
        initial_stats = self.translator.get_cache_stats()
        
        self.translator.clear_cache()
        
        stats_after_clear = self.translator.get_cache_stats()
        assert stats_after_clear['cache_size'] == 0

class TestMultiLanguageSentimentAnalyzer:
    """Test sentiment analysis functionality"""
    
    def setup_method(self):
        self.analyzer = MultiLanguageSentimentAnalyzer(use_gpu=False, cache_models=False)
    
    @pytest.mark.asyncio
    async def test_english_sentiment_analysis(self):
        """Test English sentiment analysis"""
        positive_text = "I love India! It's a great country."
        result = await self.analyzer.analyze_sentiment(positive_text, 'en')
        
        assert result.language == 'en'
        assert result.sentiment in ['pro_india', 'positive', 'neutral']
        assert result.confidence > 0.0
        assert 'pro_india' in result.scores or 'positive' in result.scores
    
    @pytest.mark.asyncio
    async def test_hindi_sentiment_analysis(self):
        """Test Hindi sentiment analysis"""
        hindi_text = "भारत एक महान देश है।"
        result = await self.analyzer.analyze_sentiment(hindi_text, 'hi')
        
        assert result.language == 'hi'
        assert result.sentiment in ['pro_india', 'neutral', 'anti_india']
        assert result.confidence >= 0.0
    
    @pytest.mark.asyncio
    async def test_auto_language_detection(self):
        """Test automatic language detection in sentiment analysis"""
        text = "This is a neutral statement."
        result = await self.analyzer.analyze_sentiment(text)  # No language specified
        
        assert result.language is not None
        assert result.sentiment in ['pro_india', 'neutral', 'anti_india']
    
    @pytest.mark.asyncio
    async def test_batch_sentiment_analysis(self):
        """Test batch sentiment analysis"""
        texts = [
            "I love India",
            "This is neutral",
            "भारत महान है"
        ]
        
        results = await self.analyzer.batch_analyze(texts)
        
        assert len(results) == 3
        for result in results:
            assert isinstance(result, SentimentResult)
            assert result.sentiment in ['pro_india', 'neutral', 'anti_india']
    
    def test_india_context_adjustments(self):
        """Test India-specific context adjustments"""
        # Test with pro-India keywords
        pro_india_scores = {'pro_india': 0.3, 'neutral': 0.4, 'anti_india': 0.3}
        adjusted = self.analyzer._apply_india_context_adjustments(
            "भारत माता की जय", pro_india_scores, 'hi'
        )
        
        assert adjusted['pro_india'] > pro_india_scores['pro_india']
    
    def test_get_supported_languages(self):
        """Test getting supported languages"""
        languages = self.analyzer.get_supported_languages()
        
        assert 'hi' in languages
        assert 'en' in languages
        assert languages['hi'] == 'Hindi'

class TestTranslationQualityScorer:
    """Test translation quality scoring"""
    
    def setup_method(self):
        self.scorer = TranslationQualityScorer()
    
    def test_identical_text_quality(self):
        """Test quality scoring for identical texts"""
        text = "This is a test"
        metrics = self.scorer.score_translation(text, text, 'en', 'en')
        
        assert metrics.overall_score > 0.8
        assert metrics.confidence > 0.5
        assert len(metrics.issues) == 0
    
    def test_empty_translation_quality(self):
        """Test quality scoring for empty translation"""
        metrics = self.scorer.score_translation("Hello", "", 'en', 'hi')
        
        assert metrics.overall_score == 0.0
        assert 'Empty translation' in metrics.issues
    
    def test_length_ratio_scoring(self):
        """Test length ratio scoring"""
        original = "Hello"
        translated = "नमस्ते"  # Hindi greeting
        
        metrics = self.scorer.score_translation(original, translated, 'en', 'hi')
        
        assert metrics.length_ratio > 0
        assert metrics.fluency_score >= 0
        assert metrics.adequacy_score >= 0
    
    def test_batch_quality_scoring(self):
        """Test batch quality scoring"""
        translations = [
            ("Hello", "नमस्ते", 'en', 'hi'),
            ("World", "दुनिया", 'en', 'hi'),
            ("Test", "", 'en', 'hi')  # Empty translation
        ]
        
        results = self.scorer.batch_score(translations)
        
        assert len(results) == 3
        assert all(isinstance(r, QualityMetrics) for r in results)
        assert results[2].overall_score == 0.0  # Empty translation

class TestMultiLanguageNLPService:
    """Test integrated NLP service"""
    
    def setup_method(self):
        config = NLPConfig(use_gpu=False, cache_models=False)
        self.service = MultiLanguageNLPService(config)
    
    @pytest.mark.asyncio
    async def test_comprehensive_text_analysis(self):
        """Test comprehensive text analysis"""
        text = "I love India! It's a wonderful country."
        
        result = await self.service.analyze_text(
            text,
            target_language='hi',
            include_translation=True,
            include_sentiment=True,
            include_quality_metrics=True
        )
        
        assert result.success == True
        assert result.language_detection.language == 'en'
        assert result.sentiment is not None
        assert result.sentiment.sentiment in ['pro_india', 'neutral', 'anti_india']
        assert result.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_batch_analysis(self):
        """Test batch text analysis"""
        texts = [
            "This is English text",
            "यह हिंदी पाठ है",
            "I love my country"
        ]
        
        results = await self.service.batch_analyze(
            texts,
            target_language='en',
            include_translation=True,
            include_sentiment=True,
            max_concurrent=2
        )
        
        assert len(results) == 3
        assert all(isinstance(r, NLPAnalysisResult) for r in results)
        assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_detect_and_translate(self):
        """Test language detection and translation"""
        hindi_text = "नमस्ते दुनिया"
        
        detection, translation = await self.service.detect_and_translate(
            hindi_text, 'en'
        )
        
        assert detection.language == 'hi'
        assert translation is not None
        assert translation.source_language == 'hi'
        assert translation.target_language == 'en'
    
    @pytest.mark.asyncio
    async def test_multilang_sentiment_analysis(self):
        """Test multi-language sentiment analysis"""
        text = "भारत एक अद्भुत देश है"
        
        result = await self.service.analyze_sentiment_multilang(text)
        
        assert result.language == 'hi'
        assert result.sentiment in ['pro_india', 'neutral', 'anti_india']
    
    def test_get_supported_languages(self):
        """Test getting all supported languages"""
        languages = self.service.get_supported_languages()
        
        assert 'hi' in languages
        assert 'bn' in languages
        assert 'en' in languages
        assert len(languages) >= 10  # Should support multiple Indian languages
    
    def test_get_service_stats(self):
        """Test getting service statistics"""
        stats = self.service.get_service_stats()
        
        assert 'supported_languages' in stats
        assert 'translation_cache_size' in stats
        assert 'gpu_available' in stats
        assert 'configuration' in stats
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test service health check"""
        health = await self.service.health_check()
        
        assert 'overall' in health
        assert 'components' in health
        assert 'timestamp' in health
        assert health['overall'] in ['healthy', 'degraded', 'unhealthy']
    
    def test_clear_caches(self):
        """Test clearing all caches"""
        # This should not raise any exceptions
        self.service.clear_caches()

class TestNLPConfig:
    """Test NLP configuration"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = NLPConfig()
        
        assert config.use_gpu == False  # Default without GPU
        assert config.cache_models == True
        assert config.language_detection_confidence_threshold == 0.7
        assert config.fallback_language == "en"
        assert len(config.supported_languages) > 10
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = NLPConfig(
            use_gpu=True,
            cache_models=False,
            language_detection_confidence_threshold=0.8,
            translation_cache_size=500
        )
        
        assert config.cache_models == False
        assert config.language_detection_confidence_threshold == 0.8
        assert config.translation_cache_size == 500

# Integration tests
class TestNLPIntegration:
    """Integration tests for NLP components"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete end-to-end NLP workflow"""
        service = MultiLanguageNLPService(NLPConfig(use_gpu=False, cache_models=False))
        
        # Test with Hindi text
        hindi_text = "भारत एक महान देश है और मुझे इस पर गर्व है।"
        
        # Comprehensive analysis
        result = await service.analyze_text(
            hindi_text,
            target_language='en',
            include_translation=True,
            include_sentiment=True,
            include_quality_metrics=True
        )
        
        # Verify all components worked
        assert result.success == True
        assert result.language_detection.language == 'hi'
        assert result.translation is not None
        assert result.sentiment is not None
        assert result.sentiment.sentiment == 'pro_india'  # Should detect pro-India sentiment
        
        # Test with English text
        english_text = "India is facing challenges but remains strong."
        
        result2 = await service.analyze_text(
            english_text,
            include_sentiment=True
        )
        
        assert result2.success == True
        assert result2.language_detection.language == 'en'
        assert result2.sentiment is not None

if __name__ == "__main__":
    pytest.main([__file__])