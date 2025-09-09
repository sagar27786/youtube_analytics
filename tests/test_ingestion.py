#!/usr/bin/env python3
"""
Unit tests for YouTube data ingestion module
"""

import pytest
import tempfile
import os
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.youtube_data import (
    YouTubeDataIngester, IngestionResult, get_ingester
)
from src.database.models import Video, VideoMetrics, ChannelMetrics, APIQuota
from src.auth.youtube_auth import YouTubeAuthenticator

class TestIngestionResult:
    """Test cases for IngestionResult dataclass."""
    
    def test_ingestion_result_creation(self):
        """Test IngestionResult creation and properties."""
        result = IngestionResult(
            success=True,
            videos_processed=10,
            metrics_saved=50,
            errors=[],
            quota_used=1000
        )
        
        assert result.success is True
        assert result.videos_processed == 10
        assert result.metrics_saved == 50
        assert result.errors == []
        assert result.quota_used == 1000
    
    def test_ingestion_result_with_errors(self):
        """Test IngestionResult with errors."""
        errors = ["API quota exceeded", "Video not found"]
        result = IngestionResult(
            success=False,
            videos_processed=5,
            metrics_saved=20,
            errors=errors,
            quota_used=5000
        )
        
        assert result.success is False
        assert result.errors == errors
        assert len(result.errors) == 2

