"""Model evaluation and metrics module for sentiment analysis."""

import asyncio
import time
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict, Counter
import logging
import json
import numpy as np
from datetime import datetime, timedelta

from shared.models.post import SentimentType, PropagandaTechnique
from ..models.requests import SentimentAnalysisResponse

logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetrics:
    """Container for evaluation metrics."""
    
    accuracy: float
    precision: Dict[str, float]
    recall: Dict[str, float]
    f1_score: Dict[str, float]
    confusion_matrix: Dict[str, Dict[str, int]]
    macro_avg_precision: float
    macro_avg_recall: float
    macro_avg_f1: float
    weighted_avg_precision: float
    weighted_avg_recall: float
    weighted_avg_f1: float
    
    # Performance metrics
    avg_processing_time_ms: float
    throughput_per_second: float
    
    # Confidence metrics
    avg_confidence: float
    confidence_distribution: Dict[str, int]
    
    # Risk assessment metrics
    avg_risk_score: float
    risk_distribution: Dict[str, int]
    
    # Propaganda detection metrics
    propaganda_detection_rate: float
    propaganda_techniques_distribution: Dict[str, int]


@dataclass
class TestCase:
    """Test case for model evaluation."""
    
    text: str
    expected_sentiment: SentimentType
    expected_propaganda_techniques: Optional[List[PropagandaTechnique]] = None
    language: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None


