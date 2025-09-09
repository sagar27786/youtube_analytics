#!/usr/bin/env python3
"""
Unit tests for database models and operations
"""

import pytest
import tempfile
import os
from datetime import datetime, date
from unittest.mock import Mock, patch
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import (
    Base, Video, VideoMetrics, ChannelMetrics, Insight, APIQuota,
    DatabaseManager, get_db_session
)
from src.utils.config import Config

class TestDatabaseModels:
    """Test cases for database models."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary in-memory database for testing."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        yield session
        
        session.close()
    
    def test_video_model_creation(self, temp_db):
        """Test Video model creation and basic operations."""
        video = Video(
            video_id="test_video_123",
            channel_id="test_channel_456",
            title="Test Video Title",
            description="Test video description",
            published_at=datetime(2024, 1, 1, 12, 0, 0),
            thumbnail_url="https://example.com/thumb.jpg",
            duration=300,
            tags=["test", "video"]
        )
        
        temp_db.add(video)
        temp_db.commit()
        
        # Retrieve and verify
        retrieved_video = temp_db.query(Video).filter_by(video_id="test_video_123").first()
        
        assert retrieved_video is not None
        assert retrieved_video.video_id == "test_video_123"
        assert retrieved_video.channel_id == "test_channel_456"
        assert retrieved_video.title == "Test Video Title"
        assert retrieved_video.description == "Test video description"
        assert retrieved_video.duration == 300
        assert retrieved_video.tags == ["test", "video"]
    
    def test_video_model_repr(self, temp_db):
        """Test Video model string representation."""
        video = Video(
            video_id="test_video_123",
            channel_id="test_channel_456",
            title="Test Video Title"
        )
        
        expected_repr = "<Video(video_id='test_video_123', title='Test Video Title')>"
        assert repr(video) == expected_repr
    
    def test_video_metrics_model_creation(self, temp_db):
        """Test VideoMetrics model creation and relationships."""
        # Create video first
        video = Video(
            video_id="test_video_123",
            channel_id="test_channel_456",
            title="Test Video"
        )
        temp_db.add(video)
        temp_db.commit()
        
        # Create metrics
        metrics = VideoMetrics(
            video_id="test_video_123",
            date=date(2024, 1, 1),
            impressions=10000,
            impressions_ctr=0.05,
            views=500,
            unique_viewers=450,
            average_view_duration=120.5,
            watch_time=60250,
            likes=25,
            comments=5,
            shares=3,
            subscribers_gained=2,
            subscribers_lost=1
        )
        
        temp_db.add(metrics)
        temp_db.commit()
        
        # Retrieve and verify
        retrieved_metrics = temp_db.query(VideoMetrics).filter_by(
            video_id="test_video_123",
            date=date(2024, 1, 1)
        ).first()
        
        assert retrieved_metrics is not None
        assert retrieved_metrics.video_id == "test_video_123"
        assert retrieved_metrics.impressions == 10000
        assert retrieved_metrics.impressions_ctr == 0.05
        assert retrieved_metrics.views == 500
        assert retrieved_metrics.average_view_duration == 120.5
        
        # Test relationship
        assert retrieved_metrics.video == video
        assert video.metrics[0] == retrieved_metrics
    
    def test_video_metrics_calculated_properties(self, temp_db):
        """Test calculated properties in VideoMetrics."""
        metrics = VideoMetrics(
            video_id="test_video_123",
            date=date(2024, 1, 1),
            views=1000,
            likes=50,
            comments=10,
            shares=5,
            average_view_duration=120,
            watch_time=120000
        )
        
        # Test engagement rate calculation
        expected_engagement_rate = (50 + 10 + 5) / 1000
        assert metrics.engagement_rate == expected_engagement_rate
        
        # Test average view percentage (assuming 3-minute video)
        video_duration = 180  # 3 minutes
        expected_avg_view_percentage = 120 / video_duration
        assert metrics.get_average_view_percentage(video_duration) == expected_avg_view_percentage
    
    def test_channel_metrics_model_creation(self, temp_db):
        """Test ChannelMetrics model creation."""
        channel_metrics = ChannelMetrics(
            channel_id="test_channel_456",
            date=date(2024, 1, 1),
            views=50000,
            impressions=200000,
            impressions_ctr=0.25,
            watch_time=1500000,
            subscribers_gained=100,
            subscribers_lost=10,
            videos_published=5
        )
        
        temp_db.add(channel_metrics)
        temp_db.commit()
        
        # Retrieve and verify
        retrieved_metrics = temp_db.query(ChannelMetrics).filter_by(
            channel_id="test_channel_456",
            date=date(2024, 1, 1)
        ).first()
        
        assert retrieved_metrics is not None
        assert retrieved_metrics.channel_id == "test_channel_456"
        assert retrieved_metrics.views == 50000
        assert retrieved_metrics.subscribers_gained == 100
        assert retrieved_metrics.net_subscribers == 90  # 100 - 10
    
    def test_insight_model_creation(self, temp_db):
        """Test Insight model creation."""
        insight_payload = {
            "action_type": "optimize_title",
            "suggested_title": "Better Video Title",
            "reasoning": "Current title has low CTR"
        }
        
        insight = Insight(
            video_id="test_video_123",
            insight_type="video",
            priority="high",
            confidence=0.85,
            rationale="Low CTR suggests title optimization needed",
            payload_json=insight_payload
        )
        
        temp_db.add(insight)
        temp_db.commit()
        
        # Retrieve and verify
        retrieved_insight = temp_db.query(Insight).filter_by(
            video_id="test_video_123"
        ).first()
        
        assert retrieved_insight is not None
        assert retrieved_insight.insight_type == "video"
        assert retrieved_insight.priority == "high"
        assert retrieved_insight.confidence == 0.85
        assert retrieved_insight.payload_json == insight_payload
    
    def test_insight_model_channel_level(self, temp_db):
        """Test Insight model for channel-level insights."""
        insight = Insight(
            video_id=None,  # Channel-level insight
            insight_type="channel",
            priority="medium",
            confidence=0.75,
            rationale="Upload schedule optimization recommended",
            payload_json={"recommended_schedule": "Tuesday, Thursday"}
        )
        
        temp_db.add(insight)
        temp_db.commit()
        
        # Retrieve and verify
        retrieved_insight = temp_db.query(Insight).filter_by(
            insight_type="channel"
        ).first()
        
        assert retrieved_insight is not None
        assert retrieved_insight.video_id is None
        assert retrieved_insight.insight_type == "channel"
    
    def test_api_quota_model_creation(self, temp_db):
        """Test APIQuota model creation."""
        quota = APIQuota(
            date=date(2024, 1, 1),
            data_api_quota_used=5000,
            analytics_api_quota_used=100
        )
        
        temp_db.add(quota)
        temp_db.commit()
        
        # Retrieve and verify
        retrieved_quota = temp_db.query(APIQuota).filter_by(
            date=date(2024, 1, 1)
        ).first()
        
        assert retrieved_quota is not None
        assert retrieved_quota.data_api_quota_used == 5000
        assert retrieved_quota.analytics_api_quota_used == 100
    
    def test_model_relationships(self, temp_db):
        """Test relationships between models."""
        # Create video
        video = Video(
            video_id="test_video_123",
            channel_id="test_channel_456",
            title="Test Video"
        )
        temp_db.add(video)
        
        # Create metrics
        metrics1 = VideoMetrics(
            video_id="test_video_123",
            date=date(2024, 1, 1),
            views=1000
        )
        metrics2 = VideoMetrics(
            video_id="test_video_123",
            date=date(2024, 1, 2),
            views=1500
        )
        temp_db.add_all([metrics1, metrics2])
        
        # Create insights
        insight1 = Insight(
            video_id="test_video_123",
            insight_type="video",
            priority="high",
            confidence=0.8,
            rationale="Test insight 1"
        )
        insight2 = Insight(
            video_id="test_video_123",
            insight_type="video",
            priority="medium",
            confidence=0.6,
            rationale="Test insight 2"
        )
        temp_db.add_all([insight1, insight2])
        
        temp_db.commit()
        
        # Test relationships
        retrieved_video = temp_db.query(Video).filter_by(video_id="test_video_123").first()
        
        assert len(retrieved_video.metrics) == 2
        assert len(retrieved_video.insights) == 2
        
        # Test back-references
        assert metrics1.video == retrieved_video
        assert insight1.video == retrieved_video

class TestDatabaseManager:
    """Test cases for DatabaseManager class."""
    
    @pytest.fixture
    def temp_db_file(self):
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    
    @pytest.fixture
    def mock_config(self, temp_db_file):
        """Create a mock configuration with temporary database."""
        config = Mock(spec=Config)
        config.database_url = f"sqlite:///{temp_db_file}"
        return config
    
    def test_database_manager_init(self, mock_config):
        """Test DatabaseManager initialization."""
        with patch('src.database.models.get_config', return_value=mock_config):
            db_manager = DatabaseManager()
            
            assert db_manager.engine is not None
            assert db_manager.SessionLocal is not None
    
    def test_create_tables(self, mock_config):
        """Test table creation."""
        with patch('src.database.models.get_config', return_value=mock_config):
            db_manager = DatabaseManager()
            db_manager.create_tables()
            
            # Verify tables exist by creating a session and querying
            session = db_manager.get_session()
            
            # Should not raise an exception
            session.query(Video).count()
            session.query(VideoMetrics).count()
            session.query(ChannelMetrics).count()
            session.query(Insight).count()
            session.query(APIQuota).count()
            
            session.close()
    
    def test_get_session(self, mock_config):
        """Test session creation."""
        with patch('src.database.models.get_config', return_value=mock_config):
            db_manager = DatabaseManager()
            db_manager.create_tables()
            
            session = db_manager.get_session()
            
            assert session is not None
            
            # Test basic operations
            video = Video(
                video_id="test_video",
                channel_id="test_channel",
                title="Test"
            )
            session.add(video)
            session.commit()
            
            retrieved = session.query(Video).filter_by(video_id="test_video").first()
            assert retrieved is not None
            
            session.close()
    
    def test_database_manager_singleton(self, mock_config):
        """Test that DatabaseManager behaves as singleton."""
        with patch('src.database.models.get_config', return_value=mock_config):
            # Clear any existing instance
            import src.database.models
            src.database.models._db_manager = None
            
            manager1 = DatabaseManager()
            manager2 = DatabaseManager()
            
            # Should be the same instance
            assert manager1 is manager2

class TestDatabaseUtilities:
    """Test database utility functions."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=Config)
        config.database_url = "sqlite:///:memory:"
        return config
    
    def test_get_db_session(self, mock_config):
        """Test get_db_session function."""
        with patch('src.database.models.get_config', return_value=mock_config):
            # Clear any existing instance
            import src.database.models
            src.database.models._db_manager = None
            
            session = get_db_session()
            
            assert session is not None
            
            # Should be able to perform basic operations
            result = session.execute("SELECT 1").scalar()
            assert result == 1
            
            session.close()

