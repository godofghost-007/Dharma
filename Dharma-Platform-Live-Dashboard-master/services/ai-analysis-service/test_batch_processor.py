#!/usr/bin/env python3
"""Test script for batch processing optimization."""

import asyncio
import sys
import os
import time
from pathlib import Path

# Add the project root to Python path
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_root)

try:
    from shared.models.post import SentimentType, PropagandaTechnique
except ImportError:
    # Define enums locally if import fails
    from enum import Enum
    
    class SentimentType(str, Enum):
        PRO_INDIA = "pro_india"
        NEUTRAL = "neutral"
        ANTI_INDIA = "anti_india"
    
    class PropagandaTechnique(str, Enum):
        LOADED_LANGUAGE = "loaded_language"
        NAME_CALLING = "name_calling"
        REPETITION = "repetition"
        APPEAL_TO_FEAR = "appeal_to_fear"
        BANDWAGON = "bandwagon"

# Import components
from test_sentiment_minimal import MockSentimentAnalyzer
from app.analysis.batch_processor import BatchProcessor, BatchConfig, ProgressTracker


def generate_test_texts(count: int) -> list:
    """Generate test texts for batch processing."""
    
    base_texts = [
        "India is making great progress in technology and innovation.",
        "The weather is nice today in Mumbai.",
        "India is a corrupt country with terrible policies.",
        "I love Indian food and culture.",
        "The government policies are questionable.",
        "Bollywood movies are entertaining.",
        "India has many beautiful temples and monuments.",
        "The traffic in Delhi is very heavy.",
        "Indian cricket team played well today.",
        "The economy is showing signs of growth."
    ]
    
    # Repeat and modify texts to reach desired count
    texts = []
    for i in range(count):
        base_text = base_texts[i % len(base_texts)]
        # Add variation to make each text unique
        modified_text = f"{base_text} (Sample {i+1})"
        texts.append(modified_text)
    
    return texts


async def test_basic_batch_processing():
    """Test basic batch processing functionality."""
    
    print("🔄 Testing Basic Batch Processing")
    print("=" * 50)
    
    # Initialize components
    analyzer = MockSentimentAnalyzer()
    await analyzer.initialize()
    
    config = BatchConfig(
        batch_size=5,
        max_concurrent_batches=2,
        timeout_seconds=10.0,
        retry_attempts=2
    )
    
    processor = BatchProcessor(analyzer, config)
    
    # Generate test data
    test_texts = generate_test_texts(20)
    
    print(f"Processing {len(test_texts)} texts with batch_size={config.batch_size}")
    
    # Track progress
    progress_tracker = ProgressTracker(len(test_texts), update_interval=5)
    
    def progress_callback(processed, total):
        progress_tracker.update(processed, total)
    
    # Process batch
    start_time = time.time()
    result = await processor.process_batch(
        test_texts,
        translate=False,
        progress_callback=progress_callback
    )
    total_time = time.time() - start_time
    
    # Display results
    print(f"\n📊 Batch Processing Results")
    print("-" * 30)
    print(f"Total Processed: {result.total_processed}")
    print(f"Successful: {result.successful_processed}")
    print(f"Failed: {result.failed_processed}")
    print(f"Total Time: {result.total_time_seconds:.2f}s")
    print(f"Avg Time per Text: {result.avg_time_per_text_ms:.2f}ms")
    print(f"Throughput: {result.throughput_per_second:.1f} texts/second")
    
    # Display batch statistics
    if result.batch_stats:
        print(f"\n📈 Batch Statistics")
        print("-" * 30)
        
        if 'sentiment_distribution' in result.batch_stats:
            print("Sentiment Distribution:")
            for sentiment, count in result.batch_stats['sentiment_distribution'].items():
                print(f"  {sentiment}: {count}")
        
        if 'confidence_stats' in result.batch_stats:
            conf_stats = result.batch_stats['confidence_stats']
            print(f"Confidence: mean={conf_stats['mean']:.3f}, std={conf_stats['std']:.3f}")
        
        if 'risk_stats' in result.batch_stats:
            risk_stats = result.batch_stats['risk_stats']
            print(f"Risk Score: mean={risk_stats['mean']:.3f}, std={risk_stats['std']:.3f}")
    
    # Display errors if any
    if result.error_details:
        print(f"\n❌ Errors ({len(result.error_details)}):")
        for error in result.error_details[:3]:  # Show first 3 errors
            print(f"  {error}")
    
    print(f"\n✅ Basic batch processing test completed")
    return result


