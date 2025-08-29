"""
Advanced performance profiler with bottleneck identification
Integrates with distributed tracing for comprehensive performance monitoring
"""

import time
import asyncio
import threading
import psutil
import gc
import sys
import traceback
import cProfile
import pstats
import io
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import wraps
from contextlib import contextmanager
import json
import statistics

import aioredis
from opentelemetry import trace
from opentelemetry.trace.status import Status, StatusCode

from .tracer import get_tracer
from .correlation import get_correlation_id, get_request_id


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    operation_name: str
    duration: float
    cpu_usage: float
    memory_usage: float
    timestamp: datetime
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    success: bool = True
    error_type: Optional[str] = None
    thread_id: Optional[int] = None
    process_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class BottleneckInfo:
    """Bottleneck identification information"""
    operation_name: str
    bottleneck_type: str  # 'cpu', 'memory', 'io', 'network', 'database'
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    metrics: Dict[str, Any]
    recommendations: List[str]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class SystemMonitor:
    """System resource monitoring"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.system_metrics = deque(maxlen=1000)
        self.monitoring = False
        self._monitor_task = None
    
    def start_monitoring(self, interval: float = 1.0):
        """Start system monitoring"""
        if not self.monitoring:
            self.monitoring = True
            self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
    
    async def _monitor_loop(self, interval: float):
        """Background monitoring loop"""
        while self.monitoring:
            try:
                metrics = self.get_current_metrics()
                self.system_metrics.append(metrics)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in system monitoring: {e}")
                await asyncio.sleep(interval)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            process_memory = self.process.memory_info()
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            
            # Network I/O
            network_io = psutil.net_io_counters()
            
            # Process-specific metrics
            process_cpu = self.process.cpu_percent()
            process_threads = self.process.num_threads()
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'process_percent': process_cpu
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'process_rss': process_memory.rss,
                    'process_vms': process_memory.vms
                },
                'disk_io': {
                    'read_bytes': disk_io.read_bytes if disk_io else 0,
                    'write_bytes': disk_io.write_bytes if disk_io else 0,
                    'read_count': disk_io.read_count if disk_io else 0,
                    'write_count': disk_io.write_count if disk_io else 0
                } if disk_io else {},
                'network_io': {
                    'bytes_sent': network_io.bytes_sent if network_io else 0,
                    'bytes_recv': network_io.bytes_recv if network_io else 0,
                    'packets_sent': network_io.packets_sent if network_io else 0,
                    'packets_recv': network_io.packets_recv if network_io else 0
                } if network_io else {},
                'process': {
                    'threads': process_threads,
                    'pid': self.process.pid
                }
            }
        except Exception as e:
            print(f"Error getting system metrics: {e}")
            return {}
    
    def get_metrics_summary(self, duration: timedelta = timedelta(minutes=5)) -> Dict[str, Any]:
        """Get metrics summary for time period"""
        cutoff_time = datetime.utcnow() - duration
        
        recent_metrics = [
            m for m in self.system_metrics
            if datetime.fromisoformat(m['timestamp']) > cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        # Calculate averages and peaks
        cpu_values = [m['cpu']['percent'] for m in recent_metrics if 'cpu' in m]
        memory_values = [m['memory']['percent'] for m in recent_metrics if 'memory' in m]
        
        return {
            'duration_minutes': duration.total_seconds() / 60,
            'sample_count': len(recent_metrics),
            'cpu': {
                'avg': statistics.mean(cpu_values) if cpu_values else 0,
                'max': max(cpu_values) if cpu_values else 0,
                'min': min(cpu_values) if cpu_values else 0
            },
            'memory': {
                'avg': statistics.mean(memory_values) if memory_values else 0,
                'max': max(memory_values) if memory_values else 0,
                'min': min(memory_values) if memory_values else 0
            }
        }


class AdvancedPerformanceProfiler:
    """Advanced performance profiler with bottleneck identification"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.tracer = get_tracer()
        self.system_monitor = SystemMonitor()
        
        # Performance data storage
        self.performance_data = deque(maxlen=10000)
        self.bottlenecks = deque(maxlen=1000)
        
        # Thresholds for bottleneck detection
        self.thresholds = {
            'cpu_high': 80.0,
            'cpu_critical': 95.0,
            'memory_high': 80.0,
            'memory_critical': 95.0,
            'duration_slow': 1.0,
            'duration_very_slow': 5.0,
            'duration_critical': 10.0
        }
        
        # Profiling state
        self.active_profiles = {}
        self._lock = threading.Lock()
    
    async def initialize(self):
        """Initialize profiler"""
        self.redis_client = await aioredis.from_url(self.redis_url)
        self.system_monitor.start_monitoring()
    
    async def close(self):
        """Close profiler"""
        self.system_monitor.stop_monitoring()
        if self.redis_client:
            await self.redis_client.close()
    
    @contextmanager
    def profile_operation(self, operation_name: str, 
                         enable_cprofile: bool = False,
                         custom_attributes: Dict[str, Any] = None):
        """Context manager for profiling operations"""
        start_time = time.time()
        start_cpu = psutil.cpu_percent()
        start_memory = psutil.virtual_memory().percent
        
        # Start cProfile if requested
        profiler = None
        if enable_cprofile:
            profiler = cProfile.Profile()
            profiler.enable()
        
        # Get correlation IDs
        correlation_id = get_correlation_id()
        request_id = get_request_id()
        
        # Start tracing span
        span = self.tracer.start_span(f"profile.{operation_name}")
        span.set_attribute("profiling.enabled", True)
        span.set_attribute("profiling.cprofile", enable_cprofile)
        
        if correlation_id:
            span.set_attribute("correlation.id", correlation_id)
        if request_id:
            span.set_attribute("request.id", request_id)
        
        if custom_attributes:
            for key, value in custom_attributes.items():
                span.set_attribute(f"custom.{key}", str(value))
        
        try:
            with trace.use_span(span):
                yield span
        
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
        
        finally:
            # Stop cProfile
            profile_stats = None
            if profiler:
                profiler.disable()
                profile_stats = self._extract_profile_stats(profiler)
            
            # Calculate metrics
            end_time = time.time()
            duration = end_time - start_time
            end_cpu = psutil.cpu_percent()
            end_memory = psutil.virtual_memory().percent
            
            # Create performance metrics
            metrics = PerformanceMetrics(
                operation_name=operation_name,
                duration=duration,
                cpu_usage=max(end_cpu - start_cpu, 0),
                memory_usage=max(end_memory - start_memory, 0),
                timestamp=datetime.utcnow(),
                correlation_id=correlation_id,
                request_id=request_id,
                trace_id=self.tracer.get_trace_id(),
                span_id=self.tracer.get_span_id(),
                thread_id=threading.get_ident(),
                process_id=psutil.Process().pid
            )
            
            # Add span attributes
            span.set_attribute("performance.duration", duration)
            span.set_attribute("performance.cpu_usage", metrics.cpu_usage)
            span.set_attribute("performance.memory_usage", metrics.memory_usage)
            
            # Store metrics
            self.performance_data.append(metrics)
            asyncio.create_task(self._store_metrics(metrics, profile_stats))
            
            # Check for bottlenecks
            bottleneck = self._detect_bottleneck(metrics, profile_stats)
            if bottleneck:
                self.bottlenecks.append(bottleneck)
                asyncio.create_task(self._store_bottleneck(bottleneck))
                
                # Add bottleneck info to span
                span.set_attribute("bottleneck.detected", True)
                span.set_attribute("bottleneck.type", bottleneck.bottleneck_type)
                span.set_attribute("bottleneck.severity", bottleneck.severity)
                span.add_event("Bottleneck detected", {
                    "type": bottleneck.bottleneck_type,
                    "severity": bottleneck.severity,
                    "description": bottleneck.description
                })
            
            span.end()
    
    def _extract_profile_stats(self, profiler: cProfile.Profile) -> Dict[str, Any]:
        """Extract statistics from cProfile"""
        try:
            stats_stream = io.StringIO()
            stats = pstats.Stats(profiler, stream=stats_stream)
            stats.sort_stats('cumulative')
            stats.print_stats(20)  # Top 20 functions
            
            # Parse the output to extract key information
            stats_output = stats_stream.getvalue()
            
            # Get top functions by cumulative time
            stats.sort_stats('cumulative')
            top_functions = []
            
            for func, (cc, nc, tt, ct, callers) in stats.stats.items():
                if len(top_functions) < 10:  # Top 10 functions
                    top_functions.append({
                        'function': f"{func[0]}:{func[1]}({func[2]})",
                        'call_count': cc,
                        'total_time': tt,
                        'cumulative_time': ct,
                        'per_call': ct / cc if cc > 0 else 0
                    })
            
            return {
                'total_calls': stats.total_calls,
                'total_time': stats.total_tt,
                'top_functions': top_functions,
                'raw_output': stats_output[:2000]  # Truncate for storage
            }
        
        except Exception as e:
            return {'error': str(e)}
    
    def _detect_bottleneck(self, metrics: PerformanceMetrics, 
                          profile_stats: Dict[str, Any] = None) -> Optional[BottleneckInfo]:
        """Detect performance bottlenecks"""
        bottlenecks = []
        
        # Duration-based bottlenecks
        if metrics.duration > self.thresholds['duration_critical']:
            bottlenecks.append({
                'type': 'duration',
                'severity': 'critical',
                'description': f"Operation took {metrics.duration:.2f}s (critical threshold: {self.thresholds['duration_critical']}s)",
                'recommendations': [
                    "Review algorithm complexity",
                    "Consider caching frequently accessed data",
                    "Optimize database queries",
                    "Use async operations where possible"
                ]
            })
        elif metrics.duration > self.thresholds['duration_very_slow']:
            bottlenecks.append({
                'type': 'duration',
                'severity': 'high',
                'description': f"Operation took {metrics.duration:.2f}s (slow threshold: {self.thresholds['duration_very_slow']}s)",
                'recommendations': [
                    "Profile code to identify slow functions",
                    "Consider parallel processing",
                    "Optimize I/O operations"
                ]
            })
        
        # CPU-based bottlenecks
        if metrics.cpu_usage > self.thresholds['cpu_critical']:
            bottlenecks.append({
                'type': 'cpu',
                'severity': 'critical',
                'description': f"High CPU usage: {metrics.cpu_usage:.1f}%",
                'recommendations': [
                    "Optimize computational algorithms",
                    "Use multiprocessing for CPU-intensive tasks",
                    "Consider caching computed results",
                    "Profile CPU-intensive functions"
                ]
            })
        
        # Memory-based bottlenecks
        if metrics.memory_usage > self.thresholds['memory_critical']:
            bottlenecks.append({
                'type': 'memory',
                'severity': 'critical',
                'description': f"High memory usage increase: {metrics.memory_usage:.1f}%",
                'recommendations': [
                    "Review memory leaks",
                    "Optimize data structures",
                    "Use generators for large datasets",
                    "Implement proper garbage collection"
                ]
            })
        
        # Profile-based bottlenecks
        if profile_stats and 'top_functions' in profile_stats:
            top_function = profile_stats['top_functions'][0] if profile_stats['top_functions'] else None
            if top_function and top_function['cumulative_time'] > 0.5:  # Function taking >50% of time
                bottlenecks.append({
                    'type': 'function',
                    'severity': 'high',
                    'description': f"Function {top_function['function']} consuming {top_function['cumulative_time']:.2f}s",
                    'recommendations': [
                        f"Optimize function: {top_function['function']}",
                        "Consider algorithm improvements",
                        "Review function complexity"
                    ]
                })
        
        # Return the most severe bottleneck
        if bottlenecks:
            severity_order = {'critical': 3, 'high': 2, 'medium': 1, 'low': 0}
            most_severe = max(bottlenecks, key=lambda x: severity_order.get(x['severity'], 0))
            
            return BottleneckInfo(
                operation_name=metrics.operation_name,
                bottleneck_type=most_severe['type'],
                severity=most_severe['severity'],
                description=most_severe['description'],
                metrics=metrics.to_dict(),
                recommendations=most_severe['recommendations'],
                timestamp=datetime.utcnow()
            )
        
        return None
    
    async def _store_metrics(self, metrics: PerformanceMetrics, 
                           profile_stats: Dict[str, Any] = None):
        """Store performance metrics"""
        if not self.redis_client:
            return
        
        try:
            # Store individual metrics
            key = f"perf_metrics:{metrics.correlation_id or 'unknown'}:{int(time.time())}"
            data = metrics.to_dict()
            if profile_stats:
                data['profile_stats'] = profile_stats
            
            await self.redis_client.setex(key, 3600, json.dumps(data))
            
            # Store aggregated metrics by operation
            operation_key = f"perf_operation:{metrics.operation_name}"
            await self.redis_client.lpush(operation_key, json.dumps(data))
            await self.redis_client.ltrim(operation_key, 0, 999)  # Keep last 1000
            await self.redis_client.expire(operation_key, 86400)  # 24 hours
        
        except Exception as e:
            print(f"Error storing performance metrics: {e}")
    
    async def _store_bottleneck(self, bottleneck: BottleneckInfo):
        """Store bottleneck information"""
        if not self.redis_client:
            return
        
        try:
            key = f"bottleneck:{int(time.time())}"
            await self.redis_client.setex(key, 86400, json.dumps(bottleneck.to_dict()))
            
            # Store in bottleneck list
            bottleneck_list_key = "bottlenecks:recent"
            await self.redis_client.lpush(bottleneck_list_key, json.dumps(bottleneck.to_dict()))
            await self.redis_client.ltrim(bottleneck_list_key, 0, 99)  # Keep last 100
            await self.redis_client.expire(bottleneck_list_key, 86400)
        
        except Exception as e:
            print(f"Error storing bottleneck: {e}")
    
    def profile_function(self, operation_name: str = None,
                        enable_cprofile: bool = False,
                        custom_attributes: Dict[str, Any] = None):
        """Decorator for profiling functions"""
        def decorator(func):
            func_operation_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.profile_operation(
                    func_operation_name, 
                    enable_cprofile, 
                    custom_attributes
                ):
                    return await func(*args, **kwargs)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.profile_operation(
                    func_operation_name, 
                    enable_cprofile, 
                    custom_attributes
                ):
                    return func(*args, **kwargs)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    async def get_performance_summary(self, operation_name: str = None,
                                    time_range: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.redis_client:
            return {}
        
        try:
            if operation_name:
                # Get operation-specific metrics
                key = f"perf_operation:{operation_name}"
                metrics_data = await self.redis_client.lrange(key, 0, -1)
            else:
                # Get all recent metrics
                pattern = "perf_metrics:*"
                keys = await self.redis_client.keys(pattern)
                metrics_data = []
                for key in keys:
                    data = await self.redis_client.get(key)
                    if data:
                        metrics_data.append(data)
            
            if not metrics_data:
                return {}
            
            # Parse metrics
            metrics = []
            for data in metrics_data:
                try:
                    metric = json.loads(data)
                    metric_time = datetime.fromisoformat(metric['timestamp'])
                    if datetime.utcnow() - metric_time <= time_range:
                        metrics.append(metric)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
            
            if not metrics:
                return {}
            
            # Calculate summary statistics
            durations = [m['duration'] for m in metrics]
            cpu_usages = [m['cpu_usage'] for m in metrics]
            memory_usages = [m['memory_usage'] for m in metrics]
            
            return {
                'operation': operation_name or 'all',
                'time_range_hours': time_range.total_seconds() / 3600,
                'total_calls': len(metrics),
                'duration': {
                    'avg': statistics.mean(durations),
                    'min': min(durations),
                    'max': max(durations),
                    'p50': statistics.median(durations),
                    'p95': sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 20 else max(durations),
                    'p99': sorted(durations)[int(len(durations) * 0.99)] if len(durations) > 100 else max(durations)
                },
                'cpu_usage': {
                    'avg': statistics.mean(cpu_usages),
                    'max': max(cpu_usages)
                },
                'memory_usage': {
                    'avg': statistics.mean(memory_usages),
                    'max': max(memory_usages)
                },
                'slow_calls': len([d for d in durations if d > self.thresholds['duration_slow']]),
                'very_slow_calls': len([d for d in durations if d > self.thresholds['duration_very_slow']]),
                'critical_calls': len([d for d in durations if d > self.thresholds['duration_critical']])
            }
        
        except Exception as e:
            print(f"Error getting performance summary: {e}")
            return {}
    
    async def get_recent_bottlenecks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent bottlenecks"""
        if not self.redis_client:
            return []
        
        try:
            bottleneck_data = await self.redis_client.lrange("bottlenecks:recent", 0, limit - 1)
            bottlenecks = []
            
            for data in bottleneck_data:
                try:
                    bottleneck = json.loads(data)
                    bottlenecks.append(bottleneck)
                except (json.JSONDecodeError, TypeError):
                    continue
            
            return bottlenecks
        
        except Exception as e:
            print(f"Error getting recent bottlenecks: {e}")
            return []


# Global profiler instance
_profiler_instance = None

def get_profiler(redis_url: str = "redis://localhost:6379") -> AdvancedPerformanceProfiler:
    """Get global profiler instance"""
    global _profiler_instance
    
    if _profiler_instance is None:
        _profiler_instance = AdvancedPerformanceProfiler(redis_url)
    
    return _profiler_instance


# Example usage and testing
if __name__ == "__main__":
    async def test_profiler():
        profiler = get_profiler()
        await profiler.initialize()
        
        # Test profiling
        with profiler.profile_operation("test_operation", enable_cprofile=True):
            # Simulate some work
            time.sleep(0.1)
            
            # CPU intensive task
            sum(i * i for i in range(10000))
            
            # Memory allocation
            data = [i for i in range(100000)]
            del data
        
        # Test function decoration
        @profiler.profile_function("decorated_test", enable_cprofile=True)
        def test_function():
            time.sleep(0.05)
            return sum(i for i in range(50000))
        
        result = test_function()
        print(f"Function result: {result}")
        
        # Wait for async operations
        await asyncio.sleep(1)
        
        # Get performance summary
        summary = await profiler.get_performance_summary()
        print(f"Performance summary: {summary}")
        
        # Get bottlenecks
        bottlenecks = await profiler.get_recent_bottlenecks()
        print(f"Recent bottlenecks: {bottlenecks}")
        
        await profiler.close()
    
    # Run test
    asyncio.run(test_profiler())