"""
Metrics collection system for Project Dharma
Provides Prometheus metrics collection and custom business metrics
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
from functools import wraps
import threading
from collections import defaultdict, Counter

from prometheus_client import (
    Counter as PrometheusCounter,
    Histogram,
    Gauge,
    Summary,
    Info,
    Enum as PrometheusEnum,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
    start_http_server
)
import psutil
import aioredis
from elasticsearch import AsyncElasticsearch


class MetricType(Enum):
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    SUMMARY = "summary"
    INFO = "info"
    ENUM = "enum"


@dataclass
class MetricDefinition:
    """Metric definition"""
    name: str
    description: str
    metric_type: MetricType
    labels: List[str] = None
    buckets: List[float] = None  # For histograms
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = []


class MetricsCollector:
    """Main metrics collector for Dharma platform"""
    
    def __init__(self, service_name: str, port: int = 9090):
        self.service_name = service_name
        self.port = port
        self.registry = CollectorRegistry()
        
        # Metric storage
        self.metrics = {}
        self.custom_collectors = []
        
        # Background tasks
        self.background_tasks = []
        self.running = False
        
        self._setup_default_metrics()
        self._setup_system_metrics()
    
    def _setup_default_metrics(self):
        """Setup default application metrics"""
        default_metrics = [
            MetricDefinition(
                name="http_requests_total",
                description="Total HTTP requests",
                metric_type=MetricType.COUNTER,
                labels=["method", "endpoint", "status"]
            ),
            MetricDefinition(
                name="http_request_duration_seconds",
                description="HTTP request duration in seconds",
                metric_type=MetricType.HISTOGRAM,
                labels=["method", "endpoint"],
                buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
            ),
            MetricDefinition(
                name="http_request_size_bytes",
                description="HTTP request size in bytes",
                metric_type=MetricType.HISTOGRAM,
                labels=["method", "endpoint"],
                buckets=[100, 1000, 10000, 100000, 1000000]
            ),
            MetricDefinition(
                name="http_response_size_bytes",
                description="HTTP response size in bytes",
                metric_type=MetricType.HISTOGRAM,
                labels=["method", "endpoint"],
                buckets=[100, 1000, 10000, 100000, 1000000]
            ),
            MetricDefinition(
                name="database_connections_active",
                description="Active database connections",
                metric_type=MetricType.GAUGE,
                labels=["database"]
            ),
            MetricDefinition(
                name="database_query_duration_seconds",
                description="Database query duration in seconds",
                metric_type=MetricType.HISTOGRAM,
                labels=["database", "operation"],
                buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
            ),
            MetricDefinition(
                name="cache_operations_total",
                description="Total cache operations",
                metric_type=MetricType.COUNTER,
                labels=["operation", "result"]
            ),
            MetricDefinition(
                name="cache_hit_ratio",
                description="Cache hit ratio",
                metric_type=MetricType.GAUGE,
                labels=["cache_type"]
            )
        ]
        
        for metric_def in default_metrics:
            self.register_metric(metric_def)
    
    def _setup_system_metrics(self):
        """Setup system-level metrics"""
        system_metrics = [
            MetricDefinition(
                name="process_cpu_usage_percent",
                description="Process CPU usage percentage",
                metric_type=MetricType.GAUGE
            ),
            MetricDefinition(
                name="process_memory_usage_bytes",
                description="Process memory usage in bytes",
                metric_type=MetricType.GAUGE
            ),
            MetricDefinition(
                name="process_open_fds",
                description="Number of open file descriptors",
                metric_type=MetricType.GAUGE
            ),
            MetricDefinition(
                name="process_threads",
                description="Number of threads",
                metric_type=MetricType.GAUGE
            )
        ]
        
        for metric_def in system_metrics:
            self.register_metric(metric_def)
    
    def register_metric(self, metric_def: MetricDefinition):
        """Register a new metric"""
        if metric_def.name in self.metrics:
            return self.metrics[metric_def.name]
        
        if metric_def.metric_type == MetricType.COUNTER:
            metric = PrometheusCounter(
                metric_def.name,
                metric_def.description,
                metric_def.labels,
                registry=self.registry
            )
        elif metric_def.metric_type == MetricType.HISTOGRAM:
            metric = Histogram(
                metric_def.name,
                metric_def.description,
                metric_def.labels,
                buckets=metric_def.buckets,
                registry=self.registry
            )
        elif metric_def.metric_type == MetricType.GAUGE:
            metric = Gauge(
                metric_def.name,
                metric_def.description,
                metric_def.labels,
                registry=self.registry
            )
        elif metric_def.metric_type == MetricType.SUMMARY:
            metric = Summary(
                metric_def.name,
                metric_def.description,
                metric_def.labels,
                registry=self.registry
            )
        elif metric_def.metric_type == MetricType.INFO:
            metric = Info(
                metric_def.name,
                metric_def.description,
                registry=self.registry
            )
        elif metric_def.metric_type == MetricType.ENUM:
            metric = PrometheusEnum(
                metric_def.name,
                metric_def.description,
                states=['unknown'],  # Default state
                registry=self.registry
            )
        else:
            raise ValueError(f"Unsupported metric type: {metric_def.metric_type}")
        
        self.metrics[metric_def.name] = metric
        return metric
    
    def get_metric(self, name: str):
        """Get metric by name"""
        return self.metrics.get(name)
    
    def increment_counter(self, name: str, labels: Dict[str, str] = None, value: float = 1):
        """Increment counter metric"""
        metric = self.get_metric(name)
        if metric and hasattr(metric, 'inc'):
            if labels:
                metric.labels(**labels).inc(value)
            else:
                metric.inc(value)
    
    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Observe histogram metric"""
        metric = self.get_metric(name)
        if metric and hasattr(metric, 'observe'):
            if labels:
                metric.labels(**labels).observe(value)
            else:
                metric.observe(value)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set gauge metric value"""
        metric = self.get_metric(name)
        if metric and hasattr(metric, 'set'):
            if labels:
                metric.labels(**labels).set(value)
            else:
                metric.set(value)
    
    def observe_summary(self, name: str, value: float, labels: Dict[str, str] = None):
        """Observe summary metric"""
        metric = self.get_metric(name)
        if metric and hasattr(metric, 'observe'):
            if labels:
                metric.labels(**labels).observe(value)
            else:
                metric.observe(value)
    
    def set_info(self, name: str, info: Dict[str, str]):
        """Set info metric"""
        metric = self.get_metric(name)
        if metric and hasattr(metric, 'info'):
            metric.info(info)
    
    def set_enum(self, name: str, state: str):
        """Set enum metric state"""
        metric = self.get_metric(name)
        if metric and hasattr(metric, 'state'):
            metric.state(state)
    
    def start_http_server(self):
        """Start HTTP server for metrics endpoint"""
        start_http_server(self.port, registry=self.registry)
    
    def get_metrics_text(self) -> str:
        """Get metrics in Prometheus text format"""
        return generate_latest(self.registry).decode('utf-8')
    
    def start_background_collection(self):
        """Start background metrics collection"""
        self.running = True
        
        # Start system metrics collection
        system_task = threading.Thread(target=self._collect_system_metrics)
        system_task.daemon = True
        system_task.start()
        self.background_tasks.append(system_task)
    
    def stop_background_collection(self):
        """Stop background metrics collection"""
        self.running = False
    
    def _collect_system_metrics(self):
        """Collect system metrics in background"""
        process = psutil.Process()
        
        while self.running:
            try:
                # CPU usage
                cpu_percent = process.cpu_percent()
                self.set_gauge("process_cpu_usage_percent", cpu_percent)
                
                # Memory usage
                memory_info = process.memory_info()
                self.set_gauge("process_memory_usage_bytes", memory_info.rss)
                
                # File descriptors
                try:
                    num_fds = process.num_fds()
                    self.set_gauge("process_open_fds", num_fds)
                except AttributeError:
                    # Windows doesn't have num_fds
                    pass
                
                # Threads
                num_threads = process.num_threads()
                self.set_gauge("process_threads", num_threads)
                
                time.sleep(15)  # Collect every 15 seconds
            except Exception as e:
                print(f"Error collecting system metrics: {e}")
                time.sleep(15)
    
    def add_custom_collector(self, collector: Callable[[], Dict[str, float]]):
        """Add custom metrics collector"""
        self.custom_collectors.append(collector)


class BusinessMetricsCollector:
    """Collector for business-specific metrics"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self._setup_business_metrics()
    
    def _setup_business_metrics(self):
        """Setup business-specific metrics"""
        business_metrics = [
            MetricDefinition(
                name="posts_processed_total",
                description="Total posts processed",
                metric_type=MetricType.COUNTER,
                labels=["platform", "service"]
            ),
            MetricDefinition(
                name="posts_processing_duration_seconds",
                description="Post processing duration in seconds",
                metric_type=MetricType.HISTOGRAM,
                labels=["platform", "service"],
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
            ),
            MetricDefinition(
                name="sentiment_analysis_total",
                description="Total sentiment analyses performed",
                metric_type=MetricType.COUNTER,
                labels=["sentiment", "confidence_level"]
            ),
            MetricDefinition(
                name="bots_detected_total",
                description="Total bots detected",
                metric_type=MetricType.COUNTER,
                labels=["platform", "confidence_level"]
            ),
            MetricDefinition(
                name="campaigns_detected_total",
                description="Total campaigns detected",
                metric_type=MetricType.COUNTER,
                labels=["campaign_type", "severity"]
            ),
            MetricDefinition(
                name="alerts_generated_total",
                description="Total alerts generated",
                metric_type=MetricType.COUNTER,
                labels=["alert_type", "severity"]
            ),
            MetricDefinition(
                name="alerts_pending_total",
                description="Total pending alerts",
                metric_type=MetricType.GAUGE,
                labels=["severity"]
            ),
            MetricDefinition(
                name="user_sessions_active",
                description="Active user sessions",
                metric_type=MetricType.GAUGE
            ),
            MetricDefinition(
                name="api_rate_limit_hits_total",
                description="Total API rate limit hits",
                metric_type=MetricType.COUNTER,
                labels=["api", "user"]
            ),
            MetricDefinition(
                name="model_inference_duration_seconds",
                description="Model inference duration in seconds",
                metric_type=MetricType.HISTOGRAM,
                labels=["model_type", "model_version"],
                buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
            ),
            MetricDefinition(
                name="model_accuracy_score",
                description="Model accuracy score",
                metric_type=MetricType.GAUGE,
                labels=["model_type", "model_version"]
            )
        ]
        
        for metric_def in business_metrics:
            self.metrics_collector.register_metric(metric_def)
    
    def record_post_processed(self, platform: str, service: str, processing_time: float):
        """Record post processing metrics"""
        self.metrics_collector.increment_counter(
            "posts_processed_total",
            {"platform": platform, "service": service}
        )
        self.metrics_collector.observe_histogram(
            "posts_processing_duration_seconds",
            processing_time,
            {"platform": platform, "service": service}
        )
    
    def record_sentiment_analysis(self, sentiment: str, confidence: float):
        """Record sentiment analysis metrics"""
        confidence_level = "high" if confidence > 0.8 else "medium" if confidence > 0.6 else "low"
        self.metrics_collector.increment_counter(
            "sentiment_analysis_total",
            {"sentiment": sentiment, "confidence_level": confidence_level}
        )
    
    def record_bot_detection(self, platform: str, confidence: float):
        """Record bot detection metrics"""
        confidence_level = "high" if confidence > 0.8 else "medium" if confidence > 0.6 else "low"
        self.metrics_collector.increment_counter(
            "bots_detected_total",
            {"platform": platform, "confidence_level": confidence_level}
        )
    
    def record_campaign_detection(self, campaign_type: str, severity: str):
        """Record campaign detection metrics"""
        self.metrics_collector.increment_counter(
            "campaigns_detected_total",
            {"campaign_type": campaign_type, "severity": severity}
        )
    
    def record_alert_generated(self, alert_type: str, severity: str):
        """Record alert generation metrics"""
        self.metrics_collector.increment_counter(
            "alerts_generated_total",
            {"alert_type": alert_type, "severity": severity}
        )
    
    def update_pending_alerts(self, count: int, severity: str):
        """Update pending alerts count"""
        self.metrics_collector.set_gauge(
            "alerts_pending_total",
            count,
            {"severity": severity}
        )
    
    def update_active_sessions(self, count: int):
        """Update active user sessions count"""
        self.metrics_collector.set_gauge("user_sessions_active", count)
    
    def record_rate_limit_hit(self, api: str, user: str):
        """Record API rate limit hit"""
        self.metrics_collector.increment_counter(
            "api_rate_limit_hits_total",
            {"api": api, "user": user}
        )
    
    def record_model_inference(self, model_type: str, model_version: str, duration: float, accuracy: float = None):
        """Record model inference metrics"""
        self.metrics_collector.observe_histogram(
            "model_inference_duration_seconds",
            duration,
            {"model_type": model_type, "model_version": model_version}
        )
        
        if accuracy is not None:
            self.metrics_collector.set_gauge(
                "model_accuracy_score",
                accuracy,
                {"model_type": model_type, "model_version": model_version}
            )