async def test_performance_comparison():
    """Test performance comparison between different batch configurations."""
    
    print(f"\n⚡ Testing Performance Comparison")
    print("=" * 50)
    
    # Initialize analyzer
    analyzer = MockSentimentAnalyzer()
    await analyzer.initialize()
    
    # Test different configurations
    configs = [
        BatchConfig(batch_size=1, max_concurrent_batches=1),
        BatchConfig(batch_size=5, max_concurrent_batches=1),
        BatchConfig(batch_size=10, max_concurrent_batches=1),
        BatchConfig(batch_size=5, max_concurrent_batches=2),
        BatchConfig(batch_size=10, max_concurrent_batches=4),
    ]
    
    test_texts = generate_test_texts(50)
    results = []
    
    print(f"Testing {len(configs)} configurations with {len(test_texts)} texts")
    print("\nConfiguration | Batch Size | Concurrency | Time (s) | Throughput (texts/s)")
    print("-" * 80)
    
    for i, config in enumerate(configs):
        processor = BatchProcessor(analyzer, config)
        
        start_time = time.time()
        result = await processor.process_batch(test_texts, translate=False)
        
        results.append({
            'config': config,
            'result': result,
            'config_name': f"Config {i+1}"
        })
        
        print(f"{f'Config {i+1}':>13} | {config.batch_size:>10} | {config.max_concurrent_batches:>11} | "
              f"{result.total_time_seconds:>8.2f} | {result.throughput_per_second:>18.1f}")
    
    # Find best configuration
    best_result = max(results, key=lambda x: x['result'].throughput_per_second)
    
    print(f"\n🏆 Best Configuration: {best_result['config_name']}")
    print(f"   Throughput: {best_result['result'].throughput_per_second:.1f} texts/second")
    print(f"   Batch Size: {best_result['config'].batch_size}")
    print(f"   Concurrency: {best_result['config'].max_concurrent_batches}")
    
    return results


async def test_large_dataset_processing():
    """Test processing of large datasets with chunking."""
    
    print(f"\n📦 Testing Large Dataset Processing")
    print("=" * 50)
    
    # Initialize analyzer
    analyzer = MockSentimentAnalyzer()
    await analyzer.initialize()
    
    # Configuration for large dataset
    config = BatchConfig(
        batch_size=20,
        max_concurrent_batches=3,
        chunk_size=100,  # Small chunk size for testing
        timeout_seconds=15.0
    )
    
    processor = BatchProcessor(analyzer, config)
    
    # Generate large test dataset
    large_dataset = generate_test_texts(250)  # Larger than chunk_size
    
    print(f"Processing large dataset of {len(large_dataset)} texts")
    print(f"Chunk size: {config.chunk_size}")
    print(f"Expected chunks: {(len(large_dataset) + config.chunk_size - 1) // config.chunk_size}")
    
    # Track progress
    progress_tracker = ProgressTracker(len(large_dataset), update_interval=25)
    
    def progress_callback(processed, total):
        progress_tracker.update(processed, total)
    
    # Process large dataset
    start_time = time.time()
    result = await processor.process_batch(
        large_dataset,
        translate=False,
        progress_callback=progress_callback
    )
    
    # Display results
    print(f"\n📊 Large Dataset Results")
    print("-" * 30)
    print(f"Total Processed: {result.total_processed}")
    print(f"Successful: {result.successful_processed}")
    print(f"Failed: {result.failed_processed}")
    print(f"Success Rate: {(result.successful_processed / result.total_processed) * 100:.1f}%")
    print(f"Total Time: {result.total_time_seconds:.2f}s")
    print(f"Throughput: {result.throughput_per_second:.1f} texts/second")
    
    # Progress summary
    progress_summary = progress_tracker.get_summary()
    print(f"\n📈 Progress Summary")
    print("-" * 30)
    print(f"Progress: {progress_summary['progress_percentage']:.1f}%")
    print(f"Processing Rate: {progress_summary['processing_rate_per_second']:.1f} texts/second")
    print(f"Completed: {progress_summary['completed']}")
    
    return result


async def test_config_optimization():
    """Test automatic configuration optimization."""
    
    print(f"\n🎯 Testing Configuration Optimization")
    print("=" * 50)
    
    # Initialize analyzer
    analyzer = MockSentimentAnalyzer()
    await analyzer.initialize()
    
    processor = BatchProcessor(analyzer)
    
    # Test different scenarios
    scenarios = [
        {"dataset_size": 50, "target_throughput": 100, "description": "Small dataset, low throughput"},
        {"dataset_size": 500, "target_throughput": 500, "description": "Medium dataset, medium throughput"},
        {"dataset_size": 5000, "target_throughput": 1000, "description": "Large dataset, high throughput"},
        {"dataset_size": 50000, "target_throughput": 2000, "description": "Very large dataset, very high throughput"}
    ]
    
    print("Scenario | Dataset Size | Target Throughput | Batch Size | Concurrency | Chunk Size")
    print("-" * 90)
    
    for i, scenario in enumerate(scenarios):
        optimized_config = processor.optimize_config_for_dataset(
            scenario["dataset_size"],
            scenario["target_throughput"]
        )
        
        print(f"{f'Scenario {i+1}':>8} | {scenario['dataset_size']:>12} | "
              f"{scenario['target_throughput']:>17} | {optimized_config.batch_size:>10} | "
              f"{optimized_config.max_concurrent_batches:>11} | {optimized_config.chunk_size:>10}")
    
    # Test one optimized configuration
    print(f"\n🧪 Testing Optimized Configuration")
    print("-" * 40)
    
    test_scenario = scenarios[1]  # Medium scenario
    optimized_config = processor.optimize_config_for_dataset(
        test_scenario["dataset_size"],
        test_scenario["target_throughput"]
    )
    
    optimized_processor = BatchProcessor(analyzer, optimized_config)
    test_texts = generate_test_texts(100)  # Subset for testing
    
    result = await optimized_processor.process_batch(test_texts, translate=False)
    
    print(f"Optimized config performance:")
    print(f"  Throughput: {result.throughput_per_second:.1f} texts/second")
    print(f"  Target: {test_scenario['target_throughput']} texts/second")
    print(f"  Achievement: {(result.throughput_per_second / test_scenario['target_throughput']) * 100:.1f}%")
    
    return optimized_config