class ModelEvaluator:
    """Evaluates sentiment analysis model performance."""
    
    def __init__(self, sentiment_analyzer):
        """Initialize evaluator with sentiment analyzer instance."""
        self.sentiment_analyzer = sentiment_analyzer
        self.evaluation_history = []
        
    async def evaluate_model(
        self, 
        test_cases: List[TestCase],
        include_performance_metrics: bool = True
    ) -> EvaluationMetrics:
        """Evaluate model performance on test cases.
        
        Args:
            test_cases: List of test cases to evaluate
            include_performance_metrics: Whether to include timing metrics
            
        Returns:
            EvaluationMetrics with comprehensive evaluation results
        """
        logger.info(f"Starting model evaluation with {len(test_cases)} test cases")
        
        predictions = []
        ground_truth = []
        processing_times = []
        confidences = []
        risk_scores = []
        propaganda_predictions = []
        propaganda_ground_truth = []
        
        start_time = time.time()
        
        # Run predictions
        for i, test_case in enumerate(test_cases):
            try:
                case_start_time = time.time()
                
                result = await self.sentiment_analyzer.analyze_sentiment(
                    test_case.text,
                    language=test_case.language
                )
                
                case_processing_time = (time.time() - case_start_time) * 1000
                
                # Collect predictions and metrics
                predictions.append(result.sentiment)
                ground_truth.append(test_case.expected_sentiment)
                processing_times.append(case_processing_time)
                confidences.append(result.confidence)
                risk_scores.append(result.risk_score)
                
                # Propaganda technique evaluation
                if test_case.expected_propaganda_techniques is not None:
                    propaganda_predictions.append(set(result.propaganda_techniques))
                    propaganda_ground_truth.append(set(test_case.expected_propaganda_techniques))
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(test_cases)} test cases")
                    
            except Exception as e:
                logger.error(f"Error processing test case {i}: {e}")
                # Add default values for failed cases
                predictions.append(SentimentType.NEUTRAL)
                ground_truth.append(test_case.expected_sentiment)
                processing_times.append(0.0)
                confidences.append(0.0)
                risk_scores.append(0.5)
        
        total_time = time.time() - start_time
        
        # Calculate metrics
        metrics = self._calculate_metrics(
            predictions=predictions,
            ground_truth=ground_truth,
            processing_times=processing_times,
            confidences=confidences,
            risk_scores=risk_scores,
            propaganda_predictions=propaganda_predictions,
            propaganda_ground_truth=propaganda_ground_truth,
            total_time=total_time
        )
        
        # Store evaluation in history
        evaluation_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "num_test_cases": len(test_cases),
            "metrics": metrics,
            "model_version": getattr(self.sentiment_analyzer, 'model_version', 'unknown')
        }
        self.evaluation_history.append(evaluation_record)
        
        logger.info(f"Model evaluation completed. Accuracy: {metrics.accuracy:.3f}")
        
        return metrics
    
    def _calculate_metrics(
        self,
        predictions: List[SentimentType],
        ground_truth: List[SentimentType],
        processing_times: List[float],
        confidences: List[float],
        risk_scores: List[float],
        propaganda_predictions: List[set],
        propaganda_ground_truth: List[set],
        total_time: float
    ) -> EvaluationMetrics:
        """Calculate comprehensive evaluation metrics."""
        
        # Basic classification metrics
        accuracy = sum(p == g for p, g in zip(predictions, ground_truth)) / len(predictions)
        
        # Per-class metrics
        sentiment_types = list(SentimentType)
        precision = {}
        recall = {}
        f1_score = {}
        confusion_matrix = defaultdict(lambda: defaultdict(int))
        
        # Build confusion matrix
        for pred, true in zip(predictions, ground_truth):
            confusion_matrix[true][pred] += 1
        
        # Calculate per-class metrics
        for sentiment in sentiment_types:
            # True positives, false positives, false negatives
            tp = confusion_matrix[sentiment][sentiment]
            fp = sum(confusion_matrix[other][sentiment] for other in sentiment_types if other != sentiment)
            fn = sum(confusion_matrix[sentiment][other] for other in sentiment_types if other != sentiment)
            
            # Precision, recall, F1
            precision[sentiment] = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall[sentiment] = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1_score[sentiment] = (
                2 * precision[sentiment] * recall[sentiment] / 
                (precision[sentiment] + recall[sentiment])
                if (precision[sentiment] + recall[sentiment]) > 0 else 0.0
            )
        
        # Macro and weighted averages
        macro_avg_precision = np.mean(list(precision.values()))
        macro_avg_recall = np.mean(list(recall.values()))
        macro_avg_f1 = np.mean(list(f1_score.values()))
        
        # Weighted averages (by support)
        sentiment_counts = Counter(ground_truth)
        total_samples = len(ground_truth)
        
        weighted_avg_precision = sum(
            precision[sentiment] * sentiment_counts[sentiment] / total_samples
            for sentiment in sentiment_types
        )
        weighted_avg_recall = sum(
            recall[sentiment] * sentiment_counts[sentiment] / total_samples
            for sentiment in sentiment_types
        )
        weighted_avg_f1 = sum(
            f1_score[sentiment] * sentiment_counts[sentiment] / total_samples
            for sentiment in sentiment_types
        )
        
        # Performance metrics
        avg_processing_time_ms = np.mean(processing_times) if processing_times else 0.0
        throughput_per_second = len(predictions) / total_time if total_time > 0 else 0.0
        
        # Confidence metrics
        avg_confidence = np.mean(confidences) if confidences else 0.0
        confidence_distribution = self._create_distribution(confidences, bins=5)
        
        # Risk assessment metrics
        avg_risk_score = np.mean(risk_scores) if risk_scores else 0.0
        risk_distribution = self._create_distribution(risk_scores, bins=5)
        
        # Propaganda detection metrics
        propaganda_detection_rate = 0.0
        propaganda_techniques_distribution = {}
        
        if propaganda_predictions and propaganda_ground_truth:
            # Calculate propaganda detection accuracy
            propaganda_correct = sum(
                len(pred.intersection(true)) > 0 if len(true) > 0 else len(pred) == 0
                for pred, true in zip(propaganda_predictions, propaganda_ground_truth)
            )
            propaganda_detection_rate = propaganda_correct / len(propaganda_predictions)
            
            # Count propaganda techniques
            all_techniques = []
            for pred_set in propaganda_predictions:
                all_techniques.extend(list(pred_set))
            propaganda_techniques_distribution = dict(Counter(all_techniques))
        
        return EvaluationMetrics(
            accuracy=accuracy,
            precision={str(k): v for k, v in precision.items()},
            recall={str(k): v for k, v in recall.items()},
            f1_score={str(k): v for k, v in f1_score.items()},
            confusion_matrix={
                str(true): {str(pred): count for pred, count in pred_dict.items()}
                for true, pred_dict in confusion_matrix.items()
            },
            macro_avg_precision=macro_avg_precision,
            macro_avg_recall=macro_avg_recall,
            macro_avg_f1=macro_avg_f1,
            weighted_avg_precision=weighted_avg_precision,
            weighted_avg_recall=weighted_avg_recall,
            weighted_avg_f1=weighted_avg_f1,
            avg_processing_time_ms=avg_processing_time_ms,
            throughput_per_second=throughput_per_second,
            avg_confidence=avg_confidence,
            confidence_distribution=confidence_distribution,
            avg_risk_score=avg_risk_score,
            risk_distribution=risk_distribution,
            propaganda_detection_rate=propaganda_detection_rate,
            propaganda_techniques_distribution=propaganda_techniques_distribution
        )
    
    def _create_distribution(self, values: List[float], bins: int = 5) -> Dict[str, int]:
        """Create distribution histogram for values."""
        if not values:
            return {}
        
        min_val, max_val = min(values), max(values)
        if min_val == max_val:
            return {f"{min_val:.2f}": len(values)}
        
        bin_width = (max_val - min_val) / bins
        distribution = {}
        
        for i in range(bins):
            bin_start = min_val + i * bin_width
            bin_end = min_val + (i + 1) * bin_width
            
            if i == bins - 1:  # Last bin includes max value
                count = sum(1 for v in values if bin_start <= v <= bin_end)
            else:
                count = sum(1 for v in values if bin_start <= v < bin_end)
            
            distribution[f"{bin_start:.2f}-{bin_end:.2f}"] = count
        
        return distribution
    
    async def benchmark_performance(
        self,
        test_text: str = "This is a test sentence for performance benchmarking.",
        num_iterations: int = 100,
        batch_sizes: List[int] = None
    ) -> Dict[str, Any]:
        """Benchmark model performance with different configurations.
        
        Args:
            test_text: Text to use for benchmarking
            num_iterations: Number of iterations for single prediction benchmark
            batch_sizes: List of batch sizes to test
            
        Returns:
            Performance benchmark results
        """
        if batch_sizes is None:
            batch_sizes = [1, 5, 10, 20, 50]
        
        logger.info(f"Starting performance benchmark with {num_iterations} iterations")
        
        results = {
            "single_prediction": {},
            "batch_prediction": {},
            "timestamp": datetime.utcnow().isoformat(),
            "test_text_length": len(test_text)
        }
        
        # Single prediction benchmark
        processing_times = []
        
        for i in range(num_iterations):
            start_time = time.time()
            await self.sentiment_analyzer.analyze_sentiment(test_text, translate=False)
            processing_time = (time.time() - start_time) * 1000
            processing_times.append(processing_time)
        
        results["single_prediction"] = {
            "iterations": num_iterations,
            "avg_time_ms": np.mean(processing_times),
            "min_time_ms": np.min(processing_times),
            "max_time_ms": np.max(processing_times),
            "std_time_ms": np.std(processing_times),
            "throughput_per_second": 1000 / np.mean(processing_times)
        }
        
        # Batch prediction benchmark
        batch_results = {}
        
        for batch_size in batch_sizes:
            batch_texts = [test_text] * batch_size
            
            start_time = time.time()
            await self.sentiment_analyzer.batch_analyze_sentiment(batch_texts, translate=False)
            total_time = (time.time() - start_time) * 1000
            
            batch_results[str(batch_size)] = {
                "batch_size": batch_size,
                "total_time_ms": total_time,
                "avg_time_per_text_ms": total_time / batch_size if batch_size > 0 else 0.0,
                "throughput_per_second": (batch_size * 1000) / total_time if total_time > 0 else 0.0
            }
        
        results["batch_prediction"] = batch_results
        
        logger.info("Performance benchmark completed")
        return results
    
    def generate_evaluation_report(self, metrics: EvaluationMetrics) -> str:
        """Generate a comprehensive evaluation report.
        
        Args:
            metrics: Evaluation metrics to report
            
        Returns:
            Formatted evaluation report
        """
        report = []
        report.append("=" * 60)
        report.append("SENTIMENT ANALYSIS MODEL EVALUATION REPORT")
        report.append("=" * 60)
        
        # Overall performance
        report.append("\n📊 OVERALL PERFORMANCE")
        report.append("-" * 30)
        report.append(f"Accuracy: {metrics.accuracy:.3f} ({metrics.accuracy*100:.1f}%)")
        report.append(f"Macro Avg Precision: {metrics.macro_avg_precision:.3f}")
        report.append(f"Macro Avg Recall: {metrics.macro_avg_recall:.3f}")
        report.append(f"Macro Avg F1-Score: {metrics.macro_avg_f1:.3f}")
        
        # Per-class performance
        report.append("\n📈 PER-CLASS PERFORMANCE")
        report.append("-" * 30)
        for sentiment in SentimentType:
            sentiment_str = str(sentiment)
            if sentiment_str in metrics.precision:
                report.append(f"{sentiment_str}:")
                report.append(f"  Precision: {metrics.precision[sentiment_str]:.3f}")
                report.append(f"  Recall: {metrics.recall[sentiment_str]:.3f}")
                report.append(f"  F1-Score: {metrics.f1_score[sentiment_str]:.3f}")
        
        # Confusion matrix
        report.append("\n🔄 CONFUSION MATRIX")
        report.append("-" * 30)
        sentiments = list(SentimentType)
        
        # Header
        header = "True\\Pred".ljust(12)
        for sentiment in sentiments:
            header += str(sentiment).split('.')[-1][:8].ljust(10)
        report.append(header)
        
        # Matrix rows
        for true_sentiment in sentiments:
            true_str = str(true_sentiment)
            row = str(true_sentiment).split('.')[-1][:10].ljust(12)
            
            for pred_sentiment in sentiments:
                pred_str = str(pred_sentiment)
                count = metrics.confusion_matrix.get(true_str, {}).get(pred_str, 0)
                row += str(count).ljust(10)
            
            report.append(row)
        
        # Performance metrics
        report.append("\n⚡ PERFORMANCE METRICS")
        report.append("-" * 30)
        report.append(f"Avg Processing Time: {metrics.avg_processing_time_ms:.2f}ms")
        report.append(f"Throughput: {metrics.throughput_per_second:.1f} texts/second")
        
        # Confidence and risk metrics
        report.append("\n🎯 CONFIDENCE & RISK METRICS")
        report.append("-" * 30)
        report.append(f"Average Confidence: {metrics.avg_confidence:.3f}")
        report.append(f"Average Risk Score: {metrics.avg_risk_score:.3f}")
        
        # Propaganda detection
        if metrics.propaganda_detection_rate > 0:
            report.append("\n🚨 PROPAGANDA DETECTION")
            report.append("-" * 30)
            report.append(f"Detection Rate: {metrics.propaganda_detection_rate:.3f}")
            
            if metrics.propaganda_techniques_distribution:
                report.append("Techniques Detected:")
                for technique, count in metrics.propaganda_techniques_distribution.items():
                    report.append(f"  {technique}: {count}")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)
    
    def get_evaluation_history(self) -> List[Dict[str, Any]]:
        """Get evaluation history."""
        return self.evaluation_history.copy()
    
    def export_metrics(self, metrics: EvaluationMetrics, filepath: str) -> None:
        """Export metrics to JSON file.
        
        Args:
            metrics: Metrics to export
            filepath: Path to save the metrics
        """
        metrics_dict = {
            "accuracy": metrics.accuracy,
            "precision": metrics.precision,
            "recall": metrics.recall,
            "f1_score": metrics.f1_score,
            "confusion_matrix": metrics.confusion_matrix,
            "macro_averages": {
                "precision": metrics.macro_avg_precision,
                "recall": metrics.macro_avg_recall,
                "f1_score": metrics.macro_avg_f1
            },
            "weighted_averages": {
                "precision": metrics.weighted_avg_precision,
                "recall": metrics.weighted_avg_recall,
                "f1_score": metrics.weighted_avg_f1
            },
            "performance": {
                "avg_processing_time_ms": metrics.avg_processing_time_ms,
                "throughput_per_second": metrics.throughput_per_second
            },
            "confidence": {
                "average": metrics.avg_confidence,
                "distribution": metrics.confidence_distribution
            },
            "risk": {
                "average": metrics.avg_risk_score,
                "distribution": metrics.risk_distribution
            },
            "propaganda_detection": {
                "rate": metrics.propaganda_detection_rate,
                "techniques_distribution": metrics.propaganda_techniques_distribution
            },
            "export_timestamp": datetime.utcnow().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metrics_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Metrics exported to {filepath}")


def create_india_specific_test_cases() -> List[TestCase]:
    """Create comprehensive test cases for India-specific sentiment analysis."""
    
    test_cases = [
        # Pro-India cases
        TestCase(
            text="India is making incredible progress in technology and space exploration. Proud to be Indian!",
            expected_sentiment=SentimentType.PRO_INDIA,
            description="Positive technology progress",
            category="pro_india_tech"
        ),
        TestCase(
            text="Modi government's digital initiatives are transforming India for the better.",
            expected_sentiment=SentimentType.PRO_INDIA,
            description="Pro-government policy",
            category="pro_india_policy"
        ),
        TestCase(
            text="Indian culture and traditions are beautiful and should be celebrated worldwide.",
            expected_sentiment=SentimentType.PRO_INDIA,
            description="Cultural appreciation",
            category="pro_india_culture"
        ),
        
        # Anti-India cases
        TestCase(
            text="India is a corrupt country with terrible policies that harm its people.",
            expected_sentiment=SentimentType.ANTI_INDIA,
            expected_propaganda_techniques=[PropagandaTechnique.LOADED_LANGUAGE],
            description="Negative policy criticism",
            category="anti_india_policy"
        ),
        TestCase(
            text="The Indian government is oppressive and violates human rights in Kashmir.",
            expected_sentiment=SentimentType.ANTI_INDIA,
            description="Human rights criticism",
            category="anti_india_rights"
        ),
        TestCase(
            text="All Indians are terrorists and enemies of peace. They destroy everything!",
            expected_sentiment=SentimentType.ANTI_INDIA,
            expected_propaganda_techniques=[PropagandaTechnique.LOADED_LANGUAGE, PropagandaTechnique.NAME_CALLING],
            description="Hate speech with propaganda",
            category="anti_india_hate"
        ),
        
        # Neutral cases
        TestCase(
            text="India has a population of over 1.4 billion people and many different languages.",
            expected_sentiment=SentimentType.NEUTRAL,
            description="Factual information",
            category="neutral_facts"
        ),
        TestCase(
            text="The weather in Delhi is hot during summer months.",
            expected_sentiment=SentimentType.NEUTRAL,
            description="Weather information",
            category="neutral_weather"
        ),
        TestCase(
            text="I had lunch with my friends today. The food was good.",
            expected_sentiment=SentimentType.NEUTRAL,
            description="Personal experience",
            category="neutral_personal"
        ),
        
        # Edge cases
        TestCase(
            text="🇮🇳 India 🚀 Space Mission Success! 💪",
            expected_sentiment=SentimentType.PRO_INDIA,
            description="Emoji-heavy positive",
            category="edge_emoji"
        ),
        TestCase(
            text="India... is... a... country... in... Asia...",
            expected_sentiment=SentimentType.NEUTRAL,
            description="Fragmented text",
            category="edge_fragmented"
        ),
        
        # Multi-language (Hindi examples)
        TestCase(
            text="भारत एक महान देश है और हमें इस पर गर्व है।",
            expected_sentiment=SentimentType.PRO_INDIA,
            language="hi",
            description="Hindi positive content",
            category="multilingual_hindi"
        ),
    ]
    
    return test_cases