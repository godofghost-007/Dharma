"""
Correlation ID system for distributed request tracking
"""

import uuid
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CorrelationContext:
    """Correlation context for distributed tracing"""
    correlation_id: str
    request_id: str
    user_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers"""
        headers = {}
        if self.correlation_id:
            headers['X-Correlation-ID'] = self.correlation_id
        if self.request_id:
            headers['X-Request-ID'] = self.request_id
        if self.user_id:
            headers['X-User-ID'] = self.user_id
        return headers
    
    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> 'CorrelationContext':
        """Create context from headers"""
        return cls(
            correlation_id=headers.get('X-Correlation-ID', str(uuid.uuid4())),
            request_id=headers.get('X-Request-ID', str(uuid.uuid4())),
            user_id=headers.get('X-User-ID')
        )


class CorrelationManager:
    """Manages correlation IDs"""
    
    def __init__(self):
        pass
    
    def generate_correlation_id(self) -> str:
        """Generate correlation ID"""
        return str(uuid.uuid4())
    
    def generate_request_id(self) -> str:
        """Generate request ID"""
        return f"req_{int(time.time() * 1000)}_{str(uuid.uuid4())[:8]}"


# Global instance
_correlation_manager = None

def get_correlation_manager() -> CorrelationManager:
    """Get global correlation manager"""
    global _correlation_manager
    if _correlation_manager is None:
        _correlation_manager = CorrelationManager()
    return _correlation_manager


if __name__ == "__main__":
    print("Testing correlation...")
    context = CorrelationContext("test", "req")
    print(f"Context: {context}")
    manager = get_correlation_manager()
    print(f"Manager: {manager}")
    print("Done")