def metrics_middleware(metrics_collector: MetricsCollector):
    """Middleware for automatic HTTP metrics collection"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(request, *args, **kwargs):
            start_time = time.time()
            method = request.method
            path = request.url.path
            
            try:
                response = await func(request, *args, **kwargs)
                status = str(response.status_code)
                
                # Record metrics
                metrics_collector.increment_counter(
                    "http_requests_total",
                    {"method": method, "endpoint": path, "status": status}
                )
                
                duration = time.time() - start_time
                metrics_collector.observe_histogram(
                    "http_request_duration_seconds",
                    duration,
                    {"method": method, "endpoint": path}
                )
                
                return response
            
            except Exception as e:
                # Record error
                metrics_collector.increment_counter(
                    "http_requests_total",
                    {"method": method, "endpoint": path, "status": "500"}
                )
                raise
        
        @wraps(func)
        def sync_wrapper(request, *args, **kwargs):
            start_time = time.time()
            method = getattr(request, 'method', 'GET')
            path = getattr(request, 'path', '/')
            
            try:
                response = func(request, *args, **kwargs)
                status = str(getattr(response, 'status_code', 200))
                
                # Record metrics
                metrics_collector.increment_counter(
                    "http_requests_total",
                    {"method": method, "endpoint": path, "status": status}
                )
                
                duration = time.time() - start_time
                metrics_collector.observe_histogram(
                    "http_request_duration_seconds",
                    duration,
                    {"method": method, "endpoint": path}
                )
                
                return response
            
            except Exception as e:
                # Record error
                metrics_collector.increment_counter(
                    "http_requests_total",
                    {"method": method, "endpoint": path, "status": "500"}
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Global metrics collector instance
_metrics_collector = None
_business_metrics = None

def get_metrics_collector(service_name: str = None, port: int = 9090) -> MetricsCollector:
    """Get global metrics collector instance"""
    global _metrics_collector
    
    if _metrics_collector is None:
        import os
        service_name = service_name or os.getenv('SERVICE_NAME', 'dharma-service')
        _metrics_collector = MetricsCollector(service_name, port)
    
    return _metrics_collector

def get_business_metrics(service_name: str = None) -> BusinessMetricsCollector:
    """Get business metrics collector"""
    global _business_metrics
    
    if _business_metrics is None:
        metrics_collector = get_metrics_collector(service_name)
        _business_metrics = BusinessMetricsCollector(metrics_collector)
    
    return _business_metrics


# Example usage and testing
if __name__ == "__main__":
    # Initialize metrics collector
    metrics = get_metrics_collector("test-service", 9091)
    business_metrics = get_business_metrics("test-service")
    
    # Start background collection
    metrics.start_background_collection()
    
    # Start HTTP server
    metrics.start_http_server()
    
    # Record some test metrics
    business_metrics.record_post_processed("twitter", "data-collection", 1.5)
    business_metrics.record_sentiment_analysis("pro-india", 0.85)
    business_metrics.record_bot_detection("twitter", 0.92)
    business_metrics.record_campaign_detection("disinformation", "high")
    business_metrics.record_alert_generated("security_breach", "critical")
    
    print("Metrics server started on port 9091")
    print("Visit http://localhost:9091/metrics to see metrics")
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        metrics.stop_background_collection()
        print("Metrics collection stopped")