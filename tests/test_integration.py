#!/usr/bin/env python3
"""
Integration tests for YouTube Analytics application
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import pandas as pd
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.auth.youtube_auth import YouTubeAuth
from src.database.models import DatabaseManager, Video, VideoMetrics, ChannelMetrics, Insight
from src.ingestion.youtube_data import YouTubeDataIngester, IngestionResult
from src.ai.gemini_client import GeminiClient, InsightRequest, InsightResponse
from src.utils.optimization import MemoryCache, RateLimiter

class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        # Set up database
        db_manager = DatabaseManager(f"sqlite:///{db_path}")
        db_manager.create_tables()
        
        yield db_manager
        
        # Cleanup
        os.unlink(db_path)
    
    @pytest.fixture
    def mock_youtube_service(self):
        """Create mock YouTube service."""
        service = Mock()
        
        # Mock channel info
        service.channels().list().execute.return_value = {
            'items': [{
                'id': 'test_channel_id',
                'snippet': {
                    'title': 'Test Channel',
                    'description': 'Test channel description'
                },
                'statistics': {
                    'subscriberCount': '1000',
                    'videoCount': '50',
                    'viewCount': '100000'
                }
            }]
        }
        
        # Mock video list
        service.search().list().execute.return_value = {
            'items': [
                {
                    'id': {'videoId': 'video1'},
                    'snippet': {
                        'title': 'Test Video 1',
                        'description': 'Test description 1',
                        'publishedAt': '2024-01-01T00:00:00Z',
                        'thumbnails': {'default': {'url': 'http://example.com/thumb1.jpg'}}
                    }
                },
                {
                    'id': {'videoId': 'video2'},
                    'snippet': {
                        'title': 'Test Video 2',
                        'description': 'Test description 2',
                        'publishedAt': '2024-01-02T00:00:00Z',
                        'thumbnails': {'default': {'url': 'http://example.com/thumb2.jpg'}}
                    }
                }
            ]
        }
        
        # Mock video details
        service.videos().list().execute.return_value = {
            'items': [
                {
                    'id': 'video1',
                    'snippet': {
                        'title': 'Test Video 1',
                        'description': 'Test description 1',
                        'publishedAt': '2024-01-01T00:00:00Z',
                        'thumbnails': {'default': {'url': 'http://example.com/thumb1.jpg'}}
                    },
                    'statistics': {
                        'viewCount': '1000',
                        'likeCount': '50',
                        'commentCount': '10'
                    },
                    'contentDetails': {
                        'duration': 'PT5M30S'
                    }
                }
            ]
        }
        
        return service
    
    @pytest.fixture
    def mock_analytics_service(self):
        """Create mock YouTube Analytics service."""
        service = Mock()
        
        # Mock analytics data
        service.reports().query().execute.return_value = {
            'rows': [
                ['2024-01-01', 'video1', 5000, 0.05, 1000, 800, 300, 50, 10, 5, 2, 1],
                ['2024-01-02', 'video1', 4800, 0.048, 950, 760, 285, 48, 9, 4, 1, 0],
                ['2024-01-01', 'video2', 3000, 0.04, 600, 480, 180, 30, 6, 3, 1, 0],
            ],
            'columnHeaders': [
                {'name': 'day'},
                {'name': 'video'},
                {'name': 'impressions'},
                {'name': 'impressionsClickThroughRate'},
                {'name': 'views'},
                {'name': 'uniqueViewers'},
                {'name': 'watchTimeMinutes'},
                {'name': 'likes'},
                {'name': 'comments'},
                {'name': 'shares'},
                {'name': 'subscribersGained'},
                {'name': 'subscribersLost'}
            ]
        }
        
        return service
    
    @pytest.fixture
    def mock_gemini_client(self):
        """Create mock Gemini client."""
        client = Mock()
        
        # Mock insight generation
        client.generate_content.return_value.text = json.dumps({
            "action_type": "recommend_reindex",
            "confidence": 0.8,
            "rationale": "Video has good engagement but low CTR",
            "details": {
                "suggested_title": "Improved Title for Better CTR",
                "suggested_tags": ["tag1", "tag2", "tag3"]
            }
        })
        
        return client
    
    def test_complete_data_ingestion_workflow(self, temp_db, mock_youtube_service, mock_analytics_service):
        """Test complete data ingestion workflow."""
        # Create ingester with mocked services
        with patch('src.ingestion.youtube_data.build') as mock_build:
            mock_build.side_effect = [mock_youtube_service, mock_analytics_service]
            
            ingester = YouTubeDataIngester(
                credentials_path="dummy_path",
                db_manager=temp_db
            )
            
            # Set up mock authentication
            ingester.youtube_service = mock_youtube_service
            ingester.analytics_service = mock_analytics_service
            
            # Perform ingestion
            start_date = datetime(2024, 1, 1)
            end_date = datetime(2024, 1, 2)
            
            result = ingester.ingest_data(
                channel_id="test_channel_id",
                start_date=start_date,
                end_date=end_date
            )
            
            # Verify result
            assert isinstance(result, IngestionResult)
            assert result.success is True
            assert result.videos_processed > 0
            assert result.metrics_processed > 0
            
            # Verify data was saved to database
            with temp_db.get_session() as session:
                videos = session.query(Video).all()
                assert len(videos) >= 1
                
                metrics = session.query(VideoMetrics).all()
                assert len(metrics) >= 1
                
                # Verify video data
                video = videos[0]
                assert video.video_id in ['video1', 'video2']
                assert video.title is not None
                assert video.channel_id == "test_channel_id"
                
                # Verify metrics data
                metric = metrics[0]
                assert metric.video_id in ['video1', 'video2']
                assert metric.impressions > 0
                assert metric.views > 0
    
    def test_ai_insight_generation_workflow(self, temp_db, mock_gemini_client):
        """Test AI insight generation workflow."""
        # Set up test data in database
        with temp_db.get_session() as session:
            # Add test video
            video = Video(
                video_id="test_video",
                channel_id="test_channel",
                title="Test Video",
                description="Test description",
                published_at=datetime(2024, 1, 1),
                thumbnail_url="http://example.com/thumb.jpg"
            )
            session.add(video)
            
            # Add test metrics
            metrics = VideoMetrics(
                video_id="test_video",
                date=datetime(2024, 1, 1).date(),
                impressions=5000,
                ctr=0.05,
                views=1000,
                unique_viewers=800,
                watch_time_minutes=300,
                avg_view_duration_seconds=180,
                likes=50,
                comments=10,
                shares=5,
                subscribers_gained=2,
                subscribers_lost=1
            )
            session.add(metrics)
            session.commit()
        
        # Create Gemini client with mock
        with patch('src.ai.gemini_client.genai') as mock_genai:
            mock_genai.GenerativeModel.return_value = mock_gemini_client
            
            gemini_client = GeminiClient(
                api_key="test_key",
                db_manager=temp_db
            )
            gemini_client.model = mock_gemini_client
            
            # Generate insight
            insight_request = InsightRequest(
                video_id="test_video",
                title="Test Video",
                impressions=5000,
                views=1000,
                ctr=0.05,
                avg_view_duration_sec=180,
                watch_time=18000,
                published_at="2024-01-01"
            )
            
            response = gemini_client.generate_video_insight(insight_request)
            
            # Verify response
            assert isinstance(response, InsightResponse)
            assert response.action_type == "recommend_reindex"
            assert response.confidence == 0.8
            assert response.rationale is not None
            
            # Verify insight was saved to database
            with temp_db.get_session() as session:
                insights = session.query(Insight).all()
                assert len(insights) == 1
                
                insight = insights[0]
                assert insight.video_id == "test_video"
                assert insight.insight_type == "video"
                assert insight.confidence == 0.8
    
    def test_authentication_and_service_creation_workflow(self):
        """Test authentication and service creation workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            credentials_path = os.path.join(temp_dir, "credentials.json")
            
            # Create mock credentials file
            credentials_data = {
                "installed": {
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            }
            
            with open(credentials_path, 'w') as f:
                json.dump(credentials_data, f)
            
            # Mock the OAuth flow
            with patch('src.auth.youtube_auth.InstalledAppFlow') as mock_flow_class:
                mock_flow = Mock()
                mock_flow_class.from_client_secrets_file.return_value = mock_flow
                
                mock_credentials = Mock()
                mock_credentials.to_json.return_value = json.dumps({
                    "token": "test_token",
                    "refresh_token": "test_refresh_token"
                })
                mock_flow.run_local_server.return_value = mock_credentials
                
                # Create auth instance
                auth = YouTubeAuth(credentials_path, temp_dir)
                
                # Test authentication
                success = auth.authenticate()
                assert success is True
                
                # Verify credentials were saved
                token_path = os.path.join(temp_dir, "token.json")
                assert os.path.exists(token_path)
    
    def test_caching_and_rate_limiting_integration(self, temp_db):
        """Test caching and rate limiting integration."""
        # Create cache and rate limiter
        cache = MemoryCache(max_size=100, ttl=300)
        rate_limiter = RateLimiter(max_calls=5, time_window=60)
        
        call_count = [0]
        
        def expensive_api_call(param):
            """Simulate expensive API call."""
            if not rate_limiter.allow_request():
                raise Exception("Rate limit exceeded")
            
            call_count[0] += 1
            return f"result_for_{param}"
        
        def cached_api_call(param):
            """Cached version of API call."""
            cache_key = f"api_call_{param}"
            
            # Check cache first
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Make API call and cache result
            result = expensive_api_call(param)
            cache.set(cache_key, result)
            return result
        
        # Test caching behavior
        result1 = cached_api_call("param1")
        assert result1 == "result_for_param1"
        assert call_count[0] == 1
        
        # Second call should use cache
        result2 = cached_api_call("param1")
        assert result2 == "result_for_param1"
        assert call_count[0] == 1  # No additional API call
        
        # Different parameter should make new API call
        result3 = cached_api_call("param2")
        assert result3 == "result_for_param2"
        assert call_count[0] == 2
        
        # Test rate limiting
        for i in range(3):  # 3 more calls (total 5)
            cached_api_call(f"param{i+3}")
        
        assert call_count[0] == 5
        
        # Next call should be rate limited
        with pytest.raises(Exception, match="Rate limit exceeded"):
            cached_api_call("param_over_limit")
    
    def test_database_transaction_handling(self, temp_db):
        """Test database transaction handling and rollback."""
        # Test successful transaction
        with temp_db.get_session() as session:
            video = Video(
                video_id="test_video_1",
                channel_id="test_channel",
                title="Test Video 1",
                description="Test description",
                published_at=datetime(2024, 1, 1),
                thumbnail_url="http://example.com/thumb.jpg"
            )
            session.add(video)
            session.commit()
        
        # Verify data was saved
        with temp_db.get_session() as session:
            videos = session.query(Video).all()
            assert len(videos) == 1
        
        # Test transaction rollback on error
        try:
            with temp_db.get_session() as session:
                video2 = Video(
                    video_id="test_video_2",
                    channel_id="test_channel",
                    title="Test Video 2",
                    description="Test description",
                    published_at=datetime(2024, 1, 2),
                    thumbnail_url="http://example.com/thumb2.jpg"
                )
                session.add(video2)
                
                # Simulate error before commit
                raise Exception("Simulated error")
        except Exception:
            pass  # Expected
        
        # Verify rollback - should still have only 1 video
        with temp_db.get_session() as session:
            videos = session.query(Video).all()
            assert len(videos) == 1
    
    def test_data_validation_and_error_handling(self, temp_db):
        """Test data validation and error handling across modules."""
        # Test invalid video data
        with temp_db.get_session() as session:
            # Missing required fields should raise error
            with pytest.raises(Exception):
                invalid_video = Video(
                    video_id=None,  # Required field
                    channel_id="test_channel",
                    title="Test Video"
                )
                session.add(invalid_video)
                session.commit()
        
        # Test invalid metrics data
        with temp_db.get_session() as session:
            # Add valid video first
            video = Video(
                video_id="test_video",
                channel_id="test_channel",
                title="Test Video",
                description="Test description",
                published_at=datetime(2024, 1, 1),
                thumbnail_url="http://example.com/thumb.jpg"
            )
            session.add(video)
            session.commit()
            
            # Invalid metrics (negative values)
            with pytest.raises(Exception):
                invalid_metrics = VideoMetrics(
                    video_id="test_video",
                    date=datetime(2024, 1, 1).date(),
                    impressions=-100,  # Invalid negative value
                    views=1000
                )
                session.add(invalid_metrics)
                session.commit()

class TestModuleInteractions:
    """Test interactions between different modules."""
    
    def test_auth_and_ingestion_integration(self):
        """Test integration between authentication and data ingestion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock successful authentication
            with patch('src.auth.youtube_auth.InstalledAppFlow') as mock_flow_class:
                mock_flow = Mock()
                mock_flow_class.from_client_secrets_file.return_value = mock_flow
                
                mock_credentials = Mock()
                mock_credentials.to_json.return_value = json.dumps({
                    "token": "test_token",
                    "refresh_token": "test_refresh_token"
                })
                mock_flow.run_local_server.return_value = mock_credentials
                
                # Create credentials file
                credentials_path = os.path.join(temp_dir, "credentials.json")
                with open(credentials_path, 'w') as f:
                    json.dump({"installed": {"client_id": "test"}}, f)
                
                # Test auth
                auth = YouTubeAuth(credentials_path, temp_dir)
                success = auth.authenticate()
                assert success is True
                
                # Test that ingester can use authenticated credentials
                with patch('src.ingestion.youtube_data.build') as mock_build:
                    mock_service = Mock()
                    mock_build.return_value = mock_service
                    
                    # Create temporary database
                    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
                        db_path = f.name
                    
                    try:
                        db_manager = DatabaseManager(f"sqlite:///{db_path}")
                        db_manager.create_tables()
                        
                        ingester = YouTubeDataIngester(
                            credentials_path=credentials_path,
                            db_manager=db_manager
                        )
                        
                        # Verify ingester was created successfully
                        assert ingester is not None
                        
                    finally:
                        os.unlink(db_path)
    
    def test_ingestion_and_ai_integration(self, temp_db):
        """Test integration between data ingestion and AI insights."""
        # Set up test data
        with temp_db.get_session() as session:
            video = Video(
                video_id="test_video",
                channel_id="test_channel",
                title="Test Video",
                description="Test description",
                published_at=datetime(2024, 1, 1),
                thumbnail_url="http://example.com/thumb.jpg"
            )
            session.add(video)
            
            metrics = VideoMetrics(
                video_id="test_video",
                date=datetime(2024, 1, 1).date(),
                impressions=5000,
                ctr=0.05,
                views=1000,
                unique_viewers=800,
                watch_time_minutes=300,
                avg_view_duration_seconds=180,
                likes=50,
                comments=10,
                shares=5,
                subscribers_gained=2,
                subscribers_lost=1
            )
            session.add(metrics)
            session.commit()
        
        # Test AI insight generation using ingested data
        with patch('src.ai.gemini_client.genai') as mock_genai:
            mock_model = Mock()
            mock_model.generate_content.return_value.text = json.dumps({
                "action_type": "optimize_title",
                "confidence": 0.9,
                "rationale": "Good engagement metrics suggest title optimization could improve CTR",
                "details": {"suggested_title": "Optimized Title"}
            })
            mock_genai.GenerativeModel.return_value = mock_model
            
            gemini_client = GeminiClient(
                api_key="test_key",
                db_manager=temp_db
            )
            
            # Generate insights from ingested data
            with temp_db.get_session() as session:
                video_data = session.query(Video).filter_by(video_id="test_video").first()
                metrics_data = session.query(VideoMetrics).filter_by(video_id="test_video").first()
                
                insight_request = InsightRequest(
                    video_id=video_data.video_id,
                    title=video_data.title,
                    impressions=metrics_data.impressions,
                    views=metrics_data.views,
                    ctr=metrics_data.ctr,
                    avg_view_duration_sec=metrics_data.avg_view_duration_seconds,
                    watch_time=metrics_data.watch_time_minutes * 60,
                    published_at=video_data.published_at.isoformat()
                )
                
                response = gemini_client.generate_video_insight(insight_request)
                
                assert response.action_type == "optimize_title"
                assert response.confidence == 0.9
    
    def test_database_and_caching_integration(self, temp_db):
        """Test integration between database operations and caching."""
        cache = MemoryCache(max_size=50, ttl=300)
        
        def get_video_metrics_cached(video_id):
            """Get video metrics with caching."""
            cache_key = f"metrics_{video_id}"
            
            # Check cache first
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Query database
            with temp_db.get_session() as session:
                metrics = session.query(VideoMetrics).filter_by(video_id=video_id).all()
                result = [{
                    'date': m.date.isoformat(),
                    'views': m.views,
                    'impressions': m.impressions,
                    'ctr': m.ctr
                } for m in metrics]
            
            # Cache result
            cache.set(cache_key, result)
            return result
        
        # Set up test data
        with temp_db.get_session() as session:
            video = Video(
                video_id="cached_video",
                channel_id="test_channel",
                title="Cached Video",
                description="Test description",
                published_at=datetime(2024, 1, 1),
                thumbnail_url="http://example.com/thumb.jpg"
            )
            session.add(video)
            
            for i in range(3):
                metrics = VideoMetrics(
                    video_id="cached_video",
                    date=(datetime(2024, 1, 1) + timedelta(days=i)).date(),
                    impressions=1000 + i * 100,
                    views=100 + i * 10,
                    ctr=0.1 + i * 0.01
                )
                session.add(metrics)
            
            session.commit()
        
        # Test caching behavior
        result1 = get_video_metrics_cached("cached_video")
        assert len(result1) == 3
        assert cache.size == 1
        
        # Second call should use cache
        result2 = get_video_metrics_cached("cached_video")
        assert result1 == result2
        assert cache.size == 1

class TestErrorRecovery:
    """Test error recovery and resilience."""
    
    def test_database_connection_recovery(self):
        """Test database connection recovery after failure."""
        # Create database that will be "corrupted"
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            # Create initial database
            db_manager = DatabaseManager(f"sqlite:///{db_path}")
            db_manager.create_tables()
            
            # Add some data
            with db_manager.get_session() as session:
                video = Video(
                    video_id="test_video",
                    channel_id="test_channel",
                    title="Test Video",
                    description="Test description",
                    published_at=datetime(2024, 1, 1),
                    thumbnail_url="http://example.com/thumb.jpg"
                )
                session.add(video)
                session.commit()
            
            # Simulate database corruption by deleting file
            os.unlink(db_path)
            
            # Try to recreate database
            db_manager2 = DatabaseManager(f"sqlite:///{db_path}")
            db_manager2.create_tables()
            
            # Should be able to add data to new database
            with db_manager2.get_session() as session:
                video2 = Video(
                    video_id="test_video_2",
                    channel_id="test_channel",
                    title="Test Video 2",
                    description="Test description",
                    published_at=datetime(2024, 1, 2),
                    thumbnail_url="http://example.com/thumb2.jpg"
                )
                session.add(video2)
                session.commit()
            
            # Verify recovery
            with db_manager2.get_session() as session:
                videos = session.query(Video).all()
                assert len(videos) == 1
                assert videos[0].video_id == "test_video_2"
        
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_api_failure_recovery(self):
        """Test recovery from API failures."""
        call_count = [0]
        
        def failing_api_call():
            """API call that fails first few times."""
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("API temporarily unavailable")
            return "success"
        
        def retry_api_call(max_retries=5):
            """API call with retry logic."""
            for attempt in range(max_retries):
                try:
                    return failing_api_call()
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(0.1)  # Brief delay between retries
        
        # Should succeed after retries
        result = retry_api_call()
        assert result == "success"
        assert call_count[0] == 3
    
    def test_cache_corruption_recovery(self):
        """Test recovery from cache corruption."""
        with tempfile.TemporaryDirectory() as temp_dir:
            from src.utils.optimization import FileCache
            
            cache = FileCache(cache_dir=temp_dir, ttl=300)
            
            # Add some data
            cache.set("key1", "value1")
            cache.set("key2", "value2")
            
            # Corrupt a cache file
            cache_files = list(Path(temp_dir).glob("*.json"))
            if cache_files:
                cache_files[0].write_text("corrupted json")
            
            # Cache should handle corruption gracefully
            result1 = cache.get("key1")  # Might be None due to corruption
            result2 = cache.get("key2")  # Should work if not corrupted
            
            # Should be able to add new data
            cache.set("key3", "value3")
            result3 = cache.get("key3")
            assert result3 == "value3"

if __name__ == "__main__":
    pytest.main([__file__])