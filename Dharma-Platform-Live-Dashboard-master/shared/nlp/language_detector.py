"""
Language detection for Indian languages with confidence scoring
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Optional imports with fallbacks
try:
    import langdetect
    from langdetect.lang_detect_exception import LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    LangDetectException = Exception

try:
    import fasttext
    FASTTEXT_AVAILABLE = True
except ImportError:
    FASTTEXT_AVAILABLE = False

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class LanguageDetectionResult:
    """Result of language detection"""
    language: str
    confidence: float
    script: Optional[str] = None
    alternatives: List[Tuple[str, float]] = None

class LanguageDetector:
    """
    Advanced language detection for Indian languages
    Supports Hindi, Bengali, Tamil, Urdu, Telugu, Marathi, Gujarati, Kannada, Malayalam, Punjabi
    """
    
    # Supported Indian languages with ISO codes
    INDIAN_LANGUAGES = {
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
        'or': 'Odia',
        'as': 'Assamese'
    }
    
    # Script detection patterns
    SCRIPT_PATTERNS = {
        'devanagari': r'[\u0900-\u097F]',
        'bengali': r'[\u0980-\u09FF]',
        'tamil': r'[\u0B80-\u0BFF]',
        'telugu': r'[\u0C00-\u0C7F]',
        'kannada': r'[\u0C80-\u0CFF]',
        'malayalam': r'[\u0D00-\u0D7F]',
        'gujarati': r'[\u0A80-\u0AFF]',
        'gurmukhi': r'[\u0A00-\u0A7F]',
        'odia': r'[\u0B00-\u0B7F]',
        'arabic': r'[\u0600-\u06FF]'  # For Urdu
    }
    
    def __init__(self, model_path: Optional[str] = None):
        """Initialize language detector with optional custom model"""
        self.model_path = model_path
        self.fasttext_model = None
        self.transformer_detector = None
        self._load_models()
    
    def _load_models(self):
        """Load language detection models"""
        try:
            # Load FastText model for better Indian language support
            if self.model_path and FASTTEXT_AVAILABLE:
                self.fasttext_model = fasttext.load_model(self.model_path)
            
            # Load transformer-based detector as fallback
            if TRANSFORMERS_AVAILABLE:
                self.transformer_detector = pipeline(
                    "text-classification",
                    model="papluca/xlm-roberta-base-language-detection",
                    return_all_scores=True
                )
            
        except Exception as e:
            logger.warning(f"Could not load advanced models: {e}")
            logger.info("Falling back to basic detection methods")
    
    def detect_language(self, text: str, min_confidence: float = 0.7) -> LanguageDetectionResult:
        """
        Detect language with confidence scoring
        
        Args:
            text: Input text to analyze
            min_confidence: Minimum confidence threshold
            
        Returns:
            LanguageDetectionResult with detected language and confidence
        """
        if not text or len(text.strip()) < 3:
            return LanguageDetectionResult(
                language='unknown',
                confidence=0.0,
                alternatives=[]
            )
        
        # Try multiple detection methods
        results = []
        
        # Method 1: FastText (if available)
        if self.fasttext_model:
            try:
                predictions = self.fasttext_model.predict(text.replace('\n', ' '), k=5)
                for lang, conf in zip(predictions[0], predictions[1]):
                    lang_code = lang.replace('__label__', '')
                    if lang_code in self.INDIAN_LANGUAGES:
                        results.append((lang_code, float(conf)))
            except Exception as e:
                logger.debug(f"FastText detection failed: {e}")
        
        # Method 2: Transformer-based detection
        if self.transformer_detector:
            try:
                predictions = self.transformer_detector(text)
                for pred in predictions:
                    lang_code = pred['label'].lower()
                    if lang_code in self.INDIAN_LANGUAGES:
                        results.append((lang_code, pred['score']))
            except Exception as e:
                logger.debug(f"Transformer detection failed: {e}")
        
        # Method 3: Langdetect (fallback)
        if LANGDETECT_AVAILABLE:
            try:
                lang_probs = langdetect.detect_langs(text)
                for lang_prob in lang_probs:
                    if lang_prob.lang in self.INDIAN_LANGUAGES:
                        results.append((lang_prob.lang, lang_prob.prob))
            except LangDetectException as e:
                logger.debug(f"Langdetect failed: {e}")
        else:
            # Basic fallback - detect by script only
            logger.debug("Langdetect not available, using script-based detection only")
        
        # Method 4: Script-based detection
        script_result = self._detect_by_script(text)
        if script_result:
            results.append(script_result)
        
        # Combine results and find best match
        if not results:
            return LanguageDetectionResult(
                language='en',  # Default to English
                confidence=0.5,
                alternatives=[]
            )
        
        # Aggregate scores by language
        lang_scores = {}
        for lang, score in results:
            if lang in lang_scores:
                lang_scores[lang] = max(lang_scores[lang], score)
            else:
                lang_scores[lang] = score
        
        # Sort by confidence
        sorted_results = sorted(lang_scores.items(), key=lambda x: x[1], reverse=True)
        
        best_lang, best_conf = sorted_results[0]
        alternatives = sorted_results[1:6]  # Top 5 alternatives
        
        # Detect script
        detected_script = self._get_script_for_language(best_lang, text)
        
        return LanguageDetectionResult(
            language=best_lang,
            confidence=best_conf,
            script=detected_script,
            alternatives=alternatives
        )
    
    def _detect_by_script(self, text: str) -> Optional[Tuple[str, float]]:
        """Detect language based on script patterns"""
        import re
        
        script_matches = {}
        total_chars = len([c for c in text if c.isalpha()])
        
        if total_chars == 0:
            return None
        
        for script, pattern in self.SCRIPT_PATTERNS.items():
            matches = len(re.findall(pattern, text))
            if matches > 0:
                script_matches[script] = matches / total_chars
        
        if not script_matches:
            return None
        
        # Map script to language
        script_to_lang = {
            'devanagari': 'hi',  # Could also be Marathi, but Hindi is more common
            'bengali': 'bn',
            'tamil': 'ta',
            'telugu': 'te',
            'kannada': 'kn',
            'malayalam': 'ml',
            'gujarati': 'gu',
            'gurmukhi': 'pa',
            'odia': 'or',
            'arabic': 'ur'
        }
        
        best_script = max(script_matches.items(), key=lambda x: x[1])
        if best_script[1] > 0.3:  # At least 30% of characters match
            lang = script_to_lang.get(best_script[0])
            if lang:
                return (lang, min(best_script[1] * 2, 0.9))  # Boost confidence but cap at 0.9
        
        return None
    
    def _get_script_for_language(self, language: str, text: str) -> Optional[str]:
        """Determine script used for detected language"""
        import re
        
        lang_to_scripts = {
            'hi': ['devanagari'],
            'bn': ['bengali'],
            'ta': ['tamil'],
            'te': ['telugu'],
            'kn': ['kannada'],
            'ml': ['malayalam'],
            'gu': ['gujarati'],
            'pa': ['gurmukhi'],
            'or': ['odia'],
            'ur': ['arabic'],
            'mr': ['devanagari']
        }
        
        possible_scripts = lang_to_scripts.get(language, [])
        
        for script in possible_scripts:
            if script in self.SCRIPT_PATTERNS:
                pattern = self.SCRIPT_PATTERNS[script]
                if re.search(pattern, text):
                    return script
        
        return None
    
    def is_indian_language(self, language_code: str) -> bool:
        """Check if language code is an Indian language"""
        return language_code in self.INDIAN_LANGUAGES
    
    def get_language_name(self, language_code: str) -> str:
        """Get full language name from code"""
        return self.INDIAN_LANGUAGES.get(language_code, language_code)
    
    def batch_detect(self, texts: List[str]) -> List[LanguageDetectionResult]:
        """Detect languages for multiple texts"""
        results = []
        for text in texts:
            results.append(self.detect_language(text))
        return results