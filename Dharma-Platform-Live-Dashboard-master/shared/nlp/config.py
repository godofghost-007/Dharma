"""
Configuration for multi-language NLP services
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class NLPConfig:
    """Configuration for NLP services"""
    
    # Model settings
    use_gpu: bool = False
    cache_models: bool = True
    model_cache_dir: str = "./models"
    
    # Language detection settings
    language_detection_confidence_threshold: float = 0.7
    fallback_language: str = "en"
    
    # Translation settings
    translation_cache_size: int = 1000
    translation_quality_threshold: float = 0.6
    max_translation_length: int = 5000
    
    # Sentiment analysis settings
    sentiment_confidence_threshold: float = 0.6
    batch_size: int = 32
    
    # Supported languages
    supported_languages: List[str] = None
    
    # API keys and credentials
    google_translate_api_key: Optional[str] = None
    
    def __post_init__(self):
        if self.supported_languages is None:
            self.supported_languages = [
                'hi', 'bn', 'ta', 'ur', 'te', 'mr', 'gu', 'kn', 'ml', 'pa', 'en'
            ]
        
        # Load from environment variables
        self.google_translate_api_key = os.getenv('GOOGLE_TRANSLATE_API_KEY')
        
        # GPU detection
        try:
            import torch
            self.use_gpu = self.use_gpu and torch.cuda.is_available()
        except ImportError:
            self.use_gpu = False

# Default configuration
DEFAULT_NLP_CONFIG = NLPConfig()

# Language metadata
LANGUAGE_METADATA = {
    'hi': {
        'name': 'Hindi',
        'native_name': 'हिन्दी',
        'script': 'Devanagari',
        'family': 'Indo-European',
        'speakers': 600000000,
        'regions': ['India', 'Nepal', 'Fiji']
    },
    'bn': {
        'name': 'Bengali',
        'native_name': 'বাংলা',
        'script': 'Bengali',
        'family': 'Indo-European',
        'speakers': 300000000,
        'regions': ['Bangladesh', 'India']
    },
    'ta': {
        'name': 'Tamil',
        'native_name': 'தமிழ்',
        'script': 'Tamil',
        'family': 'Dravidian',
        'speakers': 80000000,
        'regions': ['India', 'Sri Lanka', 'Singapore']
    },
    'ur': {
        'name': 'Urdu',
        'native_name': 'اردو',
        'script': 'Arabic',
        'family': 'Indo-European',
        'speakers': 70000000,
        'regions': ['Pakistan', 'India']
    },
    'te': {
        'name': 'Telugu',
        'native_name': 'తెలుగు',
        'script': 'Telugu',
        'family': 'Dravidian',
        'speakers': 95000000,
        'regions': ['India']
    },
    'mr': {
        'name': 'Marathi',
        'native_name': 'मराठी',
        'script': 'Devanagari',
        'family': 'Indo-European',
        'speakers': 83000000,
        'regions': ['India']
    },
    'gu': {
        'name': 'Gujarati',
        'native_name': 'ગુજરાતી',
        'script': 'Gujarati',
        'family': 'Indo-European',
        'speakers': 56000000,
        'regions': ['India']
    },
    'kn': {
        'name': 'Kannada',
        'native_name': 'ಕನ್ನಡ',
        'script': 'Kannada',
        'family': 'Dravidian',
        'speakers': 44000000,
        'regions': ['India']
    },
    'ml': {
        'name': 'Malayalam',
        'native_name': 'മലയാളം',
        'script': 'Malayalam',
        'family': 'Dravidian',
        'speakers': 38000000,
        'regions': ['India']
    },
    'pa': {
        'name': 'Punjabi',
        'native_name': 'ਪੰਜਾਬੀ',
        'script': 'Gurmukhi',
        'family': 'Indo-European',
        'speakers': 33000000,
        'regions': ['India', 'Pakistan']
    },
    'en': {
        'name': 'English',
        'native_name': 'English',
        'script': 'Latin',
        'family': 'Indo-European',
        'speakers': 1500000000,
        'regions': ['Global']
    }
}