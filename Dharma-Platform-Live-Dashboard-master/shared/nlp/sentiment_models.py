"""
Multi-language sentiment analysis models for Indian languages
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Optional imports with fallbacks
try:
    import torch
    from transformers import (
        AutoTokenizer, AutoModelForSequenceClassification,
        pipeline, Pipeline
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from .language_detector import LanguageDetector
from .translator import IndianLanguageTranslator, TranslationResult

logger = logging.getLogger(__name__)

@dataclass
class SentimentResult:
    """Result of sentiment analysis"""
    text: str
    language: str
    sentiment: str  # 'pro_india', 'neutral', 'anti_india'
    confidence: float
    scores: Dict[str, float]
    model_used: str
    translation_used: bool = False
    translation_quality: float = 0.0

class MultiLanguageSentimentAnalyzer:
    """
    Multi-language sentiment analyzer with India-specific models
    Supports direct analysis for major Indian languages and translation fallback
    """
    
    # Language-specific sentiment models
    LANGUAGE_MODELS = {
        'hi': 'ai4bharat/indic-bert-hi-sentiment',
        'bn': 'ai4bharat/indic-bert-bn-sentiment', 
        'ta': 'ai4bharat/indic-bert-ta-sentiment',
        'te': 'ai4bharat/indic-bert-te-sentiment',
        'mr': 'ai4bharat/indic-bert-mr-sentiment',
        'gu': 'ai4bharat/indic-bert-gu-sentiment',
        'en': 'cardiffnlp/twitter-roberta-base-sentiment-latest'
    }
    
    # Fallback multilingual models
    MULTILINGUAL_MODELS = {
        'xlm-roberta': 'cardiffnlp/twitter-xlm-roberta-base-sentiment',
        'indic-bert': 'ai4bharat/indic-bert'
    }
    
    # India-specific sentiment labels mapping
    SENTIMENT_MAPPING = {
        'positive': 'pro_india',
        'negative': 'anti_india', 
        'neutral': 'neutral',
        'POSITIVE': 'pro_india',
        'NEGATIVE': 'anti_india',
        'NEUTRAL': 'neutral'
    }
    
    def __init__(self, use_gpu: bool = False, cache_models: bool = True):
        """Initialize multi-language sentiment analyzer"""
        self.use_gpu = use_gpu and TRANSFORMERS_AVAILABLE and torch.cuda.is_available()
        self.device = 'cuda' if self.use_gpu else 'cpu'
        self.cache_models = cache_models
        
        # Model cache
        self.models = {}
        self.tokenizers = {}
        self.pipelines = {}
        
        # Language services
        self.language_detector = LanguageDetector()
        self.translator = IndianLanguageTranslator(use_gpu=use_gpu)
        
        # Load default English model
        self._load_model('en')
        
        # Preload common Indian language models
        if cache_models:
            self._preload_common_models()
    
    def _preload_common_models(self):
        """Preload commonly used models"""
        common_languages = ['hi', 'bn', 'ta']
        for lang in common_languages:
            try:
                self._load_model(lang)
            except Exception as e:
                logger.warning(f"Failed to preload model for {lang}: {e}")
    
    def _load_model(self, language: str) -> Pipeline:
        """Load sentiment model for specific language"""
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("Transformers library not available for sentiment analysis")
            
        if language in self.pipelines:
            return self.pipelines[language]
        
        try:
            model_name = self.LANGUAGE_MODELS.get(language)
            if not model_name:
                # Use multilingual fallback
                model_name = self.MULTILINGUAL_MODELS['xlm-roberta']
            
            logger.info(f"Loading sentiment model for {language}: {model_name}")
            
            # Create pipeline
            sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model=model_name,
                tokenizer=model_name,
                device=0 if self.use_gpu else -1,
                return_all_scores=True
            )
            
            self.pipelines[language] = sentiment_pipeline
            return sentiment_pipeline
            
        except Exception as e:
            logger.error(f"Failed to load model for {language}: {e}")
            # Fallback to English model
            if language != 'en':
                return self._load_model('en')
            raise
    
    async def analyze_sentiment(
        self, 
        text: str, 
        language: Optional[str] = None,
        translate_if_needed: bool = True
    ) -> SentimentResult:
        """
        Analyze sentiment with language detection and translation fallback
        
        Args:
            text: Text to analyze
            language: Language code (auto-detect if None)
            translate_if_needed: Whether to translate for better analysis
            
        Returns:
            SentimentResult with sentiment classification
        """
        
        # Detect language if not provided
        if not language:
            detection_result = self.language_detector.detect_language(text)
            language = detection_result.language
            
            if detection_result.confidence < 0.5:
                logger.warning(f"Low confidence language detection: {detection_result.confidence}")
        
        original_language = language
        analysis_text = text
        translation_used = False
        translation_quality = 0.0
        
        # Check if we have a direct model for this language
        model_available = language in self.LANGUAGE_MODELS
        
        # Decide whether to translate
        should_translate = (
            translate_if_needed and 
            not model_available and 
            language != 'en' and
            self.language_detector.is_indian_language(language)
        )
        
        if should_translate:
            try:
                translation_result = await self.translator.translate(
                    text, language, 'en'
                )
                
                if translation_result.quality_score > 0.6:
                    analysis_text = translation_result.translated_text
                    language = 'en'
                    translation_used = True
                    translation_quality = translation_result.quality_score
                    
            except Exception as e:
                logger.warning(f"Translation failed, using original text: {e}")
        
        # Load appropriate model
        try:
            model = self._load_model(language)
        except Exception as e:
            logger.error(f"Model loading failed, using English fallback: {e}")
            model = self._load_model('en')
            language = 'en'
        
        # Perform sentiment analysis
        try:
            results = model(analysis_text)
            
            # Process results
            if isinstance(results, list) and len(results) > 0:
                if isinstance(results[0], list):
                    # Multiple scores returned
                    scores = {item['label']: item['score'] for item in results[0]}
                else:
                    # Single result
                    scores = {results[0]['label']: results[0]['score']}
            else:
                scores = {'neutral': 1.0}
            
            # Map to India-specific sentiment
            mapped_scores = {}
            for label, score in scores.items():
                mapped_label = self.SENTIMENT_MAPPING.get(label, label.lower())
                mapped_scores[mapped_label] = score
            
            # Determine final sentiment
            final_sentiment = max(mapped_scores.items(), key=lambda x: x[1])
            
            # Apply India-specific adjustments
            adjusted_scores = self._apply_india_context_adjustments(
                analysis_text, mapped_scores, original_language
            )
            
            final_sentiment = max(adjusted_scores.items(), key=lambda x: x[1])
            
            return SentimentResult(
                text=text,
                language=original_language,
                sentiment=final_sentiment[0],
                confidence=final_sentiment[1],
                scores=adjusted_scores,
                model_used=f"{language}_model",
                translation_used=translation_used,
                translation_quality=translation_quality
            )
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return SentimentResult(
                text=text,
                language=original_language,
                sentiment='neutral',
                confidence=0.0,
                scores={'neutral': 1.0},
                model_used='fallback',
                translation_used=translation_used,
                translation_quality=translation_quality
            )
    
    def _apply_india_context_adjustments(
        self, 
        text: str, 
        scores: Dict[str, float], 
        language: str
    ) -> Dict[str, float]:
        """Apply India-specific context adjustments to sentiment scores"""
        
        adjusted_scores = scores.copy()
        
        # India-positive keywords (in various languages)
        pro_india_keywords = [
            'भारत माता', 'जय हिन्द', 'वन्दे मातरम्', 'india', 'bharat',
            'স্বাধীনতা', 'ভারত মাতা', 'தாய்நாடு', 'भारतीय', 'देश प्रेम',
            'राष्ट्रीय', 'स्वतंत्रता', 'गर्व', 'महान भारत'
        ]
        
        # Anti-India keywords
        anti_india_keywords = [
            'पाकिस्तान जिंदाबाद', 'भारत मुर्दाबाद', 'काश्मीर बनेगा पाकिस्तान',
            'anti-national', 'traitor', 'terrorist', 'separatist'
        ]
        
        text_lower = text.lower()
        
        # Check for pro-India sentiment
        pro_india_matches = sum(1 for keyword in pro_india_keywords if keyword.lower() in text_lower)
        if pro_india_matches > 0:
            boost = min(0.3, pro_india_matches * 0.1)
            adjusted_scores['pro_india'] = min(1.0, adjusted_scores.get('pro_india', 0) + boost)
            adjusted_scores['anti_india'] = max(0.0, adjusted_scores.get('anti_india', 0) - boost/2)
        
        # Check for anti-India sentiment
        anti_india_matches = sum(1 for keyword in anti_india_keywords if keyword.lower() in text_lower)
        if anti_india_matches > 0:
            boost = min(0.4, anti_india_matches * 0.15)
            adjusted_scores['anti_india'] = min(1.0, adjusted_scores.get('anti_india', 0) + boost)
            adjusted_scores['pro_india'] = max(0.0, adjusted_scores.get('pro_india', 0) - boost/2)
        
        # Normalize scores
        total = sum(adjusted_scores.values())
        if total > 0:
            adjusted_scores = {k: v/total for k, v in adjusted_scores.items()}
        
        return adjusted_scores
    
    async def batch_analyze(
        self, 
        texts: List[str], 
        languages: Optional[List[str]] = None
    ) -> List[SentimentResult]:
        """Analyze sentiment for multiple texts"""
        
        if languages is None:
            languages = [None] * len(texts)
        
        tasks = []
        for text, lang in zip(texts, languages):
            task = self.analyze_sentiment(text, lang)
            tasks.append(task)
        
        import asyncio
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Sentiment analysis failed for text {i}: {result}")
                final_results.append(SentimentResult(
                    text=texts[i],
                    language='unknown',
                    sentiment='neutral',
                    confidence=0.0,
                    scores={'neutral': 1.0},
                    model_used='failed'
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get supported languages for sentiment analysis"""
        return {
            'hi': 'Hindi',
            'bn': 'Bengali',
            'ta': 'Tamil',
            'te': 'Telugu',
            'mr': 'Marathi',
            'gu': 'Gujarati',
            'en': 'English'
        }
    
    def get_model_info(self, language: str) -> Dict:
        """Get information about loaded model for language"""
        if language in self.pipelines:
            pipeline = self.pipelines[language]
            return {
                'model_name': getattr(pipeline.model, 'name_or_path', 'unknown'),
                'language': language,
                'device': str(pipeline.device),
                'loaded': True
            }
        else:
            return {
                'language': language,
                'loaded': False,
                'available': language in self.LANGUAGE_MODELS
            }
    
    def clear_cache(self):
        """Clear model cache to free memory"""
        self.models.clear()
        self.tokenizers.clear()
        self.pipelines.clear()
        
        # Clear GPU cache if using CUDA
        if self.use_gpu and torch.cuda.is_available():
            torch.cuda.empty_cache()