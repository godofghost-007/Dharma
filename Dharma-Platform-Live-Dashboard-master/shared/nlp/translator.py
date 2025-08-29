"""
Translation service for Indian languages with quality scoring
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

# Optional imports with fallbacks
try:
    from googletrans import Translator as GoogleTranslator
    GOOGLETRANS_AVAILABLE = True
except (ImportError, AttributeError, Exception):
    GOOGLETRANS_AVAILABLE = False

try:
    from transformers import MarianMTModel, MarianTokenizer, pipeline
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class TranslationResult:
    """Result of translation with quality metrics"""
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    confidence: float
    quality_score: float
    method: str
    processing_time: float

class IndianLanguageTranslator:
    """
    Advanced translation service for Indian languages
    Supports multiple translation backends with quality scoring
    """
    
    # Language mappings for different services
    GOOGLE_LANG_MAP = {
        'hi': 'hi',
        'bn': 'bn', 
        'ta': 'ta',
        'ur': 'ur',
        'te': 'te',
        'mr': 'mr',
        'gu': 'gu',
        'kn': 'kn',
        'ml': 'ml',
        'pa': 'pa'
    }
    
    # Marian model mappings (Helsinki-NLP models)
    MARIAN_MODELS = {
        'hi-en': 'Helsinki-NLP/opus-mt-hi-en',
        'bn-en': 'Helsinki-NLP/opus-mt-bn-en',
        'ta-en': 'Helsinki-NLP/opus-mt-ta-en',
        'ur-en': 'Helsinki-NLP/opus-mt-ur-en',
        'en-hi': 'Helsinki-NLP/opus-mt-en-hi',
        'en-bn': 'Helsinki-NLP/opus-mt-en-bn',
        'en-ta': 'Helsinki-NLP/opus-mt-en-ta',
        'en-ur': 'Helsinki-NLP/opus-mt-en-ur'
    }
    
    def __init__(self, cache_size: int = 1000, use_gpu: bool = False):
        """Initialize translator with caching and GPU support"""
        self.cache_size = cache_size
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.device = 'cuda' if self.use_gpu else 'cpu'
        
        # Translation cache
        self.translation_cache = {}
        
        # Initialize services
        self.google_translator = GoogleTranslator() if GOOGLETRANS_AVAILABLE else None
        self.marian_models = {}
        self.marian_tokenizers = {}
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Load commonly used models
        self._preload_models(['hi-en', 'en-hi', 'bn-en', 'en-bn'])
    
    def _preload_models(self, model_pairs: List[str]):
        """Preload commonly used Marian models"""
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("Transformers not available, skipping Marian model preloading")
            return
            
        for pair in model_pairs:
            if pair in self.MARIAN_MODELS:
                try:
                    model_name = self.MARIAN_MODELS[pair]
                    logger.info(f"Loading Marian model: {model_name}")
                    
                    tokenizer = MarianTokenizer.from_pretrained(model_name)
                    model = MarianMTModel.from_pretrained(model_name)
                    
                    if self.use_gpu:
                        model = model.to(self.device)
                    
                    self.marian_tokenizers[pair] = tokenizer
                    self.marian_models[pair] = model
                    
                except Exception as e:
                    logger.warning(f"Failed to load Marian model {pair}: {e}")
    
    async def translate(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str = 'en',
        method: str = 'auto'
    ) -> TranslationResult:
        """
        Translate text with quality scoring
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            method: Translation method ('auto', 'google', 'marian')
            
        Returns:
            TranslationResult with translation and quality metrics
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = f"{text}:{source_lang}:{target_lang}"
        if cache_key in self.translation_cache:
            cached_result = self.translation_cache[cache_key]
            cached_result.processing_time = time.time() - start_time
            return cached_result
        
        # Skip translation if already in target language
        if source_lang == target_lang:
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language=source_lang,
                target_language=target_lang,
                confidence=1.0,
                quality_score=1.0,
                method='no_translation',
                processing_time=time.time() - start_time
            )
        
        # Choose translation method
        if method == 'auto':
            method = self._choose_best_method(source_lang, target_lang)
        
        # Perform translation
        try:
            if method == 'marian':
                result = await self._translate_with_marian(text, source_lang, target_lang)
            else:
                result = await self._translate_with_google(text, source_lang, target_lang)
            
            result.processing_time = time.time() - start_time
            
            # Cache result
            if len(self.translation_cache) < self.cache_size:
                self.translation_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            # Return original text as fallback
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language=source_lang,
                target_language=target_lang,
                confidence=0.0,
                quality_score=0.0,
                method='failed',
                processing_time=time.time() - start_time
            )
    
    def _choose_best_method(self, source_lang: str, target_lang: str) -> str:
        """Choose best translation method based on language pair"""
        pair = f"{source_lang}-{target_lang}"
        
        # Prefer Marian for supported pairs
        if pair in self.MARIAN_MODELS or pair in self.marian_models:
            return 'marian'
        
        # Use Google Translate for other pairs
        return 'google'
    
    async def _translate_with_marian(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str
    ) -> TranslationResult:
        """Translate using Marian MT models"""
        pair = f"{source_lang}-{target_lang}"
        
        if pair not in self.marian_models:
            # Try to load model on demand
            if pair in self.MARIAN_MODELS:
                model_name = self.MARIAN_MODELS[pair]
                tokenizer = MarianTokenizer.from_pretrained(model_name)
                model = MarianMTModel.from_pretrained(model_name)
                
                if self.use_gpu:
                    model = model.to(self.device)
                
                self.marian_tokenizers[pair] = tokenizer
                self.marian_models[pair] = model
            else:
                raise ValueError(f"Marian model not available for {pair}")
        
        tokenizer = self.marian_tokenizers[pair]
        model = self.marian_models[pair]
        
        # Tokenize and translate
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        
        if self.use_gpu:
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = model.generate(**inputs, max_length=512, num_beams=4)
        
        translated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Calculate confidence (simplified)
        confidence = 0.8  # Marian models generally have good quality
        quality_score = self._calculate_quality_score(text, translated_text, source_lang, target_lang)
        
        return TranslationResult(
            original_text=text,
            translated_text=translated_text,
            source_language=source_lang,
            target_language=target_lang,
            confidence=confidence,
            quality_score=quality_score,
            method='marian',
            processing_time=0.0  # Will be set by caller
        )
    
    async def _translate_with_google(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str
    ) -> TranslationResult:
        """Translate using Google Translate"""
        
        # Map language codes
        google_source = self.GOOGLE_LANG_MAP.get(source_lang, source_lang)
        google_target = self.GOOGLE_LANG_MAP.get(target_lang, target_lang)
        
        if not GOOGLETRANS_AVAILABLE or not self.google_translator:
            # Fallback: return original text
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language=source_lang,
                target_language=target_lang,
                confidence=0.1,
                quality_score=0.1,
                method='unavailable',
                processing_time=0.0
            )
        
        # Perform translation in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor,
            self._google_translate_sync,
            text, google_source, google_target
        )
        
        quality_score = self._calculate_quality_score(text, result.text, source_lang, target_lang)
        
        return TranslationResult(
            original_text=text,
            translated_text=result.text,
            source_language=source_lang,
            target_language=target_lang,
            confidence=getattr(result, 'confidence', 0.7),
            quality_score=quality_score,
            method='google',
            processing_time=0.0  # Will be set by caller
        )
    
    def _google_translate_sync(self, text: str, source_lang: str, target_lang: str):
        """Synchronous Google Translate call"""
        return self.google_translator.translate(
            text, 
            src=source_lang, 
            dest=target_lang
        )
    
    def _calculate_quality_score(
        self, 
        original: str, 
        translated: str, 
        source_lang: str, 
        target_lang: str
    ) -> float:
        """Calculate translation quality score"""
        
        # Basic quality indicators
        score = 0.5  # Base score
        
        # Length ratio check
        len_ratio = len(translated) / max(len(original), 1)
        if 0.5 <= len_ratio <= 2.0:
            score += 0.2
        
        # Check for untranslated text (same as original)
        if original.strip() != translated.strip():
            score += 0.2
        
        # Check for proper sentence structure
        if translated.strip().endswith(('.', '!', '?', '।')):  # Including Devanagari danda
            score += 0.1
        
        return min(score, 1.0)
    
    async def batch_translate(
        self, 
        texts: List[str], 
        source_lang: str, 
        target_lang: str = 'en'
    ) -> List[TranslationResult]:
        """Translate multiple texts in batch"""
        
        tasks = []
        for text in texts:
            task = self.translate(text, source_lang, target_lang)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Translation failed for text {i}: {result}")
                final_results.append(TranslationResult(
                    original_text=texts[i],
                    translated_text=texts[i],
                    source_language=source_lang,
                    target_language=target_lang,
                    confidence=0.0,
                    quality_score=0.0,
                    method='failed',
                    processing_time=0.0
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages"""
        return {
            'hi': 'Hindi',
            'bn': 'Bengali',
            'ta': 'Tamil',
            'ur': 'Urdu',
            'te': 'Telugu',
            'mr': 'Marathi',
            'gu': 'Gujarati',
            'kn': 'Kannada',
            'ml': 'Malayalam',
            'pa': 'Punjabi',
            'en': 'English'
        }
    
    def clear_cache(self):
        """Clear translation cache"""
        self.translation_cache.clear()
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'cache_size': len(self.translation_cache),
            'max_size': self.cache_size,
            'hit_rate': getattr(self, '_cache_hits', 0) / max(getattr(self, '_cache_requests', 1), 1)
        }