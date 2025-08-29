"""Batch processing optimization for high-throughput sentiment analysis."""

import asyncio
import time
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import logging
from datetime import datetime
import queue
import threading

from shared.models.post import SentimentType
from ..models.requests import SentimentAnalysisResponse

logger = logging.getLogger(__name__)


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    
    batch_size: int = 32
    max_concurrent_batches: int = 4
    timeout_seconds: float = 30.0
    retry_attempts: int = 3
    use_multiprocessing: bool = False
    chunk_size: int = 1000  # For very large datasets
    
    def validate(self) -> None:
        """Validate configuration parameters."""
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.max_concurrent_batches <= 0:
            raise ValueError("max_concurrent_batches must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts must be non-negative")
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")


@dataclass
class BatchResult:
    """Result of batch processing operation."""
    
    results: List[SentimentAnalysisResponse]
    total_processed: int
    successful_processed: int
    failed_processed: int
    total_time_seconds: float
    avg_time_per_text_ms: float
    throughput_per_second: float
    error_details: List[Dict[str, Any]]
    batch_stats: Dict[str, Any]


class BatchProcessor:
    """High-performance batch processor for sentiment analysis."""
    
    def __init__(self, sentiment_analyzer, config: Optional[BatchConfig] = None):
        """Initialize batch processor.
        
        Args:
            sentiment_analyzer: Sentiment analyzer instance
            config: Batch processing configuration
        """
        self.sentiment_analyzer = sentiment_analyzer
        self.config = config or BatchConfig()
        self.config.validate()
        
        # Performance tracking
        self.total_processed = 0
        self.total_processing_time = 0.0
        self.batch_history = []
        
        # Thread/process pools
        self.thread_pool = None
        self.process_pool = None
        
        # Queue for managing work
        self.work_queue = queue.Queue()
        self.result_queue = queue.Queue()
        
        logger.info(f"BatchProcessor initialized with config: {self.config}")
    
    async def process_batch(
        self,
        texts: List[str],
        language: Optional[str] = None,
        translate: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> BatchResult:
        """Process a batch of texts with optimized performance.
        
        Args:
            texts: List of texts to analyze
            language: Language code (auto-detect if None)
            translate: Whether to translate non-English text
            progress_callback: Optional callback for progress updates
            
        Returns:
            BatchResult with processing results and statistics
        """
        if not texts:
            return BatchResult(
                results=[],
                total_processed=0,
                successful_processed=0,
                failed_processed=0,
                total_time_seconds=0.0,
                avg_time_per_text_ms=0.0,
                throughput_per_second=0.0,
                error_details=[],
                batch_stats={}
            )
        
        logger.info(f"Starting batch processing of {len(texts)} texts")
        start_time = time.time()
        
        # Split into chunks if dataset is very large
        if len(texts) > self.config.chunk_size:
            return await self._process_large_dataset(texts, language, translate, progress_callback)
        
        # Process in optimized batches
        results = []
        error_details = []
        processed_count = 0
        
        # Create batches
        batches = self._create_batches(texts)
        
        # Process batches concurrently
        if self.config.max_concurrent_batches > 1:
            batch_results = await self._process_batches_concurrent(
                batches, language, translate, progress_callback
            )
        else:
            batch_results = await self._process_batches_sequential(
                batches, language, translate, progress_callback
            )
        
        # Aggregate results
        for batch_result in batch_results:
            if isinstance(batch_result, list):
                results.extend(batch_result)
                processed_count += len(batch_result)
            else:
                # Handle error case
                error_details.append({
                    "error": str(batch_result),
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        total_time = time.time() - start_time
        successful_processed = len(results)
        failed_processed = len(texts) - successful_processed
        
        # Calculate performance metrics
        avg_time_per_text_ms = (total_time * 1000) / len(texts) if texts else 0.0
        throughput_per_second = len(texts) / total_time if total_time > 0 else 0.0
        
        # Update global stats
        self.total_processed += len(texts)
        self.total_processing_time += total_time
        
        # Create batch statistics
        batch_stats = self._calculate_batch_stats(results, total_time)
        
        # Store in history
        batch_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_texts": len(texts),
            "successful": successful_processed,
            "failed": failed_processed,
            "processing_time": total_time,
            "throughput": throughput_per_second
        }
        self.batch_history.append(batch_record)
        
        result = BatchResult(
            results=results,
            total_processed=len(texts),
            successful_processed=successful_processed,
            failed_processed=failed_processed,
            total_time_seconds=total_time,
            avg_time_per_text_ms=avg_time_per_text_ms,
            throughput_per_second=throughput_per_second,
            error_details=error_details,
            batch_stats=batch_stats
        )
        
        logger.info(f"Batch processing completed: {successful_processed}/{len(texts)} successful, "
                   f"{throughput_per_second:.1f} texts/second")
        
        return result
    
    def _create_batches(self, texts: List[str]) -> List[List[str]]:
        """Split texts into optimally sized batches."""
        batches = []
        batch_size = self.config.batch_size
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batches.append(batch)
        
        return batches
    
    async def _process_batches_concurrent(
        self,
        batches: List[List[str]],
        language: Optional[str],
        translate: bool,
        progress_callback: Optional[Callable[[int, int], None]]
    ) -> List[Any]:
        """Process batches concurrently with controlled parallelism."""
        
        semaphore = asyncio.Semaphore(self.config.max_concurrent_batches)
        
        async def process_single_batch(batch: List[str], batch_idx: int) -> List[SentimentAnalysisResponse]:
            async with semaphore:
                try:
                    # Process batch with retry logic
                    for attempt in range(self.config.retry_attempts + 1):
                        try:
                            batch_results = await asyncio.wait_for(
                                self.sentiment_analyzer.batch_analyze_sentiment(
                                    batch, language, translate
                                ),
                                timeout=self.config.timeout_seconds
                            )
                            
                            # Update progress
                            if progress_callback:
                                progress_callback(batch_idx + 1, len(batches))
                            
                            return batch_results
                            
                        except asyncio.TimeoutError:
                            if attempt < self.config.retry_attempts:
                                logger.warning(f"Batch {batch_idx} timed out, retrying (attempt {attempt + 1})")
                                await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
                            else:
                                raise
                        except Exception as e:
                            if attempt < self.config.retry_attempts:
                                logger.warning(f"Batch {batch_idx} failed, retrying (attempt {attempt + 1}): {e}")
                                await asyncio.sleep(1.0 * (attempt + 1))
                            else:
                                raise
                    
                except Exception as e:
                    logger.error(f"Batch {batch_idx} failed after all retries: {e}")
                    return e
        
        # Process all batches concurrently
        tasks = [
            process_single_batch(batch, idx)
            for idx, batch in enumerate(batches)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    async def _process_batches_sequential(
        self,
        batches: List[List[str]],
        language: Optional[str],
        translate: bool,
        progress_callback: Optional[Callable[[int, int], None]]
    ) -> List[List[SentimentAnalysisResponse]]:
        """Process batches sequentially."""
        
        results = []
        
        for idx, batch in enumerate(batches):
            try:
                batch_results = await self.sentiment_analyzer.batch_analyze_sentiment(
                    batch, language, translate
                )
                results.append(batch_results)
                
                # Update progress
                if progress_callback:
                    progress_callback(idx + 1, len(batches))
                    
            except Exception as e:
                logger.error(f"Batch {idx} failed: {e}")
                results.append(e)
        
        return results
    
    async def _process_large_dataset(
        self,
        texts: List[str],
        language: Optional[str],
        translate: bool,
        progress_callback: Optional[Callable[[int, int], None]]
    ) -> BatchResult:
        """Process very large datasets by chunking."""
        
        logger.info(f"Processing large dataset of {len(texts)} texts in chunks of {self.config.chunk_size}")
        
        all_results = []
        all_errors = []
        total_start_time = time.time()
        
        # Process in chunks
        num_chunks = (len(texts) + self.config.chunk_size - 1) // self.config.chunk_size
        
        for chunk_idx in range(num_chunks):
            start_idx = chunk_idx * self.config.chunk_size
            end_idx = min(start_idx + self.config.chunk_size, len(texts))
            chunk_texts = texts[start_idx:end_idx]
            
            logger.info(f"Processing chunk {chunk_idx + 1}/{num_chunks} ({len(chunk_texts)} texts)")
            
            # Process chunk
            chunk_result = await self.process_batch(
                chunk_texts, language, translate,
                lambda processed, total: progress_callback(
                    start_idx + processed, len(texts)
                ) if progress_callback else None
            )
            
            all_results.extend(chunk_result.results)
            all_errors.extend(chunk_result.error_details)
        
        total_time = time.time() - total_start_time
        successful_processed = len(all_results)
        failed_processed = len(texts) - successful_processed
        
        # Calculate final metrics
        avg_time_per_text_ms = (total_time * 1000) / len(texts)
        throughput_per_second = len(texts) / total_time
        
        batch_stats = self._calculate_batch_stats(all_results, total_time)
        
        return BatchResult(
            results=all_results,
            total_processed=len(texts),
            successful_processed=successful_processed,
            failed_processed=failed_processed,
            total_time_seconds=total_time,
            avg_time_per_text_ms=avg_time_per_text_ms,
            throughput_per_second=throughput_per_second,
            error_details=all_errors,
            batch_stats=batch_stats
        )
    
    def _calculate_batch_stats(
        self,
        results: List[SentimentAnalysisResponse],
        total_time: float
    ) -> Dict[str, Any]:
        """Calculate comprehensive batch statistics."""
        
        if not results:
            return {}
        
        # Sentiment distribution
        sentiment_counts = {}
        confidence_scores = []
        risk_scores = []
        processing_times = []
        propaganda_techniques = []
        
        for result in results:
            # Sentiment distribution
            sentiment = str(result.sentiment)
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
            
            # Collect metrics
            confidence_scores.append(result.confidence)
            risk_scores.append(result.risk_score)
            processing_times.append(result.processing_time_ms)
            propaganda_techniques.extend(result.propaganda_techniques)
        
        # Calculate statistics
        import numpy as np
        
        stats = {
            "sentiment_distribution": sentiment_counts,
            "confidence_stats": {
                "mean": float(np.mean(confidence_scores)),
                "std": float(np.std(confidence_scores)),
                "min": float(np.min(confidence_scores)),
                "max": float(np.max(confidence_scores)),
                "median": float(np.median(confidence_scores))
            },
            "risk_stats": {
                "mean": float(np.mean(risk_scores)),
                "std": float(np.std(risk_scores)),
                "min": float(np.min(risk_scores)),
                "max": float(np.max(risk_scores)),
                "median": float(np.median(risk_scores))
            },
            "processing_time_stats": {
                "mean_ms": float(np.mean(processing_times)),
                "std_ms": float(np.std(processing_times)),
                "min_ms": float(np.min(processing_times)),
                "max_ms": float(np.max(processing_times)),
                "median_ms": float(np.median(processing_times))
            },
            "propaganda_techniques": dict(
                (technique, propaganda_techniques.count(technique))
                for technique in set(propaganda_techniques)
            ),
            "total_processing_time": total_time,
            "batch_efficiency": len(results) / total_time if total_time > 0 else 0.0
        }
        
        return stats
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        
        avg_processing_time = (
            self.total_processing_time / self.total_processed
            if self.total_processed > 0 else 0.0
        )
        
        return {
            "total_texts_processed": self.total_processed,
            "total_processing_time_seconds": self.total_processing_time,
            "average_processing_time_per_text": avg_processing_time,
            "overall_throughput_per_second": (
                self.total_processed / self.total_processing_time
                if self.total_processing_time > 0 else 0.0
            ),
            "total_batches_processed": len(self.batch_history),
            "configuration": {
                "batch_size": self.config.batch_size,
                "max_concurrent_batches": self.config.max_concurrent_batches,
                "timeout_seconds": self.config.timeout_seconds,
                "retry_attempts": self.config.retry_attempts,
                "chunk_size": self.config.chunk_size
            }
        }
    
    def get_batch_history(self) -> List[Dict[str, Any]]:
        """Get batch processing history."""
        return self.batch_history.copy()
    
    def optimize_config_for_dataset(self, dataset_size: int, target_throughput: float) -> BatchConfig:
        """Suggest optimal configuration for a given dataset size and target throughput.
        
        Args:
            dataset_size: Number of texts to process
            target_throughput: Target throughput in texts per second
            
        Returns:
            Optimized BatchConfig
        """
        
        # Base configuration
        config = BatchConfig()
        
        # Adjust batch size based on dataset size
        if dataset_size < 100:
            config.batch_size = min(16, dataset_size)
        elif dataset_size < 1000:
            config.batch_size = 32
        elif dataset_size < 10000:
            config.batch_size = 64
        else:
            config.batch_size = 128
        
        # Adjust concurrency based on target throughput
        if target_throughput > 1000:
            config.max_concurrent_batches = 8
        elif target_throughput > 500:
            config.max_concurrent_batches = 4
        else:
            config.max_concurrent_batches = 2
        
        # Adjust chunk size for very large datasets
        if dataset_size > 50000:
            config.chunk_size = 5000
        elif dataset_size > 10000:
            config.chunk_size = 2000
        else:
            config.chunk_size = dataset_size
        
        # Adjust timeout based on batch size
        config.timeout_seconds = max(30.0, config.batch_size * 0.5)
        
        logger.info(f"Optimized config for dataset_size={dataset_size}, "
                   f"target_throughput={target_throughput}: {config}")
        
        return config
    
    async def cleanup(self):
        """Clean up resources."""
        if self.thread_pool:
            self.thread_pool.shutdown(wait=True)
        if self.process_pool:
            self.process_pool.shutdown(wait=True)
        
        logger.info("BatchProcessor cleanup completed")


class ProgressTracker:
    """Helper class for tracking batch processing progress."""
    
    def __init__(self, total_items: int, update_interval: int = 100):
        """Initialize progress tracker.
        
        Args:
            total_items: Total number of items to process
            update_interval: How often to log progress updates
        """
        self.total_items = total_items
        self.update_interval = update_interval
        self.processed_items = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        
    def update(self, processed: int, total: int = None):
        """Update progress.
        
        Args:
            processed: Number of items processed
            total: Total items (if different from initial)
        """
        self.processed_items = processed
        if total:
            self.total_items = total
        
        current_time = time.time()
        
        # Log progress at intervals
        if (processed % self.update_interval == 0 or 
            processed == self.total_items or
            current_time - self.last_update_time > 10.0):  # At least every 10 seconds
            
            elapsed_time = current_time - self.start_time
            progress_pct = (processed / self.total_items) * 100 if self.total_items > 0 else 0
            
            if elapsed_time > 0:
                rate = processed / elapsed_time
                eta_seconds = (self.total_items - processed) / rate if rate > 0 else 0
                
                logger.info(f"Progress: {processed}/{self.total_items} ({progress_pct:.1f}%) "
                           f"Rate: {rate:.1f} items/sec ETA: {eta_seconds:.0f}s")
            
            self.last_update_time = current_time
    
    def get_summary(self) -> Dict[str, Any]:
        """Get progress summary."""
        elapsed_time = time.time() - self.start_time
        rate = self.processed_items / elapsed_time if elapsed_time > 0 else 0
        
        return {
            "processed_items": self.processed_items,
            "total_items": self.total_items,
            "progress_percentage": (self.processed_items / self.total_items) * 100 if self.total_items > 0 else 0,
            "elapsed_time_seconds": elapsed_time,
            "processing_rate_per_second": rate,
            "completed": self.processed_items >= self.total_items
        }