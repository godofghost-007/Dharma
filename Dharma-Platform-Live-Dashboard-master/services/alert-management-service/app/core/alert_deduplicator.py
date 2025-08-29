"""Alert deduplication system to prevent spam and duplicate alerts."""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from shared.models.alert import Alert, AlertContext, AlertType

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class DeduplicationKey:
    """Key for alert deduplication."""
    alert_type: str
    content_hash: str
    platform: Optional[str]
    time_bucket: str  # Hour bucket for temporal grouping
    
    def __str__(self) -> str:
        return f"{self.alert_type}:{self.content_hash}:{self.platform}:{self.time_bucket}"


@dataclass
class DuplicateGroup:
    """Group of duplicate alerts."""
    key: DeduplicationKey
    alerts: List[str]  # Alert IDs
    first_seen: datetime
    last_seen: datetime
    count: int
    
    def add_alert(self, alert_id: str):
        """Add alert to duplicate group."""
        if alert_id not in self.alerts:
            self.alerts.append(alert_id)
            self.count += 1
            self.last_seen = datetime.utcnow()


class AlertDeduplicator:
    """Handles alert deduplication to prevent spam."""
    
    def __init__(self):
        self.deduplication_window = timedelta(
            minutes=config.alert_deduplication_window_minutes
        )
        self.duplicate_groups: Dict[str, DuplicateGroup] = {}
        self.alert_hashes: Dict[str, str] = {}  # alert_id -> hash
        self.similarity_threshold = 0.85
        
        # Content similarity cache
        self.content_similarity_cache: Dict[Tuple[str, str], float] = {}
    
    async def is_duplicate(self, alert_id: str, context: AlertContext) -> bool:
        """Check if alert is a duplicate of recent alerts."""
        try:
            # Generate deduplication key
            dedup_key = self._generate_deduplication_key(context)
            
            # Check for exact duplicates
            if await self._is_exact_duplicate(dedup_key):
                logger.debug(f"Alert {alert_id} is exact duplicate")
                await self._record_duplicate(alert_id, dedup_key)
                return True
            
            # Check for similar content duplicates
            if await self._is_similar_duplicate(alert_id, context):
                logger.debug(f"Alert {alert_id} is similar duplicate")
                return True
            
            # Record as new unique alert
            await self._record_new_alert(alert_id, dedup_key)
            return False
            
        except Exception as e:
            logger.error(f"Error checking duplicate for alert {alert_id}: {e}")
            return False
    
    def _generate_deduplication_key(self, context: AlertContext) -> DeduplicationKey:
        """Generate deduplication key from alert context."""
        # Create content hash from key elements
        content_elements = []
        
        # Add content samples
        if context.content_samples:
            content_elements.extend(context.content_samples)
        
        # Add keywords and hashtags
        if context.keywords_matched:
            content_elements.extend(sorted(context.keywords_matched))
        if context.hashtags_involved:
            content_elements.extend(sorted(context.hashtags_involved))
        
        # Add user and post IDs for exact matching
        if context.source_user_ids:
            content_elements.extend(sorted(context.source_user_ids))
        if context.source_post_ids:
            content_elements.extend(sorted(context.source_post_ids))
        
        # Create hash
        content_str = "|".join(content_elements)
        content_hash = hashlib.md5(content_str.encode()).hexdigest()[:12]
        
        # Create time bucket (hourly)
        time_bucket = context.detection_window_end.strftime("%Y%m%d_%H")
        
        return DeduplicationKey(
            alert_type=context.detection_method,
            content_hash=content_hash,
            platform=context.source_platform,
            time_bucket=time_bucket
        )
    
    async def _is_exact_duplicate(self, dedup_key: DeduplicationKey) -> bool:
        """Check for exact duplicate based on deduplication key."""
        key_str = str(dedup_key)
        
        if key_str in self.duplicate_groups:
            group = self.duplicate_groups[key_str]
            
            # Check if within deduplication window
            time_diff = datetime.utcnow() - group.last_seen
            if time_diff <= self.deduplication_window:
                return True
            else:
                # Clean up old group
                del self.duplicate_groups[key_str]
        
        return False
    
    async def _is_similar_duplicate(self, alert_id: str, context: AlertContext) -> bool:
        """Check for similar content duplicates."""
        if not context.content_samples:
            return False
        
        current_content = " ".join(context.content_samples)
        
        # Check against recent alerts
        cutoff_time = datetime.utcnow() - self.deduplication_window
        
        for group_key, group in list(self.duplicate_groups.items()):
            if group.last_seen < cutoff_time:
                # Clean up old group
                del self.duplicate_groups[group_key]
                continue
            
            # Skip if different platform (unless both are None)
            if (context.source_platform != group.key.platform and 
                not (context.source_platform is None and group.key.platform is None)):
                continue
            
            # Calculate content similarity
            similarity = await self._calculate_content_similarity(
                current_content,
                group.key.content_hash
            )
            
            if similarity >= self.similarity_threshold:
                logger.debug(f"Found similar duplicate with similarity {similarity:.3f}")
                await self._record_duplicate(alert_id, group.key)
                return True
        
        return False
    
    async def _calculate_content_similarity(self, content1: str, content_hash: str) -> float:
        """Calculate similarity between content and existing content hash."""
        # For now, use simple token-based similarity
        # In production, could use more sophisticated NLP similarity
        
        cache_key = (hashlib.md5(content1.encode()).hexdigest()[:8], content_hash)
        
        if cache_key in self.content_similarity_cache:
            return self.content_similarity_cache[cache_key]
        
        # Simple token-based similarity
        tokens1 = set(content1.lower().split())
        
        # For demonstration, assume we can retrieve content from hash
        # In practice, might store content samples in duplicate groups
        similarity = self._calculate_jaccard_similarity(tokens1, set())
        
        # Cache result
        self.content_similarity_cache[cache_key] = similarity
        
        # Limit cache size
        if len(self.content_similarity_cache) > 1000:
            # Remove oldest entries
            oldest_keys = list(self.content_similarity_cache.keys())[:100]
            for key in oldest_keys:
                del self.content_similarity_cache[key]
        
        return similarity
    
    def _calculate_jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set1 and not set2:
            return 1.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    async def _record_duplicate(self, alert_id: str, dedup_key: DeduplicationKey):
        """Record alert as duplicate."""
        key_str = str(dedup_key)
        
        if key_str in self.duplicate_groups:
            self.duplicate_groups[key_str].add_alert(alert_id)
        else:
            # This shouldn't happen, but handle gracefully
            group = DuplicateGroup(
                key=dedup_key,
                alerts=[alert_id],
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                count=1
            )
            self.duplicate_groups[key_str] = group
        
        # Record alert hash
        self.alert_hashes[alert_id] = dedup_key.content_hash
    
    async def _record_new_alert(self, alert_id: str, dedup_key: DeduplicationKey):
        """Record new unique alert."""
        key_str = str(dedup_key)
        
        group = DuplicateGroup(
            key=dedup_key,
            alerts=[alert_id],
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            count=1
        )
        self.duplicate_groups[key_str] = group
        
        # Record alert hash
        self.alert_hashes[alert_id] = dedup_key.content_hash
    
    async def get_duplicate_groups(self) -> List[Dict]:
        """Get current duplicate groups for monitoring."""
        groups = []
        
        for key_str, group in self.duplicate_groups.items():
            groups.append({
                "key": key_str,
                "alert_type": group.key.alert_type,
                "platform": group.key.platform,
                "count": group.count,
                "first_seen": group.first_seen.isoformat(),
                "last_seen": group.last_seen.isoformat(),
                "alert_ids": group.alerts
            })
        
        return groups
    
    async def cleanup_old_groups(self):
        """Clean up old duplicate groups."""
        cutoff_time = datetime.utcnow() - self.deduplication_window
        
        keys_to_remove = []
        for key_str, group in self.duplicate_groups.items():
            if group.last_seen < cutoff_time:
                keys_to_remove.append(key_str)
                
                # Clean up alert hashes
                for alert_id in group.alerts:
                    if alert_id in self.alert_hashes:
                        del self.alert_hashes[alert_id]
        
        for key in keys_to_remove:
            del self.duplicate_groups[key]
        
        logger.debug(f"Cleaned up {len(keys_to_remove)} old duplicate groups")
    
    async def get_deduplication_stats(self) -> Dict:
        """Get deduplication statistics."""
        total_groups = len(self.duplicate_groups)
        total_duplicates = sum(group.count - 1 for group in self.duplicate_groups.values())
        
        # Group by alert type
        type_stats = {}
        for group in self.duplicate_groups.values():
            alert_type = group.key.alert_type
            if alert_type not in type_stats:
                type_stats[alert_type] = {"groups": 0, "duplicates": 0}
            
            type_stats[alert_type]["groups"] += 1
            type_stats[alert_type]["duplicates"] += group.count - 1
        
        return {
            "total_groups": total_groups,
            "total_duplicates_prevented": total_duplicates,
            "by_type": type_stats,
            "cache_size": len(self.content_similarity_cache),
            "deduplication_window_minutes": config.alert_deduplication_window_minutes
        }