async def test_error_handling():
    """Test error handling and retry mechanisms."""
    
    print(f"\n🚨 Testing Error Handling")
    print("=" * 50)
    
    # Create a mock analyzer that sometimes fails
    class FailingMockAnalyzer(MockSentimentAnalyzer):
        def __init__(self, failure_rate=0.2):
            super().__init__()
            self.failure_rate = failure_rate
            self.call_count = 0
        
        async def analyze_sentiment(self, text, language=None, translate=True):
            self.call_count += 1
            # Simulate failures
            if self.call_count % 5 == 0:  # Fail every 5th call
                raise Exception(f"Simulated failure for call {self.call_count}")
            return await super().analyze_sentiment(text, language, translate)
    
    # Initialize failing analyzer
    failing_analyzer = FailingMockAnalyzer()
    await failing_analyzer.initialize()
    
    config = BatchConfig(
        batch_size=3,
        max_concurrent_batches=2,
        retry_attempts=2,
        timeout_seconds=5.0
    )
    
    processor = BatchProcessor(failing_analyzer, config)
    
    # Generate test data
    test_texts = generate_test_texts(15)
    
    print(f"Processing {len(test_texts)} texts with simulated failures")
    print(f"Retry attempts: {config.retry_attempts}")
    
    # Process with error handling
    result = await processor.process_batch(test_texts, translate=False)
    
    # Display results
    print(f"\n📊 Error Handling Results")
    print("-" * 30)
    print(f"Total Processed: {result.total_processed}")
    print(f"Successful: {result.successful_processed}")
    print(f"Failed: {result.failed_processed}")
    print(f"Success Rate: {(result.successful_processed / result.total_processed) * 100:.1f}%")
    print(f"Error Count: {len(result.error_details)}")
    
    if result.error_details:
        print(f"\n❌ Error Details:")
        for i, error in enumerate(result.error_details[:3]):
            print(f"  Error {i+1}: {error}")
    
    return result


async def main():
    """Main test function."""
    try:
        print("🚀 Starting Batch Processing Tests")
        print("=" * 80)
        
        # Test 1: Basic batch processing
        basic_result = await test_basic_batch_processing()
        
        # Test 2: Performance comparison
        perf_results = await test_performance_comparison()
        
        # Test 3: Large dataset processing
        large_result = await test_large_dataset_processing()
        
        # Test 4: Configuration optimization
        optimized_config = await test_config_optimization()
        
        # Test 5: Error handling
        error_result = await test_error_handling()
        
        # Summary
        print(f"\n🎯 Test Summary")
        print("=" * 80)
        print(f"✅ Basic Batch Processing: {basic_result.throughput_per_second:.1f} texts/second")
        print(f"✅ Performance Comparison: {len(perf_results)} configurations tested")
        print(f"✅ Large Dataset Processing: {large_result.total_processed} texts processed")
        print(f"✅ Configuration Optimization: Batch size {optimized_config.batch_size}")
        print(f"✅ Error Handling: {error_result.successful_processed}/{error_result.total_processed} successful")
        
        # Validate requirements
        requirements_met = {
            "batch_processing": basic_result.successful_processed > 0,
            "high_throughput": basic_result.throughput_per_second > 100,  # texts/second
            "large_dataset_support": large_result.total_processed >= 250,
            "error_handling": error_result.successful_processed > 0,
            "config_optimization": optimized_config.batch_size > 0
        }
        
        print(f"\n📋 Requirements Validation")
        print("-" * 40)
        for requirement, met in requirements_met.items():
            status = "✅" if met else "❌"
            print(f"{status} {requirement}: {met}")
        
        all_requirements_met = all(requirements_met.values())
        
        if all_requirements_met:
            print(f"\n🎉 All batch processing requirements successfully met!")
            return True
        else:
            print(f"\n⚠️  Some requirements not met. Check implementation.")
            return False
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)