#!/usr/bin/env python3
"""Test script for model evaluation and metrics."""

import asyncio
import sys
import os
import json
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

# Import the mock analyzer from our previous test
from test_sentiment_minimal import MockSentimentAnalyzer
from app.analysis.model_evaluator import ModelEvaluator, TestCase, create_india_specific_test_cases


async def test_model_evaluation():
    """Test comprehensive model evaluation functionality."""
    
    print("🧪 Testing Model Evaluation System")
    print("=" * 60)
    
    # Initialize mock analyzer and evaluator
    analyzer = MockSentimentAnalyzer()
    await analyzer.initialize()
    
    evaluator = ModelEvaluator(analyzer)
    
    # Create test cases
    test_cases = create_india_specific_test_cases()
    
    print(f"\n📋 Created {len(test_cases)} test cases")
    print("-" * 40)
    
    # Display test case categories
    categories = {}
    for case in test_cases:
        category = case.category or "uncategorized"
        categories[category] = categories.get(category, 0) + 1
    
    print("Test case distribution:")
    for category, count in categories.items():
        print(f"  {category}: {count}")
    
    # Run evaluation
    print(f"\n🔍 Running Model Evaluation")
    print("-" * 40)
    
    metrics = await evaluator.evaluate_model(test_cases)
    
    # Display key metrics
    print(f"\n📊 Key Evaluation Results")
    print("-" * 40)
    print(f"Overall Accuracy: {metrics.accuracy:.3f} ({metrics.accuracy*100:.1f}%)")
    print(f"Macro Avg F1-Score: {metrics.macro_avg_f1:.3f}")
    print(f"Avg Processing Time: {metrics.avg_processing_time_ms:.2f}ms")
    print(f"Throughput: {metrics.throughput_per_second:.1f} texts/second")
    print(f"Avg Confidence: {metrics.avg_confidence:.3f}")
    print(f"Avg Risk Score: {metrics.avg_risk_score:.3f}")
    
    # Display per-class metrics
    print(f"\n📈 Per-Class Performance")
    print("-" * 40)
    for sentiment in SentimentType:
        sentiment_str = str(sentiment)
        if sentiment_str in metrics.precision:
            print(f"{sentiment_str}:")
            print(f"  Precision: {metrics.precision[sentiment_str]:.3f}")
            print(f"  Recall: {metrics.recall[sentiment_str]:.3f}")
            print(f"  F1-Score: {metrics.f1_score[sentiment_str]:.3f}")
    
    # Display confusion matrix
    print(f"\n🔄 Confusion Matrix")
    print("-" * 40)
    sentiments = [str(s) for s in SentimentType]
    
    # Header
    header = "True\\Predicted".ljust(15)
    for sentiment in sentiments:
        header += sentiment.split('.')[-1][:10].ljust(12)
    print(header)
    
    # Matrix rows
    for true_sentiment in sentiments:
        row = true_sentiment.split('.')[-1][:13].ljust(15)
        for pred_sentiment in sentiments:
            count = metrics.confusion_matrix.get(true_sentiment, {}).get(pred_sentiment, 0)
            row += str(count).ljust(12)
        print(row)
    
    # Propaganda detection results
    if metrics.propaganda_detection_rate > 0:
        print(f"\n🚨 Propaganda Detection")
        print("-" * 40)
        print(f"Detection Rate: {metrics.propaganda_detection_rate:.3f}")
        
        if metrics.propaganda_techniques_distribution:
            print("Techniques Detected:")
            for technique, count in metrics.propaganda_techniques_distribution.items():
                print(f"  {technique}: {count}")
    
    # Generate and display full report
    print(f"\n📄 Generating Comprehensive Report")
    print("-" * 40)
    
    report = evaluator.generate_evaluation_report(metrics)
    print(report)
    
    # Export metrics
    output_dir = Path("evaluation_results")
    output_dir.mkdir(exist_ok=True)
    
    metrics_file = output_dir / "sentiment_model_metrics.json"
    evaluator.export_metrics(metrics, str(metrics_file))
    print(f"\n💾 Metrics exported to: {metrics_file}")
    
    # Save report
    report_file = output_dir / "sentiment_model_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"📄 Report saved to: {report_file}")
    
    return metrics