class ContentSimilarityCalculator:
    """Advanced content similarity calculator."""
    
    def __init__(self):
        self.min_content_length = 10
        self.stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
        }
    
    def calculate_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content strings."""
        if not content1 or not content2:
            return 0.0
        
        if len(content1) < self.min_content_length or len(content2) < self.min_content_length:
            return 0.0
        
        # Normalize content
        tokens1 = self._normalize_content(content1)
        tokens2 = self._normalize_content(content2)
        
        if not tokens1 or not tokens2:
            return 0.0
        
        # Calculate multiple similarity metrics
        jaccard = self._jaccard_similarity(tokens1, tokens2)
        cosine = self._cosine_similarity(tokens1, tokens2)
        
        # Weighted combination
        return 0.6 * jaccard + 0.4 * cosine
    
    def _normalize_content(self, content: str) -> Set[str]:
        """Normalize content for similarity calculation."""
        # Convert to lowercase and split
        tokens = content.lower().split()
        
        # Remove punctuation and filter stopwords
        normalized = set()
        for token in tokens:
            # Remove punctuation
            clean_token = ''.join(c for c in token if c.isalnum())
            
            # Filter short tokens and stopwords
            if len(clean_token) >= 3 and clean_token not in self.stopwords:
                normalized.add(clean_token)
        
        return normalized
    
    def _jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """Calculate Jaccard similarity."""
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0.0
    
    def _cosine_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """Calculate cosine similarity."""
        intersection = len(set1.intersection(set2))
        magnitude = (len(set1) * len(set2)) ** 0.5
        return intersection / magnitude if magnitude > 0 else 0.0