#!/usr/bin/env python3
"""
Simple test for multi-language NLP configuration without heavy dependencies
"""

import sys
import os

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

def test_config():
    """Test NLP configuration"""
    try:
        from nlp.config import NLPConfig, DEFAULT_NLP_CONFIG, LANGUAGE_METADATA
        
        print("✓ NLP Config loaded successfully")
        print(f"✓ Supported languages: {len(DEFAULT_NLP_CONFIG.supported_languages)}")
        print(f"✓ Languages: {DEFAULT_NLP_CONFIG.supported_languages}")
        
        # Test language metadata
        print(f"✓ Language metadata available for {len(LANGUAGE_METADATA)} languages")
        
        # Test custom config
        custom_config = NLPConfig(
            use_gpu=False,
            cache_models=True,
            translation_cache_size=500
        )
        print(f"✓ Custom config created: cache_size={custom_config.translation_cache_size}")
        
        return True
        
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        return False

def test_basic_imports():
    """Test basic imports without heavy dependencies"""
    try:
        # Test if we can import the modules (but not instantiate them)
        import nlp.language_detector
        import nlp.translator
        import nlp.sentiment_models
        import nlp.quality_scorer
        import nlp.nlp_service
        
        print("✓ All NLP modules can be imported")
        return True
        
    except Exception as e:
        print(f"✗ Import test failed: {e}")
        return False

def main():
    """Run simple tests"""
    print("Multi-Language NLP Simple Test")
    print("=" * 40)
    
    success = True
    
    # Test configuration
    if not test_config():
        success = False
    
    # Test imports
    if not test_basic_imports():
        success = False
    
    if success:
        print("\n✓ All basic tests passed!")
        print("\nMulti-language NLP support structure is ready.")
        print("Note: Full functionality requires additional dependencies:")
        print("  - fasttext (for advanced language detection)")
        print("  - transformers (for sentiment models)")
        print("  - googletrans (for translation)")
        print("  - langdetect (for language detection)")
        print("  - nltk (for quality scoring)")
        return 0
    else:
        print("\n✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)