class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    @pytest.fixture
    def temp_db_file(self):
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    
    @pytest.fixture
    def mock_config(self, temp_db_file):
        """Create a mock configuration with temporary database."""
        config = Mock(spec=Config)
        config.database_url = f"sqlite:///{temp_db_file}"
        return config
    
    def test_full_data_workflow(self, mock_config):
        """Test complete data workflow from creation to retrieval."""
        with patch('src.database.models.get_config', return_value=mock_config):
            # Clear any existing instance
            import src.database.models
            src.database.models._db_manager = None
            
            # Initialize database
            db_manager = DatabaseManager()
            db_manager.create_tables()
            
            session = get_db_session()
            
            try:
                # Create video
                video = Video(
                    video_id="integration_test_video",
                    channel_id="integration_test_channel",
                    title="Integration Test Video",
                    description="Test description",
                    published_at=datetime(2024, 1, 1),
                    duration=300
                )
                session.add(video)
                
                # Create metrics for multiple days
                for day in range(1, 8):  # 7 days of data
                    metrics = VideoMetrics(
                        video_id="integration_test_video",
                        date=date(2024, 1, day),
                        impressions=1000 * day,
                        views=100 * day,
                        likes=10 * day,
                        comments=2 * day
                    )
                    session.add(metrics)
                
                # Create insights
                insight = Insight(
                    video_id="integration_test_video",
                    insight_type="video",
                    priority="high",
                    confidence=0.9,
                    rationale="Integration test insight",
                    payload_json={"test": "data"}
                )
                session.add(insight)
                
                # Create channel metrics
                channel_metrics = ChannelMetrics(
                    channel_id="integration_test_channel",
                    date=date(2024, 1, 1),
                    views=10000,
                    subscribers_gained=50
                )
                session.add(channel_metrics)
                
                # Create API quota record
                quota = APIQuota(
                    date=date(2024, 1, 1),
                    data_api_quota_used=1000,
                    analytics_api_quota_used=50
                )
                session.add(quota)
                
                session.commit()
                
                # Verify data was saved correctly
                saved_video = session.query(Video).filter_by(
                    video_id="integration_test_video"
                ).first()
                
                assert saved_video is not None
                assert len(saved_video.metrics) == 7
                assert len(saved_video.insights) == 1
                
                # Test aggregations
                total_views = sum(m.views for m in saved_video.metrics)
                assert total_views == sum(100 * day for day in range(1, 8))
                
                # Test relationships
                first_metrics = saved_video.metrics[0]
                assert first_metrics.video == saved_video
                
                first_insight = saved_video.insights[0]
                assert first_insight.video == saved_video
                assert first_insight.payload_json == {"test": "data"}
                
            finally:
                session.close()
    
    def test_constraint_violations(self, mock_config):
        """Test database constraint violations."""
        with patch('src.database.models.get_config', return_value=mock_config):
            # Clear any existing instance
            import src.database.models
            src.database.models._db_manager = None
            
            db_manager = DatabaseManager()
            db_manager.create_tables()
            
            session = get_db_session()
            
            try:
                # Create video
                video = Video(
                    video_id="constraint_test_video",
                    channel_id="constraint_test_channel",
                    title="Constraint Test"
                )
                session.add(video)
                session.commit()
                
                # Try to create duplicate video (should fail)
                duplicate_video = Video(
                    video_id="constraint_test_video",
                    channel_id="different_channel",
                    title="Duplicate Video"
                )
                session.add(duplicate_video)
                
                with pytest.raises(Exception):  # Should raise integrity error
                    session.commit()
                
                session.rollback()
                
                # Try to create metrics for non-existent video
                invalid_metrics = VideoMetrics(
                    video_id="non_existent_video",
                    date=date(2024, 1, 1),
                    views=100
                )
                session.add(invalid_metrics)
                
                with pytest.raises(Exception):  # Should raise foreign key error
                    session.commit()
                
            finally:
                session.close()

if __name__ == "__main__":
    pytest.main([__file__])