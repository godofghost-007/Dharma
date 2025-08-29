"""
Translation quality scoring and confidence metrics
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re
import math
from collections import Counter

# Optional imports with fallbacks
try:
    import nltk
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
    from nltk.tokenize import word_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

try:
    import textstat
    TEXTSTAT_AVAILABLE = True
except ImportError:
    TEXTSTAT_AVAILABLE = False

logger = logging.getLogger(__name__)

# Download required NLTK data if available
if NLTK_AVAILABLE:
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        try:
            nltk.download('punkt')
        except Exception:
            logger.warning("Could not download NLTK punkt tokenizer")

@dataclass
class QualityMetrics:
    """Comprehensive quality metrics for translation"""
    overall_score: float
    fluency_score: float
    adequacy_score: float
    length_ratio: float
    bleu_score: float
    readability_score: float
    confidence: float
    issues: List[str]

class TranslationQualityScorer:
    """
    Advanced translation quality assessment using multiple metrics
    """
    
    def __init__(self):
        """Initialize quality scorer"""
        self.smoothing_function = SmoothingFunction().method1 if NLTK_AVAILABLE else None
        
        # Language-specific quality patterns
        self.quality_patterns = {
            'hi': {
                'sentence_endings': r'[।!?]$',
                'proper_script': r'[\u0900-\u097F]',
                'common_words': ['है', 'का', 'की', 'के', 'में', 'से', 'को', 'और', 'या']
            },
            'bn': {
                'sentence_endings': r'[।!?]$',
                'proper_script': r'[\u0980-\u09FF]',
                'common_words': ['এর', 'এবং', 'যে', 'তার', 'একটি', 'হয়', 'করে', 'থেকে']
            },
            'ta': {
                'sentence_endings': r'[।!?]$',
                'proper_script': r'[\u0B80-\u0BFF]',
                'common_words': ['அது', 'இது', 'என்று', 'ஒரு', 'அந்த', 'இந்த', 'மற்றும்']
            },
            'en': {
                'sentence_endings': r'[.!?]$',
                'proper_script': r'[a-zA-Z]',
                'common_words': ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for']
            }
        }
    
    def score_translation(
        self, 
        original_text: str, 
        translated_text: str,
        source_lang: str,
        target_lang: str,
        reference_translations: Optional[List[str]] = None
    ) -> QualityMetrics:
        """
        Comprehensive translation quality scoring
        
        Args:
            original_text: Source text
            translated_text: Translated text
            source_lang: Source language code
            target_lang: Target language code
            reference_translations: Optional reference translations for BLEU
            
        Returns:
            QualityMetrics with detailed quality assessment
        """
        
        issues = []
        
        # 1. Basic validation
        if not translated_text or not translated_text.strip():
            return QualityMetrics(
                overall_score=0.0,
                fluency_score=0.0,
                adequacy_score=0.0,
                length_ratio=0.0,
                bleu_score=0.0,
                readability_score=0.0,
                confidence=0.0,
                issues=['Empty translation']
            )
        
        # 2. Length ratio analysis
        length_ratio = len(translated_text) / max(len(original_text), 1)
        length_score = self._score_length_ratio(length_ratio, source_lang, target_lang)
        
        if length_ratio < 0.3 or length_ratio > 3.0:
            issues.append(f'Unusual length ratio: {length_ratio:.2f}')
        
        # 3. Fluency assessment
        fluency_score = self._assess_fluency(translated_text, target_lang)
        
        # 4. Adequacy assessment (content preservation)
        adequacy_score = self._assess_adequacy(original_text, translated_text, source_lang, target_lang)
        
        # 5. BLEU score calculation
        bleu_score = self._calculate_bleu_score(
            original_text, translated_text, reference_translations
        )
        
        # 6. Readability assessment
        readability_score = self._assess_readability(translated_text, target_lang)
        
        # 7. Language-specific quality checks
        lang_specific_score = self._check_language_specific_quality(translated_text, target_lang)
        
        # 8. Calculate overall score
        weights = {
            'length': 0.15,
            'fluency': 0.25,
            'adequacy': 0.25,
            'bleu': 0.15,
            'readability': 0.10,
            'language_specific': 0.10
        }
        
        overall_score = (
            weights['length'] * length_score +
            weights['fluency'] * fluency_score +
            weights['adequacy'] * adequacy_score +
            weights['bleu'] * bleu_score +
            weights['readability'] * readability_score +
            weights['language_specific'] * lang_specific_score
        )
        
        # 9. Calculate confidence based on consistency of metrics
        confidence = self._calculate_confidence([
            length_score, fluency_score, adequacy_score, 
            bleu_score, readability_score, lang_specific_score
        ])
        
        return QualityMetrics(
            overall_score=overall_score,
            fluency_score=fluency_score,
            adequacy_score=adequacy_score,
            length_ratio=length_ratio,
            bleu_score=bleu_score,
            readability_score=readability_score,
            confidence=confidence,
            issues=issues
        )
    
    def _score_length_ratio(self, ratio: float, source_lang: str, target_lang: str) -> float:
        """Score based on length ratio expectations"""
        
        # Expected length ratios for different language pairs
        expected_ratios = {
            ('hi', 'en'): (0.8, 1.2),
            ('bn', 'en'): (0.7, 1.1),
            ('ta', 'en'): (0.9, 1.3),
            ('ur', 'en'): (0.8, 1.2),
            ('en', 'hi'): (0.8, 1.3),
            ('en', 'bn'): (0.9, 1.4),
            ('en', 'ta'): (0.7, 1.1),
            ('en', 'ur'): (0.8, 1.2)
        }
        
        pair = (source_lang, target_lang)
        if pair in expected_ratios:
            min_ratio, max_ratio = expected_ratios[pair]
        else:
            min_ratio, max_ratio = (0.5, 2.0)  # Default range
        
        if min_ratio <= ratio <= max_ratio:
            return 1.0
        elif ratio < min_ratio:
            return max(0.0, 1.0 - (min_ratio - ratio) / min_ratio)
        else:
            return max(0.0, 1.0 - (ratio - max_ratio) / max_ratio)
    
    def _assess_fluency(self, text: str, language: str) -> float:
        """Assess fluency of translated text"""
        
        score = 0.5  # Base score
        
        # Check sentence structure
        sentences = re.split(r'[.!?।]', text)
        valid_sentences = [s.strip() for s in sentences if len(s.strip()) > 3]
        
        if len(valid_sentences) > 0:
            score += 0.2
        
        # Check for proper capitalization (for languages that use it)
        if language == 'en':
            if re.search(r'^[A-Z]', text.strip()):
                score += 0.1
        
        # Check for repeated words (sign of poor translation)
        words = text.lower().split()
        if len(words) > 0:
            word_counts = Counter(words)
            max_repetition = max(word_counts.values()) if word_counts else 1
            repetition_ratio = max_repetition / len(words)
            
            if repetition_ratio < 0.3:  # Less than 30% repetition is good
                score += 0.2
        
        # Check for proper script usage
        if language in self.quality_patterns:
            pattern = self.quality_patterns[language]['proper_script']
            if re.search(pattern, text):
                score += 0.1
        
        return min(score, 1.0)
    
    def _assess_adequacy(self, original: str, translated: str, source_lang: str, target_lang: str) -> float:
        """Assess content preservation (adequacy)"""
        
        # Simple word overlap for same-script languages
        if source_lang == target_lang:
            return 1.0 if original.strip() == translated.strip() else 0.8
        
        # For different languages, use heuristics
        score = 0.5
        
        # Check if translation is not just the original text
        if original.strip() != translated.strip():
            score += 0.3
        
        # Check for preservation of numbers and special entities
        original_numbers = re.findall(r'\d+', original)
        translated_numbers = re.findall(r'\d+', translated)
        
        if original_numbers == translated_numbers:
            score += 0.1
        
        # Check for preservation of proper nouns (capitalized words in English)
        if target_lang == 'en':
            original_proper = re.findall(r'\b[A-Z][a-z]+\b', original)
            translated_proper = re.findall(r'\b[A-Z][a-z]+\b', translated)
            
            overlap = len(set(original_proper) & set(translated_proper))
            if len(original_proper) > 0:
                proper_preservation = overlap / len(original_proper)
                score += 0.1 * proper_preservation
        
        return min(score, 1.0)
    
    def _calculate_bleu_score(
        self, 
        original: str, 
        translated: str, 
        references: Optional[List[str]] = None
    ) -> float:
        """Calculate BLEU score for translation quality"""
        
        if not NLTK_AVAILABLE:
            logger.debug("NLTK not available, skipping BLEU calculation")
            return 0.0
        
        try:
            # Tokenize texts
            translated_tokens = word_tokenize(translated.lower())
            
            if references:
                reference_tokens = [word_tokenize(ref.lower()) for ref in references]
            else:
                # Use original as reference (not ideal but better than nothing)
                reference_tokens = [word_tokenize(original.lower())]
            
            # Calculate BLEU score
            bleu = sentence_bleu(
                reference_tokens, 
                translated_tokens,
                smoothing_function=self.smoothing_function
            )
            
            return bleu
            
        except Exception as e:
            logger.debug(f"BLEU calculation failed: {e}")
            return 0.0
    
    def _assess_readability(self, text: str, language: str) -> float:
        """Assess readability of translated text"""
        
        if language != 'en' or not TEXTSTAT_AVAILABLE:
            # For non-English or when textstat unavailable, use simple heuristics
            return self._simple_readability_score(text)
        
        try:
            # Use textstat for English readability
            flesch_score = textstat.flesch_reading_ease(text)
            
            # Convert Flesch score to 0-1 range
            if flesch_score >= 90:
                return 1.0
            elif flesch_score >= 80:
                return 0.9
            elif flesch_score >= 70:
                return 0.8
            elif flesch_score >= 60:
                return 0.7
            elif flesch_score >= 50:
                return 0.6
            else:
                return 0.5
                
        except Exception as e:
            logger.debug(f"Readability assessment failed: {e}")
            return self._simple_readability_score(text)
    
    def _simple_readability_score(self, text: str) -> float:
        """Simple readability assessment for any language"""
        
        words = text.split()
        sentences = re.split(r'[.!?।]', text)
        
        if len(sentences) == 0 or len(words) == 0:
            return 0.0
        
        avg_words_per_sentence = len(words) / len(sentences)
        avg_chars_per_word = sum(len(word) for word in words) / len(words)
        
        # Ideal ranges
        ideal_words_per_sentence = 15
        ideal_chars_per_word = 5
        
        # Score based on how close to ideal
        sentence_score = 1.0 - min(1.0, abs(avg_words_per_sentence - ideal_words_per_sentence) / ideal_words_per_sentence)
        word_score = 1.0 - min(1.0, abs(avg_chars_per_word - ideal_chars_per_word) / ideal_chars_per_word)
        
        return (sentence_score + word_score) / 2
    
    def _check_language_specific_quality(self, text: str, language: str) -> float:
        """Check language-specific quality indicators"""
        
        if language not in self.quality_patterns:
            return 0.7  # Default score for unsupported languages
        
        patterns = self.quality_patterns[language]
        score = 0.0
        
        # Check proper sentence endings
        sentences = re.split(r'[.!?।]', text)
        valid_endings = sum(1 for s in sentences[:-1] if s.strip())  # Exclude last empty split
        if len(sentences) > 1 and valid_endings > 0:
            score += 0.3
        
        # Check for common words in the language
        words = text.lower().split()
        common_word_count = sum(1 for word in words if word in patterns['common_words'])
        if len(words) > 0:
            common_ratio = common_word_count / len(words)
            score += min(0.4, common_ratio * 2)  # Up to 0.4 points
        
        # Check proper script usage
        if re.search(patterns['proper_script'], text):
            score += 0.3
        
        return min(score, 1.0)
    
    def _calculate_confidence(self, scores: List[float]) -> float:
        """Calculate confidence based on consistency of metrics"""
        
        if not scores:
            return 0.0
        
        mean_score = sum(scores) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
        std_dev = math.sqrt(variance)
        
        # Lower standard deviation means higher confidence
        confidence = max(0.0, 1.0 - std_dev)
        
        # Boost confidence if all scores are reasonably high
        if mean_score > 0.7:
            confidence = min(1.0, confidence + 0.1)
        
        return confidence
    
    def batch_score(
        self, 
        translations: List[Tuple[str, str, str, str]]  # (original, translated, source_lang, target_lang)
    ) -> List[QualityMetrics]:
        """Score multiple translations in batch"""
        
        results = []
        for original, translated, source_lang, target_lang in translations:
            try:
                metrics = self.score_translation(original, translated, source_lang, target_lang)
                results.append(metrics)
            except Exception as e:
                logger.error(f"Quality scoring failed: {e}")
                results.append(QualityMetrics(
                    overall_score=0.0,
                    fluency_score=0.0,
                    adequacy_score=0.0,
                    length_ratio=0.0,
                    bleu_score=0.0,
                    readability_score=0.0,
                    confidence=0.0,
                    issues=[f'Scoring failed: {str(e)}']
                ))
        
        return results