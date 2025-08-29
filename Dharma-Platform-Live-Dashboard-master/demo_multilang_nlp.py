#!/usr/bin/env python3
"""
Demo script for multi-language NLP support
Tests language detection, translation, and sentiment analysis for Indian languages
"""

import asyncio
import logging
import sys
import os

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from nlp.nlp_service import MultiLanguageNLPService
from nlp.config import NLPConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def demo_language_detection():
    """Demo language detection capabilities"""
    print("\n" + "="*60)
    print("LANGUAGE DETECTION DEMO")
    print("="*60)
    
    service = MultiLanguageNLPService(NLPConfig(use_gpu=False, cache_models=False))
    
    test_texts = [
        ("This is an English sentence.", "en"),
        ("यह एक हिंदी वाक्य है।", "hi"),
        ("এটি একটি বাংলা বাক্য।", "bn"),
        ("இது ஒரு தமிழ் வாக்கியம்.", "ta"),
        ("یہ اردو کا جملہ ہے۔", "ur"),
        ("ఇది తెలుగు వాక్యం.", "te"),
        ("हे एक मराठी वाक्य आहे.", "mr"),
        ("આ એક ગુજરાતી વાક્ય છે.", "gu"),
        ("ಇದು ಒಂದು ಕನ್ನಡ ವಾಕ್ಯ.", "kn"),
        ("ഇത് ഒരു മലയാളം വാക്യമാണ്.", "ml"),
        ("ਇਹ ਇੱਕ ਪੰਜਾਬੀ ਵਾਕ ਹੈ।", "pa")
    ]
    
    for text, expected_lang in test_texts:
        result = service.language_detector.detect_language(text)
        status = "✓" if result.language == expected_lang else "✗"
        print(f"{status} Text: {text}")
        print(f"   Detected: {result.language} ({service.language_detector.get_language_name(result.language)})")
        print(f"   Confidence: {result.confidence:.3f}")
        print(f"   Script: {result.script}")
        print()

async def demo_translation():
    """Demo translation capabilities"""
    print("\n" + "="*60)
    print("TRANSLATION DEMO")
    print("="*60)
    
    service = MultiLanguageNLPService(NLPConfig(use_gpu=False, cache_models=False))
    
    test_texts = [
        ("भारत एक महान देश है।", "hi", "India is a great country."),
        ("আমি ভারতকে ভালোবাসি।", "bn", "I love India."),
        ("இந்தியா ஒரு அழகான நாடு.", "ta", "India is a beautiful country."),
        ("پاکستان اور ہندوستان دوست ہونے چاہیے۔", "ur", "Pakistan and India should be friends.")
    ]
    
    for text, source_lang, expected_meaning in test_texts:
        try:
            result = await service.translator.translate(text, source_lang, 'en')
            print(f"Original ({source_lang}): {text}")
            print(f"Translated: {result.translated_text}")
            print(f"Expected: {expected_meaning}")
            print(f"Confidence: {result.confidence:.3f}")
            print(f"Quality Score: {result.quality_score:.3f}")
            print(f"Method: {result.method}")
            print(f"Processing Time: {result.processing_time:.3f}s")
            print()
        except Exception as e:
            print(f"Translation failed for {text}: {e}")
            print()

async def demo_sentiment_analysis():
    """Demo sentiment analysis capabilities"""
    print("\n" + "="*60)
    print("SENTIMENT ANALYSIS DEMO")
    print("="*60)
    
    service = MultiLanguageNLPService(NLPConfig(use_gpu=False, cache_models=False))
    
    test_texts = [
        ("I love India! It's a wonderful country.", "en"),
        ("भारत माता की जय! हमारा देश महान है।", "hi"),
        ("ভারত একটি সুন্দর দেশ এবং আমি গর্বিত।", "bn"),
        ("India is facing some challenges but will overcome them.", "en"),
        ("भारत में कुछ समस्याएं हैं लेकिन हम उन्हें हल करेंगे।", "hi"),
        ("This country has many problems and corruption.", "en"),
        ("Pakistan is better than India in cricket.", "en"),
        ("भारत और पाकिस्तान दोनों अच्छे देश हैं।", "hi")
    ]
    
    for text, lang in test_texts:
        try:
            result = await service.sentiment_analyzer.analyze_sentiment(text, lang)
            print(f"Text: {text}")
            print(f"Language: {result.language}")
            print(f"Sentiment: {result.sentiment}")
            print(f"Confidence: {result.confidence:.3f}")
            print(f"Scores: {result.scores}")
            if result.translation_used:
                print(f"Translation Quality: {result.translation_quality:.3f}")
            print()
        except Exception as e:
            print(f"Sentiment analysis failed for {text}: {e}")
            print()