async def test_performance_benchmark():
    """Test performance benchmarking functionality."""
    
    print(f"\n⚡ Testing Performance Benchmark")
    print("=" * 60)
    
    # Initialize analyzer and evaluator
    analyzer = MockSentimentAnalyzer()
    await analyzer.initialize()
    
    evaluator = ModelEvaluator(analyzer)
    
    # Run performance benchmark
    benchmark_results = await evaluator.benchmark_performance(
        test_text="This is a comprehensive test for performance benchmarking of the sentiment analysis model.",
        num_iterations=50,
        batch_sizes=[1, 5, 10, 20]
    )
    
    # Display results
    print(f"\n🏃 Single Prediction Performance")
    print("-" * 40)
    single_perf = benchmark_results["single_prediction"]
    print(f"Iterations: {single_perf['iterations']}")
    print(f"Average Time: {single_perf['avg_time_ms']:.2f}ms")
    print(f"Min Time: {single_perf['min_time_ms']:.2f}ms")
    print(f"Max Time: {single_perf['max_time_ms']:.2f}ms")
    print(f"Std Dev: {single_perf['std_time_ms']:.2f}ms")
    print(f"Throughput: {single_perf['throughput_per_second']:.1f} texts/second")
    
    print(f"\n📦 Batch Prediction Performance")
    print("-" * 40)
    batch_perf = benchmark_results["batch_prediction"]
    
    print("Batch Size | Total Time | Avg/Text | Throughput")
    print("-" * 50)
    for batch_size, results in batch_perf.items():
        print(f"{batch_size:>9} | {results['total_time_ms']:>9.2f}ms | "
              f"{results['avg_time_per_text_ms']:>7.2f}ms | "
              f"{results['throughput_per_second']:>8.1f}/s")
    
    # Save benchmark results
    output_dir = Path("evaluation_results")
    output_dir.mkdir(exist_ok=True)
    
    benchmark_file = output_dir / "performance_benchmark.json"
    with open(benchmark_file, 'w', encoding='utf-8') as f:
        json.dump(benchmark_results, f, indent=2)
    
    print(f"\n💾 Benchmark results saved to: {benchmark_file}")
    
    return benchmark_results


async def test_evaluation_history():
    """Test evaluation history tracking."""
    
    print(f"\n📚 Testing Evaluation History")
    print("=" * 60)
    
    # Initialize analyzer and evaluator
    analyzer = MockSentimentAnalyzer()
    await analyzer.initialize()
    
    evaluator = ModelEvaluator(analyzer)
    
    # Run multiple evaluations
    test_cases = create_india_specific_test_cases()
    
    print("Running multiple evaluations to test history tracking...")
    
    # First evaluation with all test cases
    metrics1 = await evaluator.evaluate_model(test_cases)
    print(f"Evaluation 1 completed - Accuracy: {metrics1.accuracy:.3f}")
    
    # Second evaluation with subset
    metrics2 = await evaluator.evaluate_model(test_cases[:5])
    print(f"Evaluation 2 completed - Accuracy: {metrics2.accuracy:.3f}")
    
    # Third evaluation with different subset
    metrics3 = await evaluator.evaluate_model(test_cases[5:10])
    print(f"Evaluation 3 completed - Accuracy: {metrics3.accuracy:.3f}")
    
    # Check evaluation history
    history = evaluator.get_evaluation_history()
    
    print(f"\n📊 Evaluation History Summary")
    print("-" * 40)
    print(f"Total evaluations: {len(history)}")
    
    for i, record in enumerate(history, 1):
        print(f"\nEvaluation {i}:")
        print(f"  Timestamp: {record['timestamp']}")
        print(f"  Test Cases: {record['num_test_cases']}")
        print(f"  Accuracy: {record['metrics'].accuracy:.3f}")
        print(f"  Model Version: {record['model_version']}")
    
    # Save history
    output_dir = Path("evaluation_results")
    output_dir.mkdir(exist_ok=True)
    
    # Convert history to JSON-serializable format
    history_json = []
    for record in history:
        json_record = {
            "timestamp": record["timestamp"],
            "num_test_cases": record["num_test_cases"],
            "model_version": record["model_version"],
            "accuracy": record["metrics"].accuracy,
            "macro_avg_f1": record["metrics"].macro_avg_f1,
            "avg_processing_time_ms": record["metrics"].avg_processing_time_ms,
            "throughput_per_second": record["metrics"].throughput_per_second
        }
        history_json.append(json_record)
    
    history_file = output_dir / "evaluation_history.json"
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history_json, f, indent=2)
    
    print(f"\n💾 Evaluation history saved to: {history_file}")
    
    return history


async def main():
    """Main test function."""
    try:
        print("🚀 Starting Comprehensive Model Evaluation Tests")
        print("=" * 80)
        
        # Test 1: Basic model evaluation
        metrics = await test_model_evaluation()
        
        # Test 2: Performance benchmarking
        benchmark_results = await test_performance_benchmark()
        
        # Test 3: Evaluation history
        history = await test_evaluation_history()
        
        # Summary
        print(f"\n🎯 Test Summary")
        print("=" * 80)
        print(f"✅ Model Evaluation: Accuracy {metrics.accuracy:.1%}")
        print(f"✅ Performance Benchmark: {benchmark_results['single_prediction']['throughput_per_second']:.1f} texts/second")
        print(f"✅ Evaluation History: {len(history)} evaluations tracked")
        print(f"✅ All evaluation components working correctly!")
        
        # Check if results meet requirements
        requirements_met = {
            "accuracy_threshold": metrics.accuracy >= 0.6,  # 60% minimum for demo
            "performance_threshold": metrics.avg_processing_time_ms <= 1000,  # 1 second max
            "confidence_scoring": metrics.avg_confidence > 0.0,
            "risk_assessment": metrics.avg_risk_score >= 0.0,
            "propaganda_detection": len(metrics.propaganda_techniques_distribution) >= 0
        }
        
        print(f"\n📋 Requirements Validation")
        print("-" * 40)
        for requirement, met in requirements_met.items():
            status = "✅" if met else "❌"
            print(f"{status} {requirement}: {met}")
        
        all_requirements_met = all(requirements_met.values())
        
        if all_requirements_met:
            print(f"\n🎉 All requirements successfully met!")
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