class TestYouTubeDataIngester:
    """Test cases for YouTubeDataIngester class."""
    
    @pytest.fixture
    def mock_authenticator(self):
        """Create a mock YouTube authenticator."""
        auth = Mock(spec=YouTubeAuthenticator)
        auth.is_authenticated.return_value = True
        auth.get_channel_info.return_value = {
            'id': 'test_channel_123',
            'snippet': {
                'title': 'Test Channel',
                'description': 'Test channel description'
            },
            'statistics': {
                'subscriberCount': '1000',
                'videoCount': '50',
                'viewCount': '100000'
            }
        }
        return auth
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = Mock()
        session.query.return_value.filter_by.return_value.first.return_value = None
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        return session
    
    @pytest.fixture
    def mock_youtube_service(self):
        """Create a mock YouTube Data API service."""
        service = Mock()
        
        # Mock search response
        search_response = {
            'items': [
                {
                    'id': {'videoId': 'video_123'},
                    'snippet': {
                        'title': 'Test Video 1',
                        'description': 'Test description 1',
                        'publishedAt': '2024-01-01T12:00:00Z',
                        'thumbnails': {
                            'default': {'url': 'https://example.com/thumb1.jpg'}
                        }
                    }
                },
                {
                    'id': {'videoId': 'video_456'},
                    'snippet': {
                        'title': 'Test Video 2',
                        'description': 'Test description 2',
                        'publishedAt': '2024-01-02T12:00:00Z',
                        'thumbnails': {
                            'default': {'url': 'https://example.com/thumb2.jpg'}
                        }
                    }
                }
            ],
            'nextPageToken': None
        }
        
        service.search.return_value.list.return_value.execute.return_value = search_response
        
        # Mock videos response
        videos_response = {
            'items': [
                {
                    'id': 'video_123',
                    'snippet': {
                        'title': 'Test Video 1',
                        'description': 'Test description 1',
                        'publishedAt': '2024-01-01T12:00:00Z',
                        'tags': ['test', 'video'],
                        'thumbnails': {
                            'default': {'url': 'https://example.com/thumb1.jpg'}
                        }
                    },
                    'contentDetails': {
                        'duration': 'PT5M30S'  # 5 minutes 30 seconds
                    },
                    'statistics': {
                        'viewCount': '1000',
                        'likeCount': '50',
                        'commentCount': '10'
                    }
                }
            ]
        }
        
        service.videos.return_value.list.return_value.execute.return_value = videos_response
        
        return service
    
    @pytest.fixture
    def mock_analytics_service(self):
        """Create a mock YouTube Analytics API service."""
        service = Mock()
        
        # Mock analytics response
        analytics_response = {
            'rows': [
                ['2024-01-01', 'video_123', 10000, 0.05, 500, 450, 120.5, 60250, 25, 5, 3, 2, 1],
                ['2024-01-02', 'video_123', 12000, 0.06, 600, 550, 130.0, 78000, 30, 8, 4, 3, 0]
            ],
            'columnHeaders': [
                {'name': 'day'},
                {'name': 'video'},
                {'name': 'impressions'},
                {'name': 'impressionsClickThroughRate'},
                {'name': 'views'},
                {'name': 'uniqueViewers'},
                {'name': 'averageViewDuration'},
                {'name': 'watchTime'},
                {'name': 'likes'},
                {'name': 'comments'},
                {'name': 'shares'},
                {'name': 'subscribersGained'},
                {'name': 'subscribersLost'}
            ]
        }
        
        service.reports.return_value.query.return_value.execute.return_value = analytics_response
        
        return service
    
    def test_ingester_initialization(self, mock_authenticator, mock_db_session):
        """Test YouTubeDataIngester initialization."""
        with patch('src.ingestion.youtube_data.get_db_session', return_value=mock_db_session):
            ingester = YouTubeDataIngester(mock_authenticator)
            
            assert ingester.auth == mock_authenticator
            assert ingester.db_session == mock_db_session
            assert ingester.quota_tracker == {}
    
    def test_ingester_initialization_unauthenticated(self):
        """Test ingester initialization with unauthenticated user."""
        auth = Mock(spec=YouTubeAuthenticator)
        auth.is_authenticated.return_value = False
        
        with pytest.raises(ValueError, match="YouTube authentication required"):
            YouTubeDataIngester(auth)
    
    def test_track_quota_usage(self, mock_authenticator, mock_db_session):
        """Test quota tracking functionality."""
        with patch('src.ingestion.youtube_data.get_db_session', return_value=mock_db_session):
            ingester = YouTubeDataIngester(mock_authenticator)
            
            # Track some quota usage
            ingester._track_quota_usage('data_api', 100)
            ingester._track_quota_usage('analytics_api', 50)
            ingester._track_quota_usage('data_api', 200)
            
            assert ingester.quota_tracker['data_api'] == 300
            assert ingester.quota_tracker['analytics_api'] == 50
    
    def test_save_quota_usage(self, mock_authenticator, mock_db_session):
        """Test saving quota usage to database."""
        with patch('src.ingestion.youtube_data.get_db_session', return_value=mock_db_session):
            ingester = YouTubeDataIngester(mock_authenticator)
            
            # Set up quota tracking
            ingester.quota_tracker = {
                'data_api': 1000,
                'analytics_api': 200
            }
            
            # Mock existing quota record
            existing_quota = APIQuota(
                date=date.today(),
                data_api_quota_used=500,
                analytics_api_quota_used=100
            )
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = existing_quota
            
            ingester._save_quota_usage()
            
            # Verify quota was updated
            assert existing_quota.data_api_quota_used == 1500  # 500 + 1000
            assert existing_quota.analytics_api_quota_used == 300  # 100 + 200
            mock_db_session.commit.assert_called_once()
    
    def test_save_quota_usage_new_record(self, mock_authenticator, mock_db_session):
        """Test saving quota usage when no existing record."""
        with patch('src.ingestion.youtube_data.get_db_session', return_value=mock_db_session):
            ingester = YouTubeDataIngester(mock_authenticator)
            
            ingester.quota_tracker = {
                'data_api': 1000,
                'analytics_api': 200
            }
            
            # No existing quota record
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
            
            ingester._save_quota_usage()
            
            # Verify new quota record was created
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
    
    def test_parse_duration(self, mock_authenticator, mock_db_session):
        """Test ISO 8601 duration parsing."""
        with patch('src.ingestion.youtube_data.get_db_session', return_value=mock_db_session):
            ingester = YouTubeDataIngester(mock_authenticator)
            
            # Test various duration formats
            assert ingester._parse_duration('PT5M30S') == 330  # 5:30
            assert ingester._parse_duration('PT1H2M3S') == 3723  # 1:02:03
            assert ingester._parse_duration('PT45S') == 45  # 0:45
            assert ingester._parse_duration('PT2M') == 120  # 2:00
            assert ingester._parse_duration('PT1H') == 3600  # 1:00:00
            assert ingester._parse_duration('P1DT2H3M4S') == 93784  # 1 day + 2:03:04
            
            # Test invalid format
            assert ingester._parse_duration('invalid') == 0
    
    @patch('src.ingestion.youtube_data.sleep')
    def test_fetch_channel_info_with_retry(self, mock_sleep, mock_authenticator, mock_db_session, mock_youtube_service):
        """Test fetching channel info with retry logic."""
        with patch('src.ingestion.youtube_data.get_db_session', return_value=mock_db_session):
            ingester = YouTubeDataIngester(mock_authenticator)
            
            # Mock service creation
            mock_authenticator.create_youtube_service.return_value = mock_youtube_service
            
            # Test successful fetch
            channel_info = ingester._fetch_channel_info()
            
            assert channel_info is not None
            assert 'id' in channel_info
            mock_authenticator.create_youtube_service.assert_called_with('youtube', 'v3')
    
    @patch('src.ingestion.youtube_data.sleep')
    def test_fetch_channel_info_retry_on_error(self, mock_sleep, mock_authenticator, mock_db_session):
        """Test retry logic when fetching channel info fails."""
        with patch('src.ingestion.youtube_data.get_db_session', return_value=mock_db_session):
            ingester = YouTubeDataIngester(mock_authenticator)
            
            # Mock service that raises exception
            mock_service = Mock()
            mock_service.channels.return_value.list.return_value.execute.side_effect = [
                Exception("API Error"),  # First attempt fails
                Exception("API Error"),  # Second attempt fails
                {'items': [{'id': 'test_channel'}]}  # Third attempt succeeds
            ]
            
            mock_authenticator.create_youtube_service.return_value = mock_service
            
            channel_info = ingester._fetch_channel_info()
            
            assert channel_info is not None
            assert mock_sleep.call_count == 2  # Should have slept twice (after first two failures)
    
    def test_fetch_videos_for_channel(self, mock_authenticator, mock_db_session, mock_youtube_service):
        """Test fetching videos for a channel."""
        with patch('src.ingestion.youtube_data.get_db_session', return_value=mock_db_session):
            ingester = YouTubeDataIngester(mock_authenticator)
            
            mock_authenticator.create_youtube_service.return_value = mock_youtube_service
            
            start_date = date(2024, 1, 1)
            end_date = date(2024, 1, 31)
            
            videos = ingester._fetch_videos_for_channel('test_channel_123', start_date, end_date)
            
            assert len(videos) == 2
            assert videos[0]['id']['videoId'] == 'video_123'
            assert videos[1]['id']['videoId'] == 'video_456'
    
    def test_fetch_video_details(self, mock_authenticator, mock_db_session, mock_youtube_service):
        """Test fetching detailed video information."""
        with patch('src.ingestion.youtube_data.get_db_session', return_value=mock_db_session):
            ingester = YouTubeDataIngester(mock_authenticator)
            
            mock_authenticator.create_youtube_service.return_value = mock_youtube_service
            
            video_ids = ['video_123', 'video_456']
            video_details = ingester._fetch_video_details(video_ids)
            
            assert len(video_details) == 1  # Mock returns one video
            assert video_details[0]['id'] == 'video_123'
            assert 'contentDetails' in video_details[0]
            assert 'statistics' in video_details[0]
    
    def test_fetch_video_analytics(self, mock_authenticator, mock_db_session, mock_analytics_service):
        """Test fetching video analytics data."""
        with patch('src.ingestion.youtube_data.get_db_session', return_value=mock_db_session):
            ingester = YouTubeDataIngester(mock_authenticator)
            
            mock_authenticator.create_youtube_service.return_value = mock_analytics_service
            
            start_date = date(2024, 1, 1)
            end_date = date(2024, 1, 2)
            video_ids = ['video_123']
            
            analytics_data = ingester._fetch_video_analytics(video_ids, start_date, end_date)
            
            assert len(analytics_data) == 2  # Two days of data
            assert analytics_data[0][1] == 'video_123'  # Video ID
            assert analytics_data[0][2] == 10000  # Impressions
    
    def test_save_video_to_db(self, mock_authenticator, mock_db_session):
        """Test saving video data to database."""
        with patch('src.ingestion.youtube_data.get_db_session', return_value=mock_db_session):
            ingester = YouTubeDataIngester(mock_authenticator)
            
            video_data = {
                'id': 'test_video_123',
                'snippet': {
                    'title': 'Test Video',
                    'description': 'Test description',
                    'publishedAt': '2024-01-01T12:00:00Z',
                    'tags': ['test', 'video'],
                    'thumbnails': {
                        'default': {'url': 'https://example.com/thumb.jpg'}
                    }
                },
                'contentDetails': {
                    'duration': 'PT5M30S'
                }
            }
            
            channel_id = 'test_channel_123'
            
            # Mock no existing video
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
            
            ingester._save_video_to_db(video_data, channel_id)
            
            # Verify video was added
            mock_db_session.add.assert_called_once()
            
            # Get the video object that was added
            added_video = mock_db_session.add.call_args[0][0]
            assert isinstance(added_video, Video)
            assert added_video.video_id == 'test_video_123'
            assert added_video.channel_id == 'test_channel_123'
            assert added_video.title == 'Test Video'
            assert added_video.duration == 330  # 5:30 in seconds
    
    def test_save_video_metrics_to_db(self, mock_authenticator, mock_db_session):
        """Test saving video metrics to database."""
        with patch('src.ingestion.youtube_data.get_db_session', return_value=mock_db_session):
            ingester = YouTubeDataIngester(mock_authenticator)
            
            analytics_row = [
                '2024-01-01', 'video_123', 10000, 0.05, 500, 450, 120.5, 60250, 25, 5, 3, 2, 1
            ]
            
            # Mock no existing metrics
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
            
            ingester._save_video_metrics_to_db(analytics_row)
            
            # Verify metrics were added
            mock_db_session.add.assert_called_once()
            
            # Get the metrics object that was added
            added_metrics = mock_db_session.add.call_args[0][0]
            assert isinstance(added_metrics, VideoMetrics)
            assert added_metrics.video_id == 'video_123'
            assert added_metrics.date == date(2024, 1, 1)
            assert added_metrics.impressions == 10000
            assert added_metrics.views == 500
    
    def test_ingest_data_success(self, mock_authenticator, mock_db_session, mock_youtube_service, mock_analytics_service):
        """Test successful data ingestion workflow."""
        with patch('src.ingestion.youtube_data.get_db_session', return_value=mock_db_session):
            ingester = YouTubeDataIngester(mock_authenticator)
            
            # Mock services
            mock_authenticator.create_youtube_service.side_effect = [
                mock_youtube_service,  # For data API
                mock_analytics_service  # For analytics API
            ]
            
            # Mock no existing data in DB
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
            
            start_date = date(2024, 1, 1)
            end_date = date(2024, 1, 2)
            
            result = ingester.ingest_data(start_date, end_date)
            
            assert result.success is True
            assert result.videos_processed > 0
            assert result.metrics_saved > 0
            assert len(result.errors) == 0
            assert result.quota_used > 0
    
    def test_ingest_data_with_errors(self, mock_authenticator, mock_db_session):
        """Test data ingestion with errors."""
        with patch('src.ingestion.youtube_data.get_db_session', return_value=mock_db_session):
            ingester = YouTubeDataIngester(mock_authenticator)
            
            # Mock service that raises exception
            mock_service = Mock()
            mock_service.channels.return_value.list.return_value.execute.side_effect = Exception("API Error")
            mock_authenticator.create_youtube_service.return_value = mock_service
            
            start_date = date(2024, 1, 1)
            end_date = date(2024, 1, 2)
            
            with patch('src.ingestion.youtube_data.sleep'):  # Mock sleep to speed up test
                result = ingester.ingest_data(start_date, end_date)
            
            assert result.success is False
            assert len(result.errors) > 0
            assert "Failed to fetch channel info" in result.errors[0]
    
    def test_ingest_data_date_validation(self, mock_authenticator, mock_db_session):
        """Test date validation in ingest_data method."""
        with patch('src.ingestion.youtube_data.get_db_session', return_value=mock_db_session):
            ingester = YouTubeDataIngester(mock_authenticator)
            
            # Test invalid date range (end before start)
            start_date = date(2024, 1, 10)
            end_date = date(2024, 1, 5)
            
            with pytest.raises(ValueError, match="End date must be after start date"):
                ingester.ingest_data(start_date, end_date)
            
            # Test future dates
            future_date = date.today() + timedelta(days=1)
            
            with pytest.raises(ValueError, match="Cannot fetch data for future dates"):
                ingester.ingest_data(date.today(), future_date)

