"""
Enhanced tests for campaign detection engine.
Tests the new functionality for content similarity, temporal clustering, 
network visualization, and comprehensive reporting.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.analysis.campaign_detector import CampaignDetector
from project_dharma.shared.models.campaign import CampaignType, CoordinationMethod, SeverityLevel


class TestCampaignDetectorEnhanced:
    """Test enhanced campaign detection functionality."""
    
    @pytest.fixture
    async def detector(self):
        """Create and initialize campaign detector."""
        detector = CampaignDetector()
        await detector.initialize()
        return detector
    
    @pytest.fixture
    def sample_coordinated_posts(self):
        """Sample posts showing coordinated behavior."""
        base_time = datetime.utcnow()
        
        return [
            {
                'post_id': 'post_1',
                'user_id': 'user_1',
                'content': 'This is a coordinated message about India policy',
                'timestamp': base_time.isoformat(),
                'platform': 'twitter',
                'hashtags': ['IndiaPolicy', 'Coordination'],
                'metrics': {'likes': 10, 'shares': 5, 'comments': 2}
            },
            {
                'post_id': 'post_2',
                'user_id': 'user_2',
                'content': 'This is a coordinated message about India policy',
                'timestamp': (base_time + timedelta(minutes=2)).isoformat(),
                'platform': 'twitter',
                'hashtags': ['IndiaPolicy', 'Coordination'],
                'metrics': {'likes': 8, 'shares': 4, 'comments': 1}
            },
            {
                'post_id': 'post_3',
                'user_id': 'user_3',
                'content': 'This is a similar coordinated message about India policy',
                'timestamp': (base_time + timedelta(minutes=3)).isoformat(),
                'platform': 'twitter',
                'hashtags': ['IndiaPolicy', 'Coordination'],
                'metrics': {'likes': 12, 'shares': 6, 'comments': 3}
            },
            {
                'post_id': 'post_4',
                'user_id': 'user_4',
                'content': 'Another coordinated message about India policy',
                'timestamp': (base_time + timedelta(minutes=5)).isoformat(),
                'platform': 'twitter',
                'hashtags': ['IndiaPolicy'],
                'metrics': {'likes': 15, 'shares': 8, 'comments': 4}
            },
            {
                'post_id': 'post_5',
                'user_id': 'user_5',
                'content': 'Yet another coordinated message about India policy',
                'timestamp': (base_time + timedelta(minutes=7)).isoformat(),
                'platform': 'twitter',
                'hashtags': ['IndiaPolicy', 'Coordination'],
                'metrics': {'likes': 9, 'shares': 3, 'comments': 2}
            }
        ]
    
    @pytest.fixture
    def sample_network_posts(self):
        """Sample posts for network analysis."""
        base_time = datetime.utcnow()
        
        return [
            {
                'post_id': 'net_1',
                'user_id': 'user_a',
                'content': 'Network message from user A',
                'timestamp': base_time.isoformat(),
                'mentions': ['user_b', 'user_c'],
                'hashtags': ['Network']
            },
            {
                'post_id': 'net_2',
                'user_id': 'user_b',
                'content': 'Network message from user B',
                'timestamp': (base_time + timedelta(minutes=1)).isoformat(),
                'mentions': ['user_a', 'user_c'],
                'hashtags': ['Network']
            },
            {
                'post_id': 'net_3',
                'user_id': 'user_c',
                'content': 'Network message from user C',
                'timestamp': (base_time + timedelta(minutes=2)).isoformat(),
                'mentions': ['user_a', 'user_b'],
                'hashtags': ['Network']
            },
            {
                'post_id': 'net_4',
                'user_id': 'user_d',
                'content': 'Isolated message from user D',
                'timestamp': (base_time + timedelta(minutes=10)).isoformat(),
                'hashtags': ['Isolated']
            }
        ]
    
    @pytest.mark.asyncio
    async def test_content_similarity_analysis(self, detector, sample_coordinated_posts):
        """Test content similarity analysis using sentence transformers."""
        similarity_score = await detector._analyze_content_similarity(sample_coordinated_posts)
        
        # Should detect high similarity in coordinated posts
        assert similarity_score > 0.7, f"Expected high similarity, got {similarity_score}"
        
        # Test with diverse content
        diverse_posts = [
            {'content': 'Completely different topic about sports'},
            {'content': 'Another topic about weather'},
            {'content': 'Third topic about technology'}
        ]
        
        diverse_similarity = await detector._analyze_content_similarity(diverse_posts)
        assert diverse_similarity < 0.5, f"Expected low similarity for diverse content, got {diverse_similarity}"
    
    @pytest.mark.asyncio
    async def test_temporal_coordination_analysis(self, detector, sample_coordinated_posts):
        """Test temporal coordination analysis."""
        temporal_score = await detector._analyze_temporal_coordination(sample_coordinated_posts)
        
        # Should detect temporal coordination in synchronized posts
        assert temporal_score > 0.5, f"Expected temporal coordination, got {temporal_score}"
        
        # Test with scattered timestamps
        scattered_posts = []
        base_time = datetime.utcnow()
        for i in range(5):
            scattered_posts.append({
                'content': f'Message {i}',
                'timestamp': (base_time + timedelta(hours=i*6)).isoformat()
            })
        
        scattered_score = await detector._analyze_temporal_coordination(scattered_posts)
        assert scattered_score < 0.3, f"Expected low temporal coordination for scattered posts, got {scattered_score}"
    
    @pytest.mark.asyncio
    async def test_network_graph_building(self, detector, sample_network_posts):
        """Test network graph construction."""
        network_graph = await detector._build_interaction_network(sample_network_posts)
        
        # Should have nodes for all users
        assert len(network_graph.nodes()) == 4
        
        # Should have edges between connected users
        assert len(network_graph.edges()) > 0
        
        # Check specific connections
        assert network_graph.has_node('user_a')
        assert network_graph.has_node('user_b')
        assert network_graph.has_node('user_c')
        assert network_graph.has_node('user_d')
    
    @pytest.mark.asyncio
    async def test_coordination_methods_detection(self, detector, sample_coordinated_posts):
        """Test detection of coordination methods."""
        methods = await detector._detect_coordination_methods(sample_coordinated_posts)
        
        # Should detect synchronized posting
        assert CoordinationMethod.SYNCHRONIZED_POSTING in methods
        
        # Should detect hashtag coordination
        assert CoordinationMethod.HASHTAG_HIJACKING in methods
    
    @pytest.mark.asyncio
    async def test_synchronized_posting_detection(self, detector):
        """Test synchronized posting detection."""
        base_time = datetime.utcnow()
        
        # Create synchronized posts (within 5 minutes)
        sync_posts = []
        for i in range(5):
            sync_posts.append({
                'user_id': f'user_{i}',
                'content': f'Synchronized message {i}',
                'timestamp': (base_time + timedelta(minutes=i)).isoformat()
            })
        
        is_synchronized = await detector._detect_synchronized_posting(sync_posts)
        assert is_synchronized, "Should detect synchronized posting"
        
        # Test non-synchronized posts
        async_posts = []
        for i in range(5):
            async_posts.append({
                'user_id': f'user_{i}',
                'content': f'Async message {i}',
                'timestamp': (base_time + timedelta(hours=i*2)).isoformat()
            })
        
        is_not_synchronized = await detector._detect_synchronized_posting(async_posts)
        assert not is_not_synchronized, "Should not detect synchronized posting for async posts"
    
    @pytest.mark.asyncio
    async def test_content_amplification_detection(self, detector):
        """Test content amplification detection."""
        # Create posts with high repost ratio
        amplified_posts = []
        for i in range(10):
            amplified_posts.append({
                'user_id': f'user_{i}',
                'content': 'Original message to be amplified',
                'is_repost': i > 2,  # 70% are reposts
                'original_post_id': 'original_1' if i > 2 else None
            })
        
        is_amplified = await detector._detect_content_amplification(amplified_posts)
        assert is_amplified, "Should detect content amplification"
    
    @pytest.mark.asyncio
    async def test_network_metrics_calculation(self, detector, sample_network_posts):
        """Test comprehensive network metrics calculation."""
        network_graph = await detector._build_interaction_network(sample_network_posts)
        metrics = await detector._calculate_network_metrics(network_graph)
        
        # Should have basic metrics
        assert 'node_count' in metrics
        assert 'edge_count' in metrics
        assert 'density' in metrics
        assert 'average_clustering' in metrics
        
        # Should have centrality metrics
        assert 'max_degree_centrality' in metrics
        assert 'max_betweenness_centrality' in metrics
        
        # Should have community metrics
        assert 'community_count' in metrics
        assert 'modularity' in metrics
        
        # Validate metric ranges
        assert 0 <= metrics['density'] <= 1
        assert 0 <= metrics['average_clustering'] <= 1
        assert -1 <= metrics['modularity'] <= 1
    
    @pytest.mark.asyncio
    async def test_campaign_report_generation(self, detector, sample_coordinated_posts):
        """Test comprehensive campaign report generation."""
        # First detect a campaign
        detection_result = await detector.detect_campaigns(sample_coordinated_posts)
        
        if detection_result.campaigns_detected > 0:
            # Create sample campaign data
            campaign_data = {
                'campaign_id': 'test_campaign_001',
                'name': 'Test Coordinated Campaign',
                'coordination_score': detection_result.coordination_score,
                'participant_count': detection_result.participant_count,
                'campaign_type': CampaignType.DISINFORMATION,
                'severity': SeverityLevel.HIGH,
                'coordination_methods': [CoordinationMethod.SYNCHRONIZED_POSTING]
            }
            
            # Build network graph
            network_graph = await detector._build_interaction_network(sample_coordinated_posts)
            
            # Generate report
            report = await detector.generate_campaign_report(
                campaign_data, sample_coordinated_posts, network_graph
            )
            
            # Validate report structure
            assert 'campaign_id' in report
            assert 'analysis_summary' in report
            assert 'network_analysis' in report
            assert 'content_analysis' in report
            assert 'temporal_analysis' in report
            assert 'evidence' in report
            assert 'recommendations' in report
            
            # Validate analysis summary
            summary = report['analysis_summary']
            assert summary['coordination_score'] > 0
            assert summary['participant_count'] > 0
            assert summary['content_count'] > 0
            
            # Validate network analysis
            network_analysis = report['network_analysis']
            assert 'network_metrics' in network_analysis
            assert 'key_participants' in network_analysis
            
            # Validate content analysis
            content_analysis = report['content_analysis']
            assert 'content_similarity_score' in content_analysis
            assert 'unique_content_ratio' in content_analysis
            
            # Validate evidence
            evidence = report['evidence']
            assert 'sample_coordinated_content' in evidence
            assert 'network_visualization_data' in evidence
            assert 'timeline_data' in evidence
            
            # Validate recommendations
            assert isinstance(report['recommendations'], list)
            assert len(report['recommendations']) > 0
    
    @pytest.mark.asyncio
    async def test_activity_burst_identification(self, detector):
        """Test identification of activity bursts."""
        base_time = datetime.utcnow()
        
        # Create posts with activity bursts
        burst_posts = []
        
        # Normal activity (1 post per hour)
        for i in range(5):
            burst_posts.append({
                'user_id': f'user_{i}',
                'content': f'Normal message {i}',
                'timestamp': (base_time + timedelta(hours=i)).isoformat()
            })
        
        # Activity burst (10 posts in one hour)
        burst_hour = base_time + timedelta(hours=6)
        for i in range(10):
            burst_posts.append({
                'user_id': f'burst_user_{i}',
                'content': f'Burst message {i}',
                'timestamp': (burst_hour + timedelta(minutes=i*5)).isoformat()
            })
        
        bursts = await detector._identify_activity_bursts(burst_posts)
        
        # Should identify the burst hour
        assert len(bursts) > 0
        assert bursts[0]['post_count'] >= 10
        assert bursts[0]['intensity'] > 1.0
    
    @pytest.mark.asyncio
    async def test_evidence_collection(self, detector, sample_coordinated_posts):
        """Test evidence sample collection."""
        evidence_samples = await detector._collect_evidence_samples(sample_coordinated_posts)
        
        # Should collect coordinated content samples
        assert len(evidence_samples) > 0
        
        for sample in evidence_samples:
            assert sample['type'] == 'coordinated_content'
            assert 'similarity_score' in sample
            assert 'post1' in sample
            assert 'post2' in sample
            assert sample['similarity_score'] > 0.7  # High similarity threshold
    
    @pytest.mark.asyncio
    async def test_network_visualization_data(self, detector, sample_network_posts):
        """Test network visualization data preparation."""
        network_graph = await detector._build_interaction_network(sample_network_posts)
        viz_data = await detector._prepare_network_visualization_data(network_graph)
        
        # Should have nodes and edges
        assert 'nodes' in viz_data
        assert 'edges' in viz_data
        assert 'node_count' in viz_data
        assert 'edge_count' in viz_data
        
        # Validate node structure
        if viz_data['nodes']:
            node = viz_data['nodes'][0]
            assert 'id' in node
            assert 'label' in node
            assert 'degree' in node
            assert 'centrality' in node
            assert 'size' in node
        
        # Validate edge structure
        if viz_data['edges']:
            edge = viz_data['edges'][0]
            assert 'source' in edge
            assert 'target' in edge
            assert 'weight' in edge
    
    @pytest.mark.asyncio
    async def test_timeline_data_preparation(self, detector, sample_coordinated_posts):
        """Test timeline data preparation."""
        timeline_data = await detector._prepare_timeline_data(sample_coordinated_posts)
        
        # Should have timeline entries
        assert len(timeline_data) > 0
        
        # Should be sorted by timestamp
        timestamps = [entry['timestamp'] for entry in timeline_data]
        assert timestamps == sorted(timestamps)
        
        # Validate timeline entry structure
        entry = timeline_data[0]
        assert 'timestamp' in entry
        assert 'user_id' in entry
        assert 'content_preview' in entry
        assert 'platform' in entry
        assert 'metrics' in entry
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, detector, sample_coordinated_posts):
        """Test performance metrics tracking."""
        # Run some analyses to generate metrics
        await detector.detect_campaigns(sample_coordinated_posts)
        await detector.detect_campaigns(sample_coordinated_posts[:3])
        
        metrics = await detector.get_performance_metrics()
        
        # Should have performance data
        assert 'total_analyses' in metrics
        assert 'total_processing_time_ms' in metrics
        assert 'average_processing_time_ms' in metrics
        assert 'model_version' in metrics
        
        # Should have processed at least 2 analyses
        assert metrics['total_analyses'] >= 2
        assert metrics['total_processing_time_ms'] > 0
        assert metrics['average_processing_time_ms'] > 0
    
    @pytest.mark.asyncio
    async def test_full_campaign_detection_pipeline(self, detector, sample_coordinated_posts):
        """Test the complete campaign detection pipeline."""
        # Run full detection
        result = await detector.detect_campaigns(
            sample_coordinated_posts,
            time_window_hours=24.0,
            min_coordination_score=0.5
        )
        
        # Should detect coordination
        assert result.coordination_score > 0.5
        assert result.participant_count >= 3
        assert result.content_similarity_score > 0.7
        assert result.temporal_coordination_score > 0.3
        assert result.processing_time_ms > 0
        
        # Should detect at least one campaign
        assert result.campaigns_detected >= 1
        assert len(result.campaign_ids) >= 1
        
        # Should have network metrics
        assert result.network_metrics is not None
        assert len(result.network_metrics) > 0


if __name__ == "__main__":
    # Run a simple test
    async def run_simple_test():
        detector = CampaignDetector()
        await detector.initialize()
        
        # Test with sample data
        sample_posts = [
            {
                'post_id': 'test_1',
                'user_id': 'user_1',
                'content': 'Test coordinated message',
                'timestamp': datetime.utcnow().isoformat(),
                'platform': 'twitter'
            },
            {
                'post_id': 'test_2',
                'user_id': 'user_2',
                'content': 'Test coordinated message',
                'timestamp': (datetime.utcnow() + timedelta(minutes=1)).isoformat(),
                'platform': 'twitter'
            }
        ]
        
        result = await detector.detect_campaigns(sample_posts)
        print(f"Detection result: {result}")
        
        if result.campaigns_detected > 0:
            print("Campaign detected successfully!")
        else:
            print("No campaigns detected")
    
    # Run the test
    asyncio.run(run_simple_test())