async def demo_comprehensive_analysis():
    """Demo comprehensive NLP analysis"""
    print("\n" + "="*60)
    print("COMPREHENSIVE ANALYSIS DEMO")
    print("="*60)
    
    service = MultiLanguageNLPService(NLPConfig(use_gpu=False, cache_models=False))
    
    test_texts = [
        "भारत एक अद्भुत देश है और मुझे इस पर गर्व है।",
        "India is facing challenges but remains strong and united.",
        "এই দেশটি অনেক সমস্যার সম্মুখীন কিন্তু এটি শক্তিশালী।",
        "Pakistan and India should work together for peace."
    ]
    
    for text in test_texts:
        try:
            result = await service.analyze_text(
                text,
                target_language='en',
                include_translation=True,
                include_sentiment=True,
                include_quality_metrics=True
            )
            
            print(f"Original Text: {text}")
            print(f"Detected Language: {result.language_detection.language} "
                  f"(confidence: {result.language_detection.confidence:.3f})")
            
            if result.translation:
                print(f"Translation: {result.translation.translated_text}")
                print(f"Translation Quality: {result.translation.quality_score:.3f}")
            
            if result.sentiment:
                print(f"Sentiment: {result.sentiment.sentiment} "
                      f"(confidence: {result.sentiment.confidence:.3f})")
            
            if result.quality_metrics:
                print(f"Overall Quality Score: {result.quality_metrics.overall_score:.3f}")
            
            print(f"Processing Time: {result.processing_time:.3f}s")
            print(f"Success: {result.success}")
            print()
            
        except Exception as e:
            print(f"Comprehensive analysis failed for {text}: {e}")
            print()

async def demo_batch_processing():
    """Demo batch processing capabilities"""
    print("\n" + "="*60)
    print("BATCH PROCESSING DEMO")
    print("="*60)
    
    service = MultiLanguageNLPService(NLPConfig(use_gpu=False, cache_models=False))
    
    texts = [
        "I love my country India.",
        "भारत महान है।",
        "এই দেশ সুন্দর।",
        "India has great potential.",
        "हमारा देश प्रगति कर रहा है।"
    ]
    
    try:
        results = await service.batch_analyze(
            texts,
            target_language='en',
            include_translation=True,
            include_sentiment=True,
            max_concurrent=3
        )
        
        print(f"Processed {len(texts)} texts:")
        for i, (text, result) in enumerate(zip(texts, results)):
            print(f"\n{i+1}. {text}")
            print(f"   Language: {result.language_detection.language}")
            if result.sentiment:
                print(f"   Sentiment: {result.sentiment.sentiment}")
            if result.translation:
                print(f"   Translation: {result.translation.translated_text}")
            print(f"   Success: {result.success}")
            
    except Exception as e:
        print(f"Batch processing failed: {e}")

async def demo_service_stats():
    """Demo service statistics and health check"""
    print("\n" + "="*60)
    print("SERVICE STATISTICS DEMO")
    print("="*60)
    
    service = MultiLanguageNLPService(NLPConfig(use_gpu=False, cache_models=False))
    
    # Get service statistics
    stats = service.get_service_stats()
    print("Service Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nSupported Languages:")
    languages = service.get_supported_languages()
    for code, name in languages.items():
        print(f"  {code}: {name}")
    
    # Perform health check
    print("\nHealth Check:")
    health = await service.health_check()
    print(f"Overall Status: {health['overall']}")
    print("Component Status:")
    for component, status in health['components'].items():
        print(f"  {component}: {status['status']}")
        if 'error' in status:
            print(f"    Error: {status['error']}")

async def main():
    """Run all demos"""
    print("Multi-Language NLP Support Demo")
    print("Project Dharma - Advanced Features Implementation")
    
    try:
        await demo_language_detection()
        await demo_translation()
        await demo_sentiment_analysis()
        await demo_comprehensive_analysis()
        await demo_batch_processing()
        await demo_service_stats()
        
        print("\n" + "="*60)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("="*60)
        print("\nMulti-language NLP support is now available with:")
        print("✓ Language detection for 11+ Indian languages")
        print("✓ Translation with quality scoring")
        print("✓ India-specific sentiment analysis")
        print("✓ Batch processing capabilities")
        print("✓ Comprehensive health monitoring")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\nDemo failed with error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)