class TestIngesterUtilities:
    """Test utility functions for ingestion module."""
    
    @patch('src.ingestion.youtube_data.get_db_session')
    def test_get_ingester_function(self, mock_get_db_session):
        """Test get_ingester utility function."""
        mock_session = Mock()
        mock_get_db_session.return_value = mock_session
        
        mock_auth = Mock(spec=YouTubeAuthenticator)
        mock_auth.is_authenticated.return_value = True
        
        with patch('src.ingestion.youtube_data.get_authenticator', return_value=mock_auth):
            ingester = get_ingester()
            
            assert isinstance(ingester, YouTubeDataIngester)
            assert ingester.auth == mock_auth
    
    @patch('src.ingestion.youtube_data.get_db_session')
    def test_get_ingester_unauthenticated(self, mock_get_db_session):
        """Test get_ingester with unauthenticated user."""
        mock_session = Mock()
        mock_get_db_session.return_value = mock_session
        
        mock_auth = Mock(spec=YouTubeAuthenticator)
        mock_auth.is_authenticated.return_value = False
        
        with patch('src.ingestion.youtube_data.get_authenticator', return_value=mock_auth):
            with pytest.raises(ValueError, match="YouTube authentication required"):
                get_ingester()

class TestIngestionIntegration:
    """Integration tests for data ingestion."""
    
    @pytest.fixture
    def mock_full_setup(self):
        """Set up mocks for full integration test."""
        # Mock authenticator
        auth = Mock(spec=YouTubeAuthenticator)
        auth.is_authenticated.return_value = True
        auth.get_channel_info.return_value = {'id': 'test_channel'}
        
        # Mock database session
        session = Mock()
        session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Mock YouTube services
        data_service = Mock()
        analytics_service = Mock()
        
        # Configure data service responses
        data_service.channels.return_value.list.return_value.execute.return_value = {
            'items': [{'id': 'test_channel', 'snippet': {'title': 'Test Channel'}}]
        }
        
        data_service.search.return_value.list.return_value.execute.return_value = {
            'items': [
                {
                    'id': {'videoId': 'video_123'},
                    'snippet': {
                        'title': 'Test Video',
                        'publishedAt': '2024-01-01T12:00:00Z'
                    }
                }
            ]
        }
        
        data_service.videos.return_value.list.return_value.execute.return_value = {
            'items': [
                {
                    'id': 'video_123',
                    'snippet': {
                        'title': 'Test Video',
                        'publishedAt': '2024-01-01T12:00:00Z'
                    },
                    'contentDetails': {'duration': 'PT5M'},
                    'statistics': {'viewCount': '1000'}
                }
            ]
        }
        
        # Configure analytics service response
        analytics_service.reports.return_value.query.return_value.execute.return_value = {
            'rows': [['2024-01-01', 'video_123', 1000, 0.05, 100, 90, 60, 6000, 10, 2, 1, 1, 0]],
            'columnHeaders': [
                {'name': 'day'}, {'name': 'video'}, {'name': 'impressions'},
                {'name': 'impressionsClickThroughRate'}, {'name': 'views'},
                {'name': 'uniqueViewers'}, {'name': 'averageViewDuration'},
                {'name': 'watchTime'}, {'name': 'likes'}, {'name': 'comments'},
                {'name': 'shares'}, {'name': 'subscribersGained'}, {'name': 'subscribersLost'}
            ]
        }
        
        auth.create_youtube_service.side_effect = [data_service, analytics_service]
        
        return {
            'auth': auth,
            'session': session,
            'data_service': data_service,
            'analytics_service': analytics_service
        }
    
    def test_full_ingestion_workflow(self, mock_full_setup):
        """Test complete ingestion workflow from start to finish."""
        mocks = mock_full_setup
        
        with patch('src.ingestion.youtube_data.get_db_session', return_value=mocks['session']):
            ingester = YouTubeDataIngester(mocks['auth'])
            
            start_date = date(2024, 1, 1)
            end_date = date(2024, 1, 1)
            
            result = ingester.ingest_data(start_date, end_date)
            
            # Verify successful ingestion
            assert result.success is True
            assert result.videos_processed == 1
            assert result.metrics_saved == 1
            assert len(result.errors) == 0
            
            # Verify database operations
            assert mocks['session'].add.call_count >= 2  # At least video and metrics
            assert mocks['session'].commit.call_count >= 1
            
            # Verify API calls were made
            mocks['data_service'].search.assert_called()
            mocks['data_service'].videos.assert_called()
            mocks['analytics_service'].reports.assert_called()

if __name__ == "__main__":
    pytest.main([__file__])