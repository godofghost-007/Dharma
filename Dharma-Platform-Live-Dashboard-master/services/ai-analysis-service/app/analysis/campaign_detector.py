"""Campaign detection engine using graph theory and content similarity analysis."""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import networkx as nx
from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict, Counter
import hashlib

from shared.models.campaign import (
    Campaign, CampaignType, CoordinationMethod, SeverityLevel,
    NetworkMetrics, ContentMetrics, TemporalPattern, ImpactMetrics
)
from ..core.config import settings
from ..models.requests import CampaignDetectionResponse


logger = logging.getLogger(__name__)


class CampaignDetector:
    """Detects coordinated disinformation campaigns using graph analysis and content similarity."""
    
    def __init__(self):
        """Initialize the campaign detector."""
        self.model_version = "1.0.0"
        
        # Sentence transformer for content similarity
        self.sentence_transformer = None
        
        # Detection thresholds
        self.min_coordination_score = 0.6
        self.min_participants = 3
        self.content_similarity_threshold = 0.8
        self.temporal_window_minutes = 60
        
        # Performance tracking
        self.total_analyses = 0
        self.total_processing_time = 0.0
        
        # Campaign type classifiers
        self.campaign_classifiers = {
            CampaignType.DISINFORMATION: self._classify_disinformation,
            CampaignType.PROPAGANDA: self._classify_propaganda,
            CampaignType.ASTROTURFING: self._classify_astroturfing,
            CampaignType.HARASSMENT: self._classify_harassment,
            CampaignType.SPAM: self._classify_spam
        }
    
    async def initialize(self) -> None:
        """Initialize the campaign detection system."""
        try:
            logger.info("Initializing campaign detector")
            
            # Load sentence transformer model
            await self._load_sentence_transformer()
            
            logger.info("Campaign detector initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize campaign detector: {e}")
            raise
    
    async def _load_sentence_transformer(self) -> None:
        """Load sentence transformer model for content similarity."""
        try:
            # Use a lightweight model for demo purposes
            model_name = "all-MiniLM-L6-v2"
            self.sentence_transformer = SentenceTransformer(model_name)
            logger.info(f"Loaded sentence transformer: {model_name}")
            
        except Exception as e:
            logger.error(f"Error loading sentence transformer: {e}")
            raise
    
    async def detect_campaigns(
        self,
        posts_data: List[Dict[str, Any]],
        time_window_hours: float = 24.0,
        min_coordination_score: float = 0.6
    ) -> CampaignDetectionResponse:
        """Detect coordinated campaigns from posts data.
        
        Args:
            posts_data: List of post data dictionaries
            time_window_hours: Time window for campaign detection
            min_coordination_score: Minimum coordination score threshold
            
        Returns:
            CampaignDetectionResponse with detection results
        """
        start_time = time.time()
        
        try:
            if len(posts_data) < self.min_participants:
                return CampaignDetectionResponse(
                    campaigns_detected=0,
                    coordination_score=0.0,
                    participant_count=0,
                    content_similarity_score=0.0,
                    temporal_coordination_score=0.0,
                    processing_time_ms=(time.time() - start_time) * 1000
                )
            
            # Filter posts within time window
            filtered_posts = await self._filter_posts_by_time_window(posts_data, time_window_hours)
            
            # Analyze content similarity
            content_similarity_score = await self._analyze_content_similarity(filtered_posts)
            
            # Analyze temporal coordination
            temporal_coordination_score = await self._analyze_temporal_coordination(filtered_posts)
            
            # Build interaction network
            network_graph = await self._build_interaction_network(filtered_posts)
            
            # Calculate overall coordination score
            coordination_score = await self._calculate_coordination_score(
                content_similarity_score,
                temporal_coordination_score,
                network_graph
            )
            
            # Detect campaigns if coordination score is above threshold
            campaigns_detected = 0
            campaign_ids = []
            network_metrics = {}
            
            if coordination_score >= min_coordination_score:
                campaigns = await self._identify_campaign_clusters(
                    filtered_posts, network_graph, coordination_score
                )
                campaigns_detected = len(campaigns)
                campaign_ids = [campaign['campaign_id'] for campaign in campaigns]
                
                # Calculate network metrics
                network_metrics = await self._calculate_network_metrics(network_graph)
            
            processing_time = (time.time() - start_time) * 1000
            
            # Update performance tracking
            self.total_analyses += 1
            self.total_processing_time += processing_time
            
            return CampaignDetectionResponse(
                campaigns_detected=campaigns_detected,
                coordination_score=coordination_score,
                participant_count=len(set(post['user_id'] for post in filtered_posts)),
                content_similarity_score=content_similarity_score,
                temporal_coordination_score=temporal_coordination_score,
                network_metrics=network_metrics,
                campaign_ids=campaign_ids,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error detecting campaigns: {e}")
            raise
    
    async def _filter_posts_by_time_window(
        self,
        posts_data: List[Dict[str, Any]],
        time_window_hours: float
    ) -> List[Dict[str, Any]]:
        """Filter posts within the specified time window.
        
        Args:
            posts_data: List of post data
            time_window_hours: Time window in hours
            
        Returns:
            Filtered list of posts
        """
        try:
            if not posts_data:
                return []
            
            # Find the latest timestamp
            latest_timestamp = None
            for post in posts_data:
                timestamp_str = post.get('timestamp')
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        if latest_timestamp is None or timestamp > latest_timestamp:
                            latest_timestamp = timestamp
                    except ValueError:
                        continue
            
            if latest_timestamp is None:
                return posts_data  # Return all if no valid timestamps
            
            # Calculate time window
            time_threshold = latest_timestamp - timedelta(hours=time_window_hours)
            
            # Filter posts
            filtered_posts = []
            for post in posts_data:
                timestamp_str = post.get('timestamp')
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        if timestamp >= time_threshold:
                            filtered_posts.append(post)
                    except ValueError:
                        continue
            
            return filtered_posts
            
        except Exception as e:
            logger.error(f"Error filtering posts by time window: {e}")
            return posts_data
    
    async def _analyze_content_similarity(self, posts_data: List[Dict[str, Any]]) -> float:
        """Analyze content similarity across posts.
        
        Args:
            posts_data: List of post data
            
        Returns:
            Content similarity score (0.0 to 1.0)
        """
        try:
            if len(posts_data) < 2:
                return 0.0
            
            # Extract content texts
            contents = []
            for post in posts_data:
                content = post.get('content', '').strip()
                if content:
                    contents.append(content)
            
            if len(contents) < 2:
                return 0.0
            
            # Generate embeddings
            embeddings = self.sentence_transformer.encode(contents)
            
            # Calculate pairwise similarities
            similarity_matrix = cosine_similarity(embeddings)
            
            # Get upper triangle (excluding diagonal)
            n = len(similarity_matrix)
            similarities = []
            for i in range(n):
                for j in range(i + 1, n):
                    similarities.append(similarity_matrix[i][j])
            
            if not similarities:
                return 0.0
            
            # Calculate average similarity
            avg_similarity = np.mean(similarities)
            
            # Check for exact duplicates or near-duplicates
            high_similarity_count = sum(1 for sim in similarities if sim > self.content_similarity_threshold)
            duplicate_ratio = high_similarity_count / len(similarities) if similarities else 0
            
            # Boost score if many duplicates found
            if duplicate_ratio > 0.3:
                avg_similarity = min(1.0, avg_similarity + 0.2)
            
            return float(avg_similarity)
            
        except Exception as e:
            logger.error(f"Error analyzing content similarity: {e}")
            return 0.0
    
    async def _analyze_temporal_coordination(self, posts_data: List[Dict[str, Any]]) -> float:
        """Analyze temporal coordination patterns.
        
        Args:
            posts_data: List of post data
            
        Returns:
            Temporal coordination score (0.0 to 1.0)
        """
        try:
            if len(posts_data) < 2:
                return 0.0
            
            # Extract timestamps
            timestamps = []
            for post in posts_data:
                timestamp_str = post.get('timestamp')
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        timestamps.append(timestamp)
                    except ValueError:
                        continue
            
            if len(timestamps) < 2:
                return 0.0
            
            # Sort timestamps
            timestamps.sort()
            
            # Calculate time differences between consecutive posts
            time_diffs = []
            for i in range(1, len(timestamps)):
                diff = (timestamps[i] - timestamps[i-1]).total_seconds() / 60  # in minutes
                time_diffs.append(diff)
            
            if not time_diffs:
                return 0.0
            
            # Detect synchronized posting (posts within short time windows)
            synchronized_count = sum(1 for diff in time_diffs if diff <= self.temporal_window_minutes)
            synchronization_ratio = synchronized_count / len(time_diffs)
            
            # Calculate temporal clustering
            temporal_score = 0.0
            
            # Check for burst patterns
            burst_threshold = 5  # minutes
            burst_count = sum(1 for diff in time_diffs if diff <= burst_threshold)
            burst_ratio = burst_count / len(time_diffs)
            
            # Combine synchronization and burst patterns
            temporal_score = (synchronization_ratio * 0.6) + (burst_ratio * 0.4)
            
            return min(1.0, temporal_score)
            
        except Exception as e:
            logger.error(f"Error analyzing temporal coordination: {e}")
            return 0.0
    
    async def _build_interaction_network(self, posts_data: List[Dict[str, Any]]) -> nx.Graph:
        """Build interaction network from posts data.
        
        Args:
            posts_data: List of post data
            
        Returns:
            NetworkX graph representing user interactions
        """
        try:
            G = nx.Graph()
            
            # Add nodes (users)
            users = set()
            for post in posts_data:
                user_id = post.get('user_id')
                if user_id:
                    users.add(user_id)
                    G.add_node(user_id)
            
            # Add edges based on interactions
            user_posts = defaultdict(list)
            for post in posts_data:
                user_id = post.get('user_id')
                if user_id:
                    user_posts[user_id].append(post)
            
            # Create edges based on content similarity and temporal proximity
            user_list = list(users)
            for i in range(len(user_list)):
                for j in range(i + 1, len(user_list)):
                    user1, user2 = user_list[i], user_list[j]
                    
                    # Calculate interaction strength
                    interaction_strength = await self._calculate_interaction_strength(
                        user_posts[user1], user_posts[user2]
                    )
                    
                    if interaction_strength > 0.3:  # Threshold for creating edge
                        G.add_edge(user1, user2, weight=interaction_strength)
            
            return G
            
        except Exception as e:
            logger.error(f"Error building interaction network: {e}")
            return nx.Graph()
    
    async def _calculate_interaction_strength(
        self,
        user1_posts: List[Dict[str, Any]],
        user2_posts: List[Dict[str, Any]]
    ) -> float:
        """Calculate interaction strength between two users.
        
        Args:
            user1_posts: Posts from user 1
            user2_posts: Posts from user 2
            
        Returns:
            Interaction strength score (0.0 to 1.0)
        """
        try:
            if not user1_posts or not user2_posts:
                return 0.0
            
            # Extract content from posts
            user1_contents = [post.get('content', '') for post in user1_posts]
            user2_contents = [post.get('content', '') for post in user2_posts]
            
            # Calculate content similarity
            all_contents = user1_contents + user2_contents
            if len(all_contents) < 2:
                return 0.0
            
            embeddings = self.sentence_transformer.encode(all_contents)
            
            # Calculate cross-user similarities
            similarities = []
            for i in range(len(user1_contents)):
                for j in range(len(user1_contents), len(all_contents)):
                    sim = cosine_similarity([embeddings[i]], [embeddings[j]])[0][0]
                    similarities.append(sim)
            
            if not similarities:
                return 0.0
            
            content_similarity = np.mean(similarities)
            
            # Calculate temporal proximity
            user1_timestamps = []
            user2_timestamps = []
            
            for post in user1_posts:
                timestamp_str = post.get('timestamp')
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        user1_timestamps.append(timestamp)
                    except ValueError:
                        continue
            
            for post in user2_posts:
                timestamp_str = post.get('timestamp')
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        user2_timestamps.append(timestamp)
                    except ValueError:
                        continue
            
            temporal_proximity = 0.0
            if user1_timestamps and user2_timestamps:
                min_time_diff = float('inf')
                for t1 in user1_timestamps:
                    for t2 in user2_timestamps:
                        diff = abs((t1 - t2).total_seconds()) / 60  # in minutes
                        min_time_diff = min(min_time_diff, diff)
                
                # Convert time difference to proximity score
                if min_time_diff <= 60:  # Within 1 hour
                    temporal_proximity = 1.0 - (min_time_diff / 60)
            
            # Combine content similarity and temporal proximity
            interaction_strength = (content_similarity * 0.7) + (temporal_proximity * 0.3)
            
            return min(1.0, interaction_strength)
            
        except Exception as e:
            logger.error(f"Error calculating interaction strength: {e}")
            return 0.0
    
    async def _calculate_coordination_score(
        self,
        content_similarity: float,
        temporal_coordination: float,
        network_graph: nx.Graph
    ) -> float:
        """Calculate overall coordination score.
        
        Args:
            content_similarity: Content similarity score
            temporal_coordination: Temporal coordination score
            network_graph: Interaction network graph
            
        Returns:
            Overall coordination score (0.0 to 1.0)
        """
        try:
            # Network-based coordination metrics
            network_score = 0.0
            
            if len(network_graph.nodes()) > 1:
                # Calculate network density
                density = nx.density(network_graph)
                
                # Calculate clustering coefficient
                clustering = nx.average_clustering(network_graph)
                
                # Calculate connectivity
                connectivity = 1.0 if nx.is_connected(network_graph) else 0.5
                
                network_score = (density * 0.4) + (clustering * 0.4) + (connectivity * 0.2)
            
            # Combine all coordination indicators
            coordination_score = (
                content_similarity * 0.4 +
                temporal_coordination * 0.3 +
                network_score * 0.3
            )
            
            return min(1.0, coordination_score)
            
        except Exception as e:
            logger.error(f"Error calculating coordination score: {e}")
            return 0.0
    
    async def _identify_campaign_clusters(
        self,
        posts_data: List[Dict[str, Any]],
        network_graph: nx.Graph,
        coordination_score: float
    ) -> List[Dict[str, Any]]:
        """Identify distinct campaign clusters.
        
        Args:
            posts_data: List of post data
            network_graph: Interaction network graph
            coordination_score: Overall coordination score
            
        Returns:
            List of identified campaigns
        """
        try:
            campaigns = []
            
            # Find connected components in the network
            components = list(nx.connected_components(network_graph))
            
            for i, component in enumerate(components):
                if len(component) >= self.min_participants:
                    # Generate campaign ID
                    campaign_id = f"campaign_{int(time.time())}_{i}"
                    
                    # Get posts from campaign participants
                    campaign_posts = [
                        post for post in posts_data
                        if post.get('user_id') in component
                    ]
                    
                    # Classify campaign type
                    campaign_type = await self._classify_campaign_type(campaign_posts)
                    
                    # Calculate severity
                    severity = await self._calculate_campaign_severity(
                        campaign_posts, coordination_score
                    )
                    
                    # Detect coordination methods
                    coordination_methods = await self._detect_coordination_methods(campaign_posts)
                    
                    campaign = {
                        'campaign_id': campaign_id,
                        'name': f"Detected Campaign {i+1}",
                        'campaign_type': campaign_type,
                        'severity': severity,
                        'coordination_score': coordination_score,
                        'participant_count': len(component),
                        'content_count': len(campaign_posts),
                        'coordination_methods': coordination_methods,
                        'participant_user_ids': list(component),
                        'content_post_ids': [post.get('post_id') for post in campaign_posts if post.get('post_id')]
                    }
                    
                    campaigns.append(campaign)
            
            return campaigns
            
        except Exception as e:
            logger.error(f"Error identifying campaign clusters: {e}")
            return []
    
    async def _classify_campaign_type(self, campaign_posts: List[Dict[str, Any]]) -> CampaignType:
        """Classify the type of campaign based on content analysis.
        
        Args:
            campaign_posts: Posts from the campaign
            
        Returns:
            Classified campaign type
        """
        try:
            # Extract all content
            contents = [post.get('content', '') for post in campaign_posts]
            combined_content = ' '.join(contents).lower()
            
            # Score each campaign type
            type_scores = {}
            
            for campaign_type, classifier in self.campaign_classifiers.items():
                score = await classifier(combined_content, campaign_posts)
                type_scores[campaign_type] = score
            
            # Return the type with highest score
            if type_scores:
                best_type = max(type_scores, key=type_scores.get)
                if type_scores[best_type] > 0.3:  # Minimum confidence threshold
                    return best_type
            
            # Default to disinformation if no clear classification
            return CampaignType.DISINFORMATION
            
        except Exception as e:
            logger.error(f"Error classifying campaign type: {e}")
            return CampaignType.DISINFORMATION
    
    async def _classify_disinformation(
        self,
        combined_content: str,
        campaign_posts: List[Dict[str, Any]]
    ) -> float:
        """Classify disinformation campaign."""
        score = 0.0
        
        # Check for disinformation keywords
        disinfo_keywords = [
            'fake news', 'false', 'lie', 'hoax', 'conspiracy',
            'propaganda', 'misleading', 'deceptive'
        ]
        
        for keyword in disinfo_keywords:
            if keyword in combined_content:
                score += 0.2
        
        # Check for anti-India sentiment
        anti_india_keywords = ['anti-india', 'against india', 'india bad']
        for keyword in anti_india_keywords:
            if keyword in combined_content:
                score += 0.3
        
        return min(1.0, score)
    
    async def _classify_propaganda(
        self,
        combined_content: str,
        campaign_posts: List[Dict[str, Any]]
    ) -> float:
        """Classify propaganda campaign."""
        score = 0.0
        
        # Check for propaganda techniques
        propaganda_keywords = [
            'enemy', 'threat', 'destroy', 'fight', 'war',
            'patriot', 'nation', 'country', 'defend'
        ]
        
        for keyword in propaganda_keywords:
            if keyword in combined_content:
                score += 0.15
        
        return min(1.0, score)
    
    async def _classify_astroturfing(
        self,
        combined_content: str,
        campaign_posts: List[Dict[str, Any]]
    ) -> float:
        """Classify astroturfing campaign."""
        score = 0.0
        
        # Check for grassroots-like language
        astroturf_keywords = [
            'we the people', 'grassroots', 'ordinary citizens',
            'real people', 'authentic', 'genuine concern'
        ]
        
        for keyword in astroturf_keywords:
            if keyword in combined_content:
                score += 0.2
        
        # Check for coordinated messaging
        if len(set(post.get('content', '') for post in campaign_posts)) < len(campaign_posts) * 0.5:
            score += 0.3  # High content duplication
        
        return min(1.0, score)
    
    async def _classify_harassment(
        self,
        combined_content: str,
        campaign_posts: List[Dict[str, Any]]
    ) -> float:
        """Classify harassment campaign."""
        score = 0.0
        
        # Check for harassment keywords
        harassment_keywords = [
            'attack', 'target', 'harass', 'bully', 'threaten',
            'abuse', 'hate', 'troll', 'mob'
        ]
        
        for keyword in harassment_keywords:
            if keyword in combined_content:
                score += 0.2
        
        return min(1.0, score)
    
    async def _classify_spam(
        self,
        combined_content: str,
        campaign_posts: List[Dict[str, Any]]
    ) -> float:
        """Classify spam campaign."""
        score = 0.0
        
        # Check for spam indicators
        spam_keywords = [
            'click here', 'buy now', 'limited time', 'offer',
            'discount', 'free', 'win', 'prize'
        ]
        
        for keyword in spam_keywords:
            if keyword in combined_content:
                score += 0.15
        
        # Check for repetitive content
        contents = [post.get('content', '') for post in campaign_posts]
        unique_contents = set(contents)
        if len(unique_contents) < len(contents) * 0.3:
            score += 0.4  # Very high duplication indicates spam
        
        return min(1.0, score)
    
    async def _calculate_campaign_severity(
        self,
        campaign_posts: List[Dict[str, Any]],
        coordination_score: float
    ) -> SeverityLevel:
        """Calculate campaign severity level.
        
        Args:
            campaign_posts: Posts from the campaign
            coordination_score: Coordination score
            
        Returns:
            Severity level
        """
        try:
            # Base severity on coordination score
            if coordination_score >= 0.9:
                base_severity = 4  # Critical
            elif coordination_score >= 0.8:
                base_severity = 3  # High
            elif coordination_score >= 0.6:
                base_severity = 2  # Medium
            else:
                base_severity = 1  # Low
            
            # Adjust based on campaign size
            participant_count = len(set(post.get('user_id') for post in campaign_posts))
            if participant_count >= 50:
                base_severity += 1
            elif participant_count >= 20:
                base_severity += 0.5
            
            # Adjust based on content volume
            if len(campaign_posts) >= 100:
                base_severity += 1
            elif len(campaign_posts) >= 50:
                base_severity += 0.5
            
            # Map to severity levels
            if base_severity >= 4:
                return SeverityLevel.CRITICAL
            elif base_severity >= 3:
                return SeverityLevel.HIGH
            elif base_severity >= 2:
                return SeverityLevel.MEDIUM
            else:
                return SeverityLevel.LOW
                
        except Exception as e:
            logger.error(f"Error calculating campaign severity: {e}")
            return SeverityLevel.MEDIUM
    
    async def _detect_coordination_methods(
        self,
        campaign_posts: List[Dict[str, Any]]
    ) -> List[CoordinationMethod]:
        """Detect coordination methods used in the campaign.
        
        Args:
            campaign_posts: Posts from the campaign
            
        Returns:
            List of detected coordination methods
        """
        try:
            coordination_methods = []
            
            # Analyze temporal patterns for synchronized posting
            if await self._detect_synchronized_posting(campaign_posts):
                coordination_methods.append(CoordinationMethod.SYNCHRONIZED_POSTING)
            
            # Analyze content amplification patterns
            if await self._detect_content_amplification(campaign_posts):
                coordination_methods.append(CoordinationMethod.CONTENT_AMPLIFICATION)
            
            # Analyze hashtag usage patterns
            if await self._detect_hashtag_hijacking(campaign_posts):
                coordination_methods.append(CoordinationMethod.HASHTAG_HIJACKING)
            
            # Analyze reply patterns
            if await self._detect_reply_flooding(campaign_posts):
                coordination_methods.append(CoordinationMethod.REPLY_FLOODING)
            
            # Analyze network amplification
            if await self._detect_network_amplification(campaign_posts):
                coordination_methods.append(CoordinationMethod.NETWORK_AMPLIFICATION)
            
            return coordination_methods
            
        except Exception as e:
            logger.error(f"Error detecting coordination methods: {e}")
            return []
    
    async def _detect_synchronized_posting(self, campaign_posts: List[Dict[str, Any]]) -> bool:
        """Detect synchronized posting patterns."""
        try:
            if len(campaign_posts) < 3:
                return False
            
            # Extract timestamps
            timestamps = []
            for post in campaign_posts:
                timestamp_str = post.get('timestamp')
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        timestamps.append(timestamp)
                    except ValueError:
                        continue
            
            if len(timestamps) < 3:
                return False
            
            timestamps.sort()
            
            # Check for posts within short time windows
            sync_threshold_minutes = 5
            synchronized_groups = 0
            
            i = 0
            while i < len(timestamps):
                group_size = 1
                j = i + 1
                
                while j < len(timestamps):
                    time_diff = (timestamps[j] - timestamps[i]).total_seconds() / 60
                    if time_diff <= sync_threshold_minutes:
                        group_size += 1
                        j += 1
                    else:
                        break
                
                if group_size >= 3:  # At least 3 posts in sync
                    synchronized_groups += 1
                
                i = j if j > i + 1 else i + 1
            
            return synchronized_groups >= 2  # At least 2 synchronized groups
            
        except Exception as e:
            logger.error(f"Error detecting synchronized posting: {e}")
            return False
    
    async def _detect_content_amplification(self, campaign_posts: List[Dict[str, Any]]) -> bool:
        """Detect content amplification patterns."""
        try:
            if len(campaign_posts) < 5:
                return False
            
            # Check for reposts/retweets
            repost_count = sum(1 for post in campaign_posts if post.get('is_repost', False))
            repost_ratio = repost_count / len(campaign_posts)
            
            # Check for content similarity (near-duplicates)
            contents = [post.get('content', '') for post in campaign_posts]
            if len(contents) < 2:
                return False
            
            embeddings = self.sentence_transformer.encode(contents)
            similarity_matrix = cosine_similarity(embeddings)
            
            # Count high-similarity pairs
            high_similarity_count = 0
            n = len(similarity_matrix)
            for i in range(n):
                for j in range(i + 1, n):
                    if similarity_matrix[i][j] > 0.9:  # Very high similarity
                        high_similarity_count += 1
            
            similarity_ratio = high_similarity_count / (n * (n - 1) / 2) if n > 1 else 0
            
            return repost_ratio > 0.3 or similarity_ratio > 0.4
            
        except Exception as e:
            logger.error(f"Error detecting content amplification: {e}")
            return False
    
    async def _detect_hashtag_hijacking(self, campaign_posts: List[Dict[str, Any]]) -> bool:
        """Detect hashtag hijacking patterns."""
        try:
            # Extract all hashtags
            all_hashtags = []
            for post in campaign_posts:
                hashtags = post.get('hashtags', [])
                all_hashtags.extend(hashtags)
            
            if len(all_hashtags) < 10:
                return False
            
            # Count hashtag frequency
            hashtag_counts = Counter(all_hashtags)
            
            # Check for coordinated hashtag usage
            top_hashtags = hashtag_counts.most_common(5)
            if not top_hashtags:
                return False
            
            # If top hashtags are used by many different users, it might be hijacking
            hashtag_users = defaultdict(set)
            for post in campaign_posts:
                user_id = post.get('user_id')
                hashtags = post.get('hashtags', [])
                for hashtag in hashtags:
                    hashtag_users[hashtag].add(user_id)
            
            # Check if top hashtags are used by multiple users
            coordinated_hashtags = 0
            for hashtag, count in top_hashtags:
                if len(hashtag_users[hashtag]) >= 3 and count >= 5:
                    coordinated_hashtags += 1
            
            return coordinated_hashtags >= 2
            
        except Exception as e:
            logger.error(f"Error detecting hashtag hijacking: {e}")
            return False
    
    async def _detect_reply_flooding(self, campaign_posts: List[Dict[str, Any]]) -> bool:
        """Detect reply flooding patterns."""
        try:
            # Count replies to specific posts
            reply_targets = defaultdict(int)
            for post in campaign_posts:
                parent_post_id = post.get('parent_post_id')
                if parent_post_id:
                    reply_targets[parent_post_id] += 1
            
            if not reply_targets:
                return False
            
            # Check for posts with many replies from campaign participants
            max_replies = max(reply_targets.values())
            high_reply_targets = sum(1 for count in reply_targets.values() if count >= 5)
            
            return max_replies >= 10 or high_reply_targets >= 3
            
        except Exception as e:
            logger.error(f"Error detecting reply flooding: {e}")
            return False
    
    async def _detect_network_amplification(self, campaign_posts: List[Dict[str, Any]]) -> bool:
        """Detect network amplification patterns."""
        try:
            # Check for mentions and interactions
            user_mentions = defaultdict(int)
            for post in campaign_posts:
                mentions = post.get('mentions', [])
                for mention in mentions:
                    user_mentions[mention] += 1
            
            # Check for cross-promotion patterns
            campaign_users = set(post.get('user_id') for post in campaign_posts)
            internal_mentions = 0
            
            for post in campaign_posts:
                mentions = post.get('mentions', [])
                for mention in mentions:
                    if mention in campaign_users:
                        internal_mentions += 1
            
            internal_mention_ratio = internal_mentions / len(campaign_posts) if campaign_posts else 0
            
            return internal_mention_ratio > 0.2  # High internal cross-promotion
            
        except Exception as e:
            logger.error(f"Error detecting network amplification: {e}")
            return False
    
    async def _calculate_network_metrics(self, network_graph: nx.Graph) -> Dict[str, Any]:
        """Calculate comprehensive network metrics.
        
        Args:
            network_graph: NetworkX graph
            
        Returns:
            Dictionary of network metrics
        """
        try:
            if len(network_graph.nodes()) == 0:
                return {}
            
            metrics = {}
            
            # Basic metrics
            metrics['node_count'] = len(network_graph.nodes())
            metrics['edge_count'] = len(network_graph.edges())
            metrics['density'] = nx.density(network_graph)
            
            # Connectivity metrics
            metrics['is_connected'] = nx.is_connected(network_graph)
            if nx.is_connected(network_graph):
                metrics['diameter'] = nx.diameter(network_graph)
                metrics['average_path_length'] = nx.average_shortest_path_length(network_graph)
            else:
                # For disconnected graphs, calculate for largest component
                largest_cc = max(nx.connected_components(network_graph), key=len)
                subgraph = network_graph.subgraph(largest_cc)
                if len(subgraph.nodes()) > 1:
                    metrics['diameter'] = nx.diameter(subgraph)
                    metrics['average_path_length'] = nx.average_shortest_path_length(subgraph)
            
            # Clustering metrics
            metrics['average_clustering'] = nx.average_clustering(network_graph)
            metrics['transitivity'] = nx.transitivity(network_graph)
            
            # Centrality metrics
            degree_centrality = nx.degree_centrality(network_graph)
            betweenness_centrality = nx.betweenness_centrality(network_graph)
            closeness_centrality = nx.closeness_centrality(network_graph)
            
            metrics['max_degree_centrality'] = max(degree_centrality.values()) if degree_centrality else 0
            metrics['max_betweenness_centrality'] = max(betweenness_centrality.values()) if betweenness_centrality else 0
            metrics['max_closeness_centrality'] = max(closeness_centrality.values()) if closeness_centrality else 0
            
            # Identify key nodes
            if degree_centrality:
                top_degree_nodes = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
                metrics['top_degree_nodes'] = [node for node, centrality in top_degree_nodes]
            
            if betweenness_centrality:
                top_betweenness_nodes = sorted(betweenness_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
                metrics['top_betweenness_nodes'] = [node for node, centrality in top_betweenness_nodes]
            
            # Community detection
            try:
                communities = list(nx.community.greedy_modularity_communities(network_graph))
                metrics['community_count'] = len(communities)
                metrics['modularity'] = nx.community.modularity(network_graph, communities)
                metrics['largest_community_size'] = max(len(community) for community in communities) if communities else 0
            except:
                metrics['community_count'] = 0
                metrics['modularity'] = 0
                metrics['largest_community_size'] = 0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating network metrics: {e}")
            return {}
    
    async def generate_campaign_report(
        self,
        campaign_data: Dict[str, Any],
        posts_data: List[Dict[str, Any]],
        network_graph: nx.Graph
    ) -> Dict[str, Any]:
        """Generate comprehensive campaign analysis report.
        
        Args:
            campaign_data: Campaign information
            posts_data: Related posts data
            network_graph: Network graph of participants
            
        Returns:
            Comprehensive campaign report
        """
        try:
            report = {
                'campaign_id': campaign_data.get('campaign_id'),
                'campaign_name': campaign_data.get('name'),
                'detection_timestamp': datetime.utcnow().isoformat(),
                'analysis_summary': {},
                'network_analysis': {},
                'content_analysis': {},
                'temporal_analysis': {},
                'evidence': {},
                'recommendations': []
            }
            
            # Analysis summary
            report['analysis_summary'] = {
                'coordination_score': campaign_data.get('coordination_score', 0.0),
                'participant_count': campaign_data.get('participant_count', 0),
                'content_count': len(posts_data),
                'campaign_type': campaign_data.get('campaign_type'),
                'severity': campaign_data.get('severity'),
                'coordination_methods': campaign_data.get('coordination_methods', [])
            }
            
            # Network analysis
            network_metrics = await self._calculate_network_metrics(network_graph)
            report['network_analysis'] = {
                'network_metrics': network_metrics,
                'key_participants': network_metrics.get('top_degree_nodes', []),
                'network_structure': {
                    'density': network_metrics.get('density', 0),
                    'clustering': network_metrics.get('average_clustering', 0),
                    'connectivity': network_metrics.get('is_connected', False)
                }
            }
            
            # Content analysis
            content_similarity = await self._analyze_content_similarity(posts_data)
            report['content_analysis'] = {
                'content_similarity_score': content_similarity,
                'unique_content_ratio': await self._calculate_unique_content_ratio(posts_data),
                'common_themes': await self._extract_common_themes(posts_data),
                'hashtag_analysis': await self._analyze_hashtag_patterns(posts_data)
            }
            
            # Temporal analysis
            temporal_coordination = await self._analyze_temporal_coordination(posts_data)
            report['temporal_analysis'] = {
                'temporal_coordination_score': temporal_coordination,
                'activity_bursts': await self._identify_activity_bursts(posts_data),
                'posting_patterns': await self._analyze_posting_patterns(posts_data)
            }
            
            # Evidence collection
            report['evidence'] = {
                'sample_coordinated_content': await self._collect_evidence_samples(posts_data),
                'network_visualization_data': await self._prepare_network_visualization_data(network_graph),
                'timeline_data': await self._prepare_timeline_data(posts_data)
            }
            
            # Generate recommendations
            report['recommendations'] = await self._generate_recommendations(campaign_data, report)
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating campaign report: {e}")
            return {}
    
    async def _calculate_unique_content_ratio(self, posts_data: List[Dict[str, Any]]) -> float:
        """Calculate ratio of unique content."""
        try:
            if not posts_data:
                return 0.0
            
            contents = [post.get('content', '') for post in posts_data]
            unique_contents = set(contents)
            
            return len(unique_contents) / len(contents)
            
        except Exception as e:
            logger.error(f"Error calculating unique content ratio: {e}")
            return 0.0
    
    async def _extract_common_themes(self, posts_data: List[Dict[str, Any]]) -> List[str]:
        """Extract common themes from campaign content."""
        try:
            # Simple keyword extraction - in production, use more sophisticated NLP
            all_content = ' '.join(post.get('content', '') for post in posts_data).lower()
            
            # Common political/social keywords
            theme_keywords = [
                'india', 'pakistan', 'china', 'government', 'election', 'democracy',
                'security', 'military', 'economy', 'corruption', 'protest', 'policy'
            ]
            
            found_themes = []
            for keyword in theme_keywords:
                if keyword in all_content and all_content.count(keyword) >= 3:
                    found_themes.append(keyword)
            
            return found_themes[:10]  # Return top 10 themes
            
        except Exception as e:
            logger.error(f"Error extracting common themes: {e}")
            return []
    
    async def _analyze_hashtag_patterns(self, posts_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze hashtag usage patterns."""
        try:
            all_hashtags = []
            for post in posts_data:
                hashtags = post.get('hashtags', [])
                all_hashtags.extend(hashtags)
            
            if not all_hashtags:
                return {}
            
            hashtag_counts = Counter(all_hashtags)
            
            return {
                'total_hashtags': len(all_hashtags),
                'unique_hashtags': len(set(all_hashtags)),
                'top_hashtags': dict(hashtag_counts.most_common(10)),
                'hashtag_diversity': len(set(all_hashtags)) / len(all_hashtags) if all_hashtags else 0
            }
            
        except Exception as e:
            logger.error(f"Error analyzing hashtag patterns: {e}")
            return {}
    
    async def _identify_activity_bursts(self, posts_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify activity bursts in the campaign."""
        try:
            # Extract timestamps
            timestamps = []
            for post in posts_data:
                timestamp_str = post.get('timestamp')
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        timestamps.append(timestamp)
                    except ValueError:
                        continue
            
            if len(timestamps) < 5:
                return []
            
            timestamps.sort()
            
            # Group posts by hour
            hourly_counts = defaultdict(int)
            for timestamp in timestamps:
                hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
                hourly_counts[hour_key] += 1
            
            # Identify bursts (hours with significantly more activity)
            counts = list(hourly_counts.values())
            if not counts:
                return []
            
            avg_count = np.mean(counts)
            std_count = np.std(counts)
            burst_threshold = avg_count + 2 * std_count  # 2 standard deviations above mean
            
            bursts = []
            for hour, count in hourly_counts.items():
                if count > burst_threshold:
                    bursts.append({
                        'timestamp': hour.isoformat(),
                        'post_count': count,
                        'intensity': count / avg_count if avg_count > 0 else 0
                    })
            
            return sorted(bursts, key=lambda x: x['intensity'], reverse=True)[:10]
            
        except Exception as e:
            logger.error(f"Error identifying activity bursts: {e}")
            return []
    
    async def _analyze_posting_patterns(self, posts_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze posting patterns."""
        try:
            # Extract timestamps
            timestamps = []
            for post in posts_data:
                timestamp_str = post.get('timestamp')
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        timestamps.append(timestamp)
                    except ValueError:
                        continue
            
            if not timestamps:
                return {}
            
            timestamps.sort()
            
            # Analyze by hour of day
            hour_counts = defaultdict(int)
            for timestamp in timestamps:
                hour_counts[timestamp.hour] += 1
            
            # Analyze by day of week
            day_counts = defaultdict(int)
            for timestamp in timestamps:
                day_counts[timestamp.weekday()] += 1
            
            return {
                'total_posts': len(timestamps),
                'time_span_hours': (timestamps[-1] - timestamps[0]).total_seconds() / 3600 if len(timestamps) > 1 else 0,
                'posts_per_hour': len(timestamps) / ((timestamps[-1] - timestamps[0]).total_seconds() / 3600) if len(timestamps) > 1 else 0,
                'peak_hour': max(hour_counts, key=hour_counts.get) if hour_counts else 0,
                'peak_day': max(day_counts, key=day_counts.get) if day_counts else 0,
                'hourly_distribution': dict(hour_counts),
                'daily_distribution': dict(day_counts)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing posting patterns: {e}")
            return {}
    
    async def _collect_evidence_samples(self, posts_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Collect evidence samples for the report."""
        try:
            evidence_samples = []
            
            # Sample of coordinated content (high similarity)
            if len(posts_data) >= 2:
                contents = [post.get('content', '') for post in posts_data]
                embeddings = self.sentence_transformer.encode(contents)
                similarity_matrix = cosine_similarity(embeddings)
                
                # Find pairs with high similarity
                high_similarity_pairs = []
                n = len(similarity_matrix)
                for i in range(n):
                    for j in range(i + 1, n):
                        if similarity_matrix[i][j] > 0.8:
                            high_similarity_pairs.append((i, j, similarity_matrix[i][j]))
                
                # Sort by similarity and take top samples
                high_similarity_pairs.sort(key=lambda x: x[2], reverse=True)
                
                for i, j, similarity in high_similarity_pairs[:5]:
                    evidence_samples.append({
                        'type': 'coordinated_content',
                        'similarity_score': float(similarity),
                        'post1': {
                            'user_id': posts_data[i].get('user_id'),
                            'content': posts_data[i].get('content', '')[:200] + '...' if len(posts_data[i].get('content', '')) > 200 else posts_data[i].get('content', ''),
                            'timestamp': posts_data[i].get('timestamp')
                        },
                        'post2': {
                            'user_id': posts_data[j].get('user_id'),
                            'content': posts_data[j].get('content', '')[:200] + '...' if len(posts_data[j].get('content', '')) > 200 else posts_data[j].get('content', ''),
                            'timestamp': posts_data[j].get('timestamp')
                        }
                    })
            
            return evidence_samples
            
        except Exception as e:
            logger.error(f"Error collecting evidence samples: {e}")
            return []
    
    async def _prepare_network_visualization_data(self, network_graph: nx.Graph) -> Dict[str, Any]:
        """Prepare data for network visualization."""
        try:
            if len(network_graph.nodes()) == 0:
                return {}
            
            # Prepare nodes data
            nodes = []
            degree_centrality = nx.degree_centrality(network_graph)
            
            for node in network_graph.nodes():
                nodes.append({
                    'id': str(node),
                    'label': str(node),
                    'degree': network_graph.degree(node),
                    'centrality': degree_centrality.get(node, 0),
                    'size': max(5, degree_centrality.get(node, 0) * 50)  # Scale for visualization
                })
            
            # Prepare edges data
            edges = []
            for edge in network_graph.edges(data=True):
                edges.append({
                    'source': str(edge[0]),
                    'target': str(edge[1]),
                    'weight': edge[2].get('weight', 1.0)
                })
            
            return {
                'nodes': nodes,
                'edges': edges,
                'node_count': len(nodes),
                'edge_count': len(edges)
            }
            
        except Exception as e:
            logger.error(f"Error preparing network visualization data: {e}")
            return {}
    
    async def _prepare_timeline_data(self, posts_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare timeline data for visualization."""
        try:
            timeline_data = []
            
            for post in posts_data:
                timestamp_str = post.get('timestamp')
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        timeline_data.append({
                            'timestamp': timestamp.isoformat(),
                            'user_id': post.get('user_id'),
                            'content_preview': post.get('content', '')[:100] + '...' if len(post.get('content', '')) > 100 else post.get('content', ''),
                            'platform': post.get('platform'),
                            'metrics': post.get('metrics', {})
                        })
                    except ValueError:
                        continue
            
            # Sort by timestamp
            timeline_data.sort(key=lambda x: x['timestamp'])
            
            return timeline_data
            
        except Exception as e:
            logger.error(f"Error preparing timeline data: {e}")
            return []
    
    async def _generate_recommendations(
        self,
        campaign_data: Dict[str, Any],
        report: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on campaign analysis."""
        try:
            recommendations = []
            
            coordination_score = campaign_data.get('coordination_score', 0.0)
            severity = campaign_data.get('severity', 'low')
            
            # High coordination score recommendations
            if coordination_score > 0.8:
                recommendations.append("High coordination detected - recommend immediate investigation and monitoring")
                recommendations.append("Consider implementing targeted content moderation measures")
            
            # Severity-based recommendations
            if severity in ['high', 'critical']:
                recommendations.append("High severity campaign - escalate to senior analysts")
                recommendations.append("Implement enhanced monitoring for related accounts and content")
            
            # Network-based recommendations
            network_metrics = report.get('network_analysis', {}).get('network_metrics', {})
            if network_metrics.get('density', 0) > 0.7:
                recommendations.append("Dense network structure suggests organized coordination - investigate funding sources")
            
            # Content-based recommendations
            content_analysis = report.get('content_analysis', {})
            if content_analysis.get('unique_content_ratio', 1.0) < 0.3:
                recommendations.append("Low content diversity indicates automated or scripted behavior")
            
            # Temporal-based recommendations
            temporal_analysis = report.get('temporal_analysis', {})
            if temporal_analysis.get('temporal_coordination_score', 0) > 0.7:
                recommendations.append("Strong temporal coordination suggests centralized control")
            
            # Default recommendations
            if not recommendations:
                recommendations.append("Continue monitoring for evolving patterns")
                recommendations.append("Document findings for future reference")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return ["Error generating recommendations - manual review required"]
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the campaign detector.
        
        Returns:
            Dictionary containing performance metrics
        """
        try:
            avg_processing_time = (
                self.total_processing_time / self.total_analyses
                if self.total_analyses > 0 else 0.0
            )
            
            return {
                'total_analyses': self.total_analyses,
                'total_processing_time_ms': self.total_processing_time,
                'average_processing_time_ms': avg_processing_time,
                'model_version': self.model_version,
                'sentence_transformer_model': getattr(self.sentence_transformer, 'model_name', 'unknown') if self.sentence_transformer else None
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}
            methods = []
            
            # Check for synchronized posting
            timestamps = []
            for post in campaign_posts:
                timestamp_str = post.get('timestamp')
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        timestamps.append(timestamp)
                    except ValueError:
                        continue
            
            if len(timestamps) >= 2:
                timestamps.sort()
                time_diffs = [
                    (timestamps[i] - timestamps[i-1]).total_seconds() / 60
                    for i in range(1, len(timestamps))
                ]
                
                synchronized_count = sum(1 for diff in time_diffs if diff <= 5)  # 5 minutes
                if synchronized_count / len(time_diffs) > 0.3:
                    methods.append(CoordinationMethod.SYNCHRONIZED_POSTING)
            
            # Check for content amplification
            contents = [post.get('content', '') for post in campaign_posts]
            unique_contents = set(contents)
            if len(unique_contents) < len(contents) * 0.5:
                methods.append(CoordinationMethod.CONTENT_AMPLIFICATION)
            
            # Check for hashtag patterns
            all_hashtags = []
            for post in campaign_posts:
                hashtags = post.get('hashtags', [])
                all_hashtags.extend(hashtags)
            
            if all_hashtags:
                hashtag_counts = Counter(all_hashtags)
                most_common = hashtag_counts.most_common(1)[0]
                if most_common[1] > len(campaign_posts) * 0.7:
                    methods.append(CoordinationMethod.HASHTAG_HIJACKING)
            
            # Check for network amplification (simplified)
            user_ids = [post.get('user_id') for post in campaign_posts]
            unique_users = set(user_ids)
            if len(unique_users) >= 10:  # Multiple users coordinating
                methods.append(CoordinationMethod.NETWORK_AMPLIFICATION)
            
            return methods
            
        except Exception as e:
            logger.error(f"Error detecting coordination methods: {e}")
            return []
    
    async def _calculate_network_metrics(self, network_graph: nx.Graph) -> Dict[str, Any]:
        """Calculate network analysis metrics.
        
        Args:
            network_graph: Network graph
            
        Returns:
            Dictionary of network metrics
        """
        try:
            if len(network_graph.nodes()) == 0:
                return {}
            
            metrics = {
                'total_nodes': len(network_graph.nodes()),
                'total_edges': len(network_graph.edges()),
                'density': nx.density(network_graph),
                'is_connected': nx.is_connected(network_graph),
                'number_of_components': nx.number_connected_components(network_graph)
            }
            
            if len(network_graph.nodes()) > 1:
                metrics['average_clustering'] = nx.average_clustering(network_graph)
                
                if nx.is_connected(network_graph):
                    metrics['average_path_length'] = nx.average_shortest_path_length(network_graph)
                    metrics['diameter'] = nx.diameter(network_graph)
            
            # Calculate centrality measures for top nodes
            if len(network_graph.nodes()) > 0:
                degree_centrality = nx.degree_centrality(network_graph)
                top_nodes = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
                metrics['top_central_nodes'] = [{'node': node, 'centrality': centrality} 
                                              for node, centrality in top_nodes]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating network metrics: {e}")
            return {}
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information and performance metrics.
        
        Returns:
            Dictionary with model information
        """
        avg_processing_time = (
            self.total_processing_time / self.total_analyses
            if self.total_analyses > 0 else 0.0
        )
        
        return {
            "model_version": self.model_version,
            "sentence_transformer_model": "all-MiniLM-L6-v2",
            "total_analyses": self.total_analyses,
            "average_processing_time_ms": avg_processing_time,
            "min_coordination_score": self.min_coordination_score,
            "min_participants": self.min_participants,
            "content_similarity_threshold": self.content_similarity_threshold,
            "temporal_window_minutes": self.temporal_window_minutes
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the campaign detector.
        
        Returns:
            Health check results
        """
        try:
            # Test with sample data
            test_posts = [
                {
                    'post_id': 'test1',
                    'user_id': 'user1',
                    'content': 'Test content for health check',
                    'timestamp': datetime.utcnow().isoformat()
                },
                {
                    'post_id': 'test2',
                    'user_id': 'user2',
                    'content': 'Another test content',
                    'timestamp': datetime.utcnow().isoformat()
                }
            ]
            
            result = await self.detect_campaigns(test_posts)
            
            return {
                "status": "healthy",
                "sentence_transformer_loaded": self.sentence_transformer is not None,
                "test_detection_successful": result is not None,
                "campaign_classifiers_count": len(self.campaign_classifiers)
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "sentence_transformer_loaded": self.sentence_transformer is not None
            }