#!/usr/bin/env python3
"""Test script for sentiment analysis module."""

import asyncio
import time
import logging
from typing import List

from app.analysis.sentiment_analyzer import SentimentAnalyzer
from shared.models.post import SentimentType, PropagandaTechnique

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_sentiment_analyzer():
    """Test the sentiment analyzer functionality."""
    
    print("🚀 Testing Sentiment Analyzer Module")
    print("=" * 50)
    
    # Initialize analyzer
    analyzer = SentimentAnalyzer()
    await analyzer.initialize()
    
    # Test cases for India-specific sentiment analysis
    test_cases = [
        # Pro-India content
        {
            "text": "India is making great progress in technology and innovation. Proud to be Indian!",
            "expected_sentiment": SentimentType.PRO_INDIA,
            "description": "Positive India content"
        },
        {
            "text": "Modi government's digital initiatives are transforming India for the better.",
            "expected_sentiment": SentimentType.PRO_INDIA,
            "description": "Pro-government content"
        },
        
        # Anti-India content
        {
            "text": "India is a corrupt country with terrible policies that harm its people.",
            "expected_sentiment": SentimentType.ANTI_INDIA,
            "description": "Negative India content"
        },
        {
            "text": "The Indian government is oppressive and violates human rights in Kashmir.",
            "expected_sentiment": SentimentType.ANTI_INDIA,
            "description": "Critical political content"
        },
        
        # Neutral content
        {
            "text": "The weather is nice today. I had lunch with my friends.",
            "expected_sentiment": SentimentType.NEUTRAL,
            "description": "Generic neutral content"
        },
        {
            "text": "India has a population of over 1.4 billion people and many different languages.",
            "expected_sentiment": SentimentType.NEUTRAL,
            "description": "Factual India content"
        },
        
        # Propaganda techniques
        {
            "text": "All Indians are terrorists and enemies of peace. They destroy everything they touch!",
            "expected_sentiment": SentimentType.ANTI_INDIA,
            "description": "Content with propaganda techniques",
            "expected_techniques": [PropagandaTechnique.LOADED_LANGUAGE, PropagandaTechnique.NAME_CALLING]
        },
        
        # Non-English content (Hindi)
        {
            "text": "भारत एक महान देश है और हमें इस पर गर्व है।",
            "expected_sentiment": SentimentType.PRO_INDIA,
            "description": "Hindi content (should be translated)"
        }
    ]
    
    print("\n📊 Running Individual Sentiment Analysis Tests")
    print("-" * 50)
    
    correct_predictions = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['description']}")
        print(f"Text: {test_case['text'][:100]}{'...' if len(test_case['text']) > 100 else ''}")
        
        try:
            result = await analyzer.analyze_sentiment(test_case['text'])
            
            print(f"Predicted: {result.sentiment} (confidence: {result.confidence:.3f})")
            print(f"Risk Score: {result.risk_score:.3f}")
            print(f"Processing Time: {result.processing_time_ms:.2f}ms")
            
            if result.translated_text:
                print(f"Translated: {result.translated_text[:100]}{'...' if len(result.translated_text) > 100 else ''}")
                print(f"Translation Confidence: {result.translation_confidence:.3f}")
            
            if result.propaganda_techniques:
                print(f"Propaganda Techniques: {result.propaganda_techniques}")
            
            # Check if prediction matches expected
            if result.sentiment == test_case['expected_sentiment']:
                print("✅ CORRECT")
                correct_predictions += 1
            else:
                print(f"❌ INCORRECT (expected: {test_case['expected_sentiment']})")
            
            # Check propaganda techniques if expected
            if 'expected_techniques' in test_case:
                expected_techniques = set(test_case['expected_techniques'])
                detected_techniques = set(result.propaganda_techniques)
                
                if expected_techniques.intersection(detected_techniques):
                    print("✅ Propaganda techniques detected correctly")
                else:
                    print(f"⚠️  Expected techniques: {expected_techniques}, Got: {detected_techniques}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    accuracy = correct_predictions / total_tests
    print(f"\n📈 Individual Test Results: {correct_predictions}/{total_tests} correct ({accuracy:.1%})")
    
    # Test batch processing
    print("\n🔄 Testing Batch Processing")
    print("-" * 50)
    
    batch_texts = [case['text'] for case in test_cases[:5]]  # Use first 5 test cases
    
    start_time = time.time()
    batch_results = await analyzer.batch_analyze_sentiment(batch_texts)
    batch_time = (time.time() - start_time) * 1000
    
    print(f"Batch processed {len(batch_texts)} texts in {batch_time:.2f}ms")
    print(f"Average time per text: {batch_time / len(batch_texts):.2f}ms")
    
    for i, result in enumerate(batch_results):
        print(f"Text {i+1}: {result.sentiment} (confidence: {result.confidence:.3f})")
    
    # Test model information
    print("\n📋 Model Information")
    print("-" * 50)
    
    model_info = analyzer.get_model_info()
    for key, value in model_info.items():
        print(f"{key}: {value}")
    
    # Test health check
    print("\n🏥 Health Check")
    print("-" * 50)
    
    health_status = await analyzer.health_check()
    for key, value in health_status.items():
        print(f"{key}: {value}")
    
    # Performance test
    print("\n⚡ Performance Test")
    print("-" * 50)
    
    performance_text = "This is a test sentence for performance evaluation."
    num_iterations = 10
    
    start_time = time.time()
    for _ in range(num_iterations):
        await analyzer.analyze_sentiment(performance_text, translate=False)
    
    total_time = (time.time() - start_time) * 1000
    avg_time = total_time / num_iterations
    
    print(f"Processed {num_iterations} texts in {total_time:.2f}ms")
    print(f"Average processing time: {avg_time:.2f}ms per text")
    print(f"Throughput: {1000 / avg_time:.1f} texts per second")
    
    print("\n✅ Sentiment Analyzer Testing Complete!")
    return accuracy


async def test_edge_cases():
    """Test edge cases and error handling."""
    
    print("\n🧪 Testing Edge Cases")
    print("-" * 50)
    
    analyzer = SentimentAnalyzer()
    await analyzer.initialize()
    
    edge_cases = [
        {
            "text": "",
            "description": "Empty text",
            "should_fail": True
        },
        {
            "text": "   ",
            "description": "Whitespace only",
            "should_fail": True
        },
        {
            "text": "a",
            "description": "Single character",
            "should_fail": False
        },
        {
            "text": "🇮🇳 🚀 💪",
            "description": "Emoji only",
            "should_fail": False
        },
        {
            "text": "x" * 10000,
            "description": "Very long text",
            "should_fail": False
        },
        {
            "text": "This is a normal sentence with some special characters: @#$%^&*()",
            "description": "Special characters",
            "should_fail": False
        }
    ]
    
    for i, case in enumerate(edge_cases, 1):
        print(f"\nEdge Case {i}: {case['description']}")
        
        try:
            if case['should_fail']:
                # For cases that should fail, we expect an exception
                try:
                    result = await analyzer.analyze_sentiment(case['text'])
                    print(f"❌ Expected failure but got result: {result.sentiment}")
                except Exception as e:
                    print(f"✅ Failed as expected: {type(e).__name__}")
            else:
                result = await analyzer.analyze_sentiment(case['text'])
                print(f"✅ Processed successfully: {result.sentiment} (confidence: {result.confidence:.3f})")
                
        except Exception as e:
            if case['should_fail']:
                print(f"✅ Failed as expected: {type(e).__name__}")
            else:
                print(f"❌ Unexpected error: {e}")


async def main():
    """Main test function."""
    try:
        # Run main tests
        accuracy = await test_sentiment_analyzer()
        
        # Run edge case tests
        await test_edge_cases()
        
        print(f"\n🎯 Overall Test Summary")
        print("=" * 50)
        print(f"Sentiment Analysis Accuracy: {accuracy:.1%}")
        print("✅ All tests completed successfully!")
        
        return accuracy >= 0.6  # Consider 60% accuracy as passing for demo
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        print(f"\n❌ Test suite failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)