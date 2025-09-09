#!/usr/bin/env python3
"""
Unit tests for Gemini AI integration module
"""

import pytest
import json
from datetime import datetime, date
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.gemini_client import (
    GeminiClient, ChannelInsightRequest, VideoInsightRequest,
    ChannelInsightResponse, VideoInsightResponse, get_gemini_client
)
from src.database.models import Insight

class TestInsightDataClasses:
    """Test cases for insight request/response dataclasses."""
    
    def test_channel_insight_request_creation(self):
        """Test ChannelInsightRequest creation."""
        aggregates = {
            "impressions": 100000,
            "views": 50000,
            "ctr": 0.05,
            "avg_view_duration_sec": 120,
            "subs_change": 50
        }
        
        top_videos = [
            {
                "video_id": "video_123",
                "title": "Test Video 1",
                "impressions": 50000,
                "ctr": 0.06,
                "views": 3000,
                "watch_time": 360000
            }
        ]
        
        request = ChannelInsightRequest(
            channel_id="test_channel_123",
            date_range="2024-01-01 to 2024-01-31",
            aggregates=aggregates,
            top_videos=top_videos
        )
        
        assert request.channel_id == "test_channel_123"
        assert request.date_range == "2024-01-01 to 2024-01-31"
        assert request.aggregates == aggregates
        assert request.top_videos == top_videos
    
    def test_video_insight_request_creation(self):
        """Test VideoInsightRequest creation."""
        request = VideoInsightRequest(
            video_id="video_123",
            title="Test Video",
            impressions=10000,
            views=500,
            ctr=0.05,
            avg_view_duration_sec=120,
            watch_time=60000,
            published_at="2024-01-01"
        )
        
        assert request.video_id == "video_123"
        assert request.title == "Test Video"
        assert request.impressions == 10000
        assert request.views == 500
        assert request.ctr == 0.05
        assert request.avg_view_duration_sec == 120
        assert request.watch_time == 60000
        assert request.published_at == "2024-01-01"
    
    def test_channel_insight_response_creation(self):
        """Test ChannelInsightResponse creation."""
        response = ChannelInsightResponse(
            action_type="optimize_upload_schedule",
            priority="high",
            confidence=0.85,
            rationale="Upload consistency can improve audience retention",
            recommended_videos=["video_123", "video_456"]
        )
        
        assert response.action_type == "optimize_upload_schedule"
        assert response.priority == "high"
        assert response.confidence == 0.85
        assert response.rationale == "Upload consistency can improve audience retention"
        assert response.recommended_videos == ["video_123", "video_456"]
    
    def test_video_insight_response_creation(self):
        """Test VideoInsightResponse creation."""
        details = {
            "suggested_title": "Improved Video Title",
            "suggested_tags": ["tag1", "tag2"]
        }
        
        response = VideoInsightResponse(
            action_type="optimize_title",
            confidence=0.75,
            rationale="Current title has low CTR potential",
            details=details
        )
        
        assert response.action_type == "optimize_title"
        assert response.confidence == 0.75
        assert response.rationale == "Current title has low CTR potential"
        assert response.details == details

class TestGeminiClient:
    """Test cases for GeminiClient class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock()
        config.gemini_api_key = "test_api_key_123"
        config.gemini_model = "gemini-pro"
        config.gemini_temperature = 0.1
        config.gemini_max_tokens = 1000
        return config
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        return session
    
    @pytest.fixture
    def mock_genai(self):
        """Create a mock Google Generative AI client."""
        with patch('src.ai.gemini_client.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            # Mock successful response
            mock_response = Mock()
            mock_response.text = json.dumps([
                {
                    "action_type": "optimize_upload_schedule",
                    "priority": "high",
                    "confidence": 0.85,
                    "rationale": "Consistent upload schedule improves audience retention",
                    "recommended_videos": ["video_123"]
                }
            ])
            
            mock_model.generate_content.return_value = mock_response
            
            yield mock_genai
    
    def test_gemini_client_initialization(self, mock_config, mock_db_session):
        """Test GeminiClient initialization."""
        with patch('src.ai.gemini_client.get_db_session', return_value=mock_db_session):
            with patch('src.ai.gemini_client.genai') as mock_genai:
                client = GeminiClient(mock_config)
                
                assert client.config == mock_config
                assert client.db_session == mock_db_session
                mock_genai.configure.assert_called_once_with(api_key="test_api_key_123")
    
    def test_gemini_client_initialization_no_api_key(self, mock_db_session):
        """Test GeminiClient initialization without API key."""
        config = Mock()
        config.gemini_api_key = None
        
        with patch('src.ai.gemini_client.get_db_session', return_value=mock_db_session):
            with pytest.raises(ValueError, match="Gemini API key is required"):
                GeminiClient(config)
    
    def test_validate_channel_response_valid(self, mock_config, mock_db_session):
        """Test validation of valid channel response."""
        with patch('src.ai.gemini_client.get_db_session', return_value=mock_db_session):
            with patch('src.ai.gemini_client.genai'):
                client = GeminiClient(mock_config)
                
                valid_response = [
                    {
                        "action_type": "optimize_upload_schedule",
                        "priority": "high",
                        "confidence": 0.85,
                        "rationale": "Test rationale",
                        "recommended_videos": ["video_123"]
                    }
                ]
                
                # Should not raise an exception
                client._validate_channel_response(valid_response)
    
    def test_validate_channel_response_invalid(self, mock_config, mock_db_session):
        """Test validation of invalid channel response."""
        with patch('src.ai.gemini_client.get_db_session', return_value=mock_db_session):
            with patch('src.ai.gemini_client.genai'):
                client = GeminiClient(mock_config)
                
                # Missing required field
                invalid_response = [
                    {
                        "action_type": "optimize_upload_schedule",
                        "priority": "high",
                        # Missing confidence and rationale
                        "recommended_videos": ["video_123"]
                    }
                ]
                
                with pytest.raises(ValueError, match="Invalid channel insight response"):
                    client._validate_channel_response(invalid_response)
    
    def test_validate_video_response_valid(self, mock_config, mock_db_session):
        """Test validation of valid video response."""
        with patch('src.ai.gemini_client.get_db_session', return_value=mock_db_session):
            with patch('src.ai.gemini_client.genai'):
                client = GeminiClient(mock_config)
                
                valid_response = {
                    "action_type": "optimize_title",
                    "confidence": 0.75,
                    "rationale": "Current title has low CTR potential",
                    "details": {
                        "suggested_title": "Better Title"
                    }
                }
                
                # Should not raise an exception
                client._validate_video_response(valid_response)
    
    def test_validate_video_response_invalid(self, mock_config, mock_db_session):
        """Test validation of invalid video response."""
        with patch('src.ai.gemini_client.get_db_session', return_value=mock_db_session):
            with patch('src.ai.gemini_client.genai'):
                client = GeminiClient(mock_config)
                
                # Invalid confidence value
                invalid_response = {
                    "action_type": "optimize_title",
                    "confidence": 1.5,  # Should be between 0 and 1
                    "rationale": "Test rationale"
                }
                
                with pytest.raises(ValueError, match="Invalid video insight response"):
                    client._validate_video_response(invalid_response)
    
    @patch('src.ai.gemini_client.sleep')
    def test_generate_channel_insights_success(self, mock_sleep, mock_config, mock_db_session, mock_genai):
        """Test successful channel insights generation."""
        with patch('src.ai.gemini_client.get_db_session', return_value=mock_db_session):
            client = GeminiClient(mock_config)
            
            request = ChannelInsightRequest(
                channel_id="test_channel_123",
                date_range="2024-01-01 to 2024-01-31",
                aggregates={
                    "impressions": 100000,
                    "views": 50000,
                    "ctr": 0.05,
                    "avg_view_duration_sec": 120,
                    "subs_change": 50
                },
                top_videos=[
                    {
                        "video_id": "video_123",
                        "title": "Test Video",
                        "impressions": 50000,
                        "ctr": 0.06,
                        "views": 3000,
                        "watch_time": 360000
                    }
                ]
            )
            
            insights = client.generate_channel_insights(request)
            
            assert len(insights) == 1
            assert insights[0].action_type == "optimize_upload_schedule"
            assert insights[0].priority == "high"
            assert insights[0].confidence == 0.85
    
    @patch('src.ai.gemini_client.sleep')
    def test_generate_channel_insights_retry_on_error(self, mock_sleep, mock_config, mock_db_session):
        """Test retry logic for channel insights generation."""
        with patch('src.ai.gemini_client.get_db_session', return_value=mock_db_session):
            with patch('src.ai.gemini_client.genai') as mock_genai:
                mock_model = Mock()
                mock_genai.GenerativeModel.return_value = mock_model
                
                # First two attempts fail, third succeeds
                mock_model.generate_content.side_effect = [
                    Exception("API Error"),
                    Exception("API Error"),
                    Mock(text=json.dumps([
                        {
                            "action_type": "optimize_upload_schedule",
                            "priority": "high",
                            "confidence": 0.85,
                            "rationale": "Test rationale",
                            "recommended_videos": []
                        }
                    ]))
                ]
                
                client = GeminiClient(mock_config)
                
                request = ChannelInsightRequest(
                    channel_id="test_channel_123",
                    date_range="2024-01-01 to 2024-01-31",
                    aggregates={},
                    top_videos=[]
                )
                
                insights = client.generate_channel_insights(request)
                
                assert len(insights) == 1
                assert mock_sleep.call_count == 2  # Should have slept twice
    
    @patch('src.ai.gemini_client.sleep')
    def test_generate_video_insights_success(self, mock_sleep, mock_config, mock_db_session):
        """Test successful video insights generation."""
        with patch('src.ai.gemini_client.get_db_session', return_value=mock_db_session):
            with patch('src.ai.gemini_client.genai') as mock_genai:
                mock_model = Mock()
                mock_genai.GenerativeModel.return_value = mock_model
                
                mock_response = Mock()
                mock_response.text = json.dumps({
                    "action_type": "optimize_title",
                    "confidence": 0.75,
                    "rationale": "Current title has low CTR potential",
                    "details": {
                        "suggested_title": "Better Title"
                    }
                })
                
                mock_model.generate_content.return_value = mock_response
                
                client = GeminiClient(mock_config)
                
                request = VideoInsightRequest(
                    video_id="video_123",
                    title="Test Video",
                    impressions=10000,
                    views=500,
                    ctr=0.05,
                    avg_view_duration_sec=120,
                    watch_time=60000,
                    published_at="2024-01-01"
                )
                
                insight = client.generate_video_insights(request)
                
                assert insight.action_type == "optimize_title"
                assert insight.confidence == 0.75
                assert insight.rationale == "Current title has low CTR potential"
                assert insight.details["suggested_title"] == "Better Title"
    
    def test_generate_insights_invalid_json(self, mock_config, mock_db_session):
        """Test handling of invalid JSON response."""
        with patch('src.ai.gemini_client.get_db_session', return_value=mock_db_session):
            with patch('src.ai.gemini_client.genai') as mock_genai:
                mock_model = Mock()
                mock_genai.GenerativeModel.return_value = mock_model
                
                # Return invalid JSON
                mock_response = Mock()
                mock_response.text = "Invalid JSON response"
                mock_model.generate_content.return_value = mock_response
                
                client = GeminiClient(mock_config)
                
                request = ChannelInsightRequest(
                    channel_id="test_channel_123",
                    date_range="2024-01-01 to 2024-01-31",
                    aggregates={},
                    top_videos=[]
                )
                
                with patch('src.ai.gemini_client.sleep'):  # Speed up test
                    with pytest.raises(ValueError, match="Failed to generate channel insights"):
                        client.generate_channel_insights(request)
    
    def test_save_channel_insights_to_db(self, mock_config, mock_db_session):
        """Test saving channel insights to database."""
        with patch('src.ai.gemini_client.get_db_session', return_value=mock_db_session):
            with patch('src.ai.gemini_client.genai'):
                client = GeminiClient(mock_config)
                
                insights = [
                    ChannelInsightResponse(
                        action_type="optimize_upload_schedule",
                        priority="high",
                        confidence=0.85,
                        rationale="Test rationale",
                        recommended_videos=["video_123"]
                    )
                ]
                
                channel_id = "test_channel_123"
                
                client.save_channel_insights_to_db(insights, channel_id)
                
                # Verify insight was added to database
                mock_db_session.add.assert_called_once()
                mock_db_session.commit.assert_called_once()
                
                # Check the insight object
                added_insight = mock_db_session.add.call_args[0][0]
                assert isinstance(added_insight, Insight)
                assert added_insight.video_id is None  # Channel-level insight
                assert added_insight.insight_type == "channel"
                assert added_insight.priority == "high"
                assert added_insight.confidence == 0.85
    
    def test_save_video_insights_to_db(self, mock_config, mock_db_session):
        """Test saving video insights to database."""
        with patch('src.ai.gemini_client.get_db_session', return_value=mock_db_session):
            with patch('src.ai.gemini_client.genai'):
                client = GeminiClient(mock_config)
                
                insight = VideoInsightResponse(
                    action_type="optimize_title",
                    confidence=0.75,
                    rationale="Current title has low CTR potential",
                    details={"suggested_title": "Better Title"}
                )
                
                video_id = "video_123"
                
                client.save_video_insights_to_db(insight, video_id)
                
                # Verify insight was added to database
                mock_db_session.add.assert_called_once()
                mock_db_session.commit.assert_called_once()
                
                # Check the insight object
                added_insight = mock_db_session.add.call_args[0][0]
                assert isinstance(added_insight, Insight)
                assert added_insight.video_id == "video_123"
                assert added_insight.insight_type == "video"
                assert added_insight.confidence == 0.75
    
    def test_database_error_handling(self, mock_config, mock_db_session):
        """Test database error handling."""
        with patch('src.ai.gemini_client.get_db_session', return_value=mock_db_session):
            with patch('src.ai.gemini_client.genai'):
                client = GeminiClient(mock_config)
                
                # Mock database error
                mock_db_session.commit.side_effect = Exception("Database error")
                
                insight = VideoInsightResponse(
                    action_type="optimize_title",
                    confidence=0.75,
                    rationale="Test rationale",
                    details={}
                )
                
                # Should handle the error gracefully
                with pytest.raises(Exception, match="Database error"):
                    client.save_video_insights_to_db(insight, "video_123")
                
                # Verify rollback was called
                mock_db_session.rollback.assert_called_once()

class TestPromptTemplates:
    """Test prompt template generation."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock()
        config.gemini_api_key = "test_api_key_123"
        config.gemini_model = "gemini-pro"
        config.gemini_temperature = 0.1
        config.gemini_max_tokens = 1000
        return config
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock()
    
    def test_channel_prompt_generation(self, mock_config, mock_db_session):
        """Test channel insights prompt generation."""
        with patch('src.ai.gemini_client.get_db_session', return_value=mock_db_session):
            with patch('src.ai.gemini_client.genai'):
                client = GeminiClient(mock_config)
                
                request = ChannelInsightRequest(
                    channel_id="test_channel_123",
                    date_range="2024-01-01 to 2024-01-31",
                    aggregates={
                        "impressions": 100000,
                        "views": 50000,
                        "ctr": 0.05,
                        "avg_view_duration_sec": 120,
                        "subs_change": 50
                    },
                    top_videos=[
                        {
                            "video_id": "video_123",
                            "title": "Test Video",
                            "impressions": 50000,
                            "ctr": 0.06,
                            "views": 3000,
                            "watch_time": 360000
                        }
                    ]
                )
                
                prompt = client._create_channel_prompt(request)
                
                # Verify prompt contains expected elements
                assert "Channel summary JSON" in prompt
                assert "test_channel_123" in prompt
                assert "2024-01-01 to 2024-01-31" in prompt
                assert "100000" in prompt  # impressions
                assert "video_123" in prompt
                assert "Return JSON only" in prompt
    
    def test_video_prompt_generation(self, mock_config, mock_db_session):
        """Test video insights prompt generation."""
        with patch('src.ai.gemini_client.get_db_session', return_value=mock_db_session):
            with patch('src.ai.gemini_client.genai'):
                client = GeminiClient(mock_config)
                
                request = VideoInsightRequest(
                    video_id="video_123",
                    title="Test Video",
                    impressions=10000,
                    views=500,
                    ctr=0.05,
                    avg_view_duration_sec=120,
                    watch_time=60000,
                    published_at="2024-01-01"
                )
                
                prompt = client._create_video_prompt(request)
                
                # Verify prompt contains expected elements
                assert "Video metrics" in prompt
                assert "video_123" in prompt
                assert "Test Video" in prompt
                assert "10000" in prompt  # impressions
                assert "500" in prompt  # views
                assert "Return JSON only" in prompt

class TestGeminiUtilities:
    """Test utility functions for Gemini module."""
    
    @patch('src.ai.gemini_client.get_db_session')
    def test_get_gemini_client_function(self, mock_get_db_session):
        """Test get_gemini_client utility function."""
        mock_session = Mock()
        mock_get_db_session.return_value = mock_session
        
        mock_config = Mock()
        mock_config.gemini_api_key = "test_api_key"
        
        with patch('src.ai.gemini_client.get_config', return_value=mock_config):
            with patch('src.ai.gemini_client.genai'):
                client = get_gemini_client()
                
                assert isinstance(client, GeminiClient)
                assert client.config == mock_config
    
    @patch('src.ai.gemini_client.get_db_session')
    def test_get_gemini_client_no_api_key(self, mock_get_db_session):
        """Test get_gemini_client with no API key."""
        mock_session = Mock()
        mock_get_db_session.return_value = mock_session
        
        mock_config = Mock()
        mock_config.gemini_api_key = None
        
        with patch('src.ai.gemini_client.get_config', return_value=mock_config):
            with pytest.raises(ValueError, match="Gemini API key is required"):
                get_gemini_client()

class TestGeminiIntegration:
    """Integration tests for Gemini AI functionality."""
    
    @pytest.fixture
    def mock_full_setup(self):
        """Set up mocks for full integration test."""
        config = Mock()
        config.gemini_api_key = "test_api_key_123"
        config.gemini_model = "gemini-pro"
        config.gemini_temperature = 0.1
        config.gemini_max_tokens = 1000
        
        session = Mock()
        session.add = Mock()
        session.commit = Mock()
        
        return {
            'config': config,
            'session': session
        }
    
    def test_full_channel_insights_workflow(self, mock_full_setup):
        """Test complete channel insights workflow."""
        mocks = mock_full_setup
        
        with patch('src.ai.gemini_client.get_db_session', return_value=mocks['session']):
            with patch('src.ai.gemini_client.genai') as mock_genai:
                # Mock successful API response
                mock_model = Mock()
                mock_genai.GenerativeModel.return_value = mock_model
                
                mock_response = Mock()
                mock_response.text = json.dumps([
                    {
                        "action_type": "optimize_upload_schedule",
                        "priority": "high",
                        "confidence": 0.85,
                        "rationale": "Consistent upload schedule improves audience retention",
                        "recommended_videos": ["video_123"]
                    },
                    {
                        "action_type": "improve_thumbnails",
                        "priority": "medium",
                        "confidence": 0.70,
                        "rationale": "Thumbnail CTR is below average",
                        "recommended_videos": ["video_456"]
                    }
                ])
                
                mock_model.generate_content.return_value = mock_response
                
                client = GeminiClient(mocks['config'])
                
                # Create request
                request = ChannelInsightRequest(
                    channel_id="test_channel_123",
                    date_range="2024-01-01 to 2024-01-31",
                    aggregates={
                        "impressions": 100000,
                        "views": 50000,
                        "ctr": 0.05,
                        "avg_view_duration_sec": 120,
                        "subs_change": 50
                    },
                    top_videos=[]
                )
                
                # Generate insights
                insights = client.generate_channel_insights(request)
                
                # Verify insights
                assert len(insights) == 2
                assert insights[0].action_type == "optimize_upload_schedule"
                assert insights[1].action_type == "improve_thumbnails"
                
                # Save to database
                client.save_channel_insights_to_db(insights, "test_channel_123")
                
                # Verify database operations
                assert mocks['session'].add.call_count == 2
                assert mocks['session'].commit.call_count == 1
    
    def test_full_video_insights_workflow(self, mock_full_setup):
        """Test complete video insights workflow."""
        mocks = mock_full_setup
        
        with patch('src.ai.gemini_client.get_db_session', return_value=mocks['session']):
            with patch('src.ai.gemini_client.genai') as mock_genai:
                # Mock successful API response
                mock_model = Mock()
                mock_genai.GenerativeModel.return_value = mock_model
                
                mock_response = Mock()
                mock_response.text = json.dumps({
                    "action_type": "optimize_title",
                    "confidence": 0.75,
                    "rationale": "Current title has low CTR potential based on keyword analysis",
                    "details": {
                        "suggested_title": "How to Master YouTube Analytics in 2024",
                        "suggested_tags": ["youtube", "analytics", "2024", "tutorial"]
                    }
                })
                
                mock_model.generate_content.return_value = mock_response
                
                client = GeminiClient(mocks['config'])
                
                # Create request
                request = VideoInsightRequest(
                    video_id="video_123",
                    title="YouTube Analytics Tutorial",
                    impressions=10000,
                    views=500,
                    ctr=0.05,
                    avg_view_duration_sec=120,
                    watch_time=60000,
                    published_at="2024-01-01"
                )
                
                # Generate insight
                insight = client.generate_video_insights(request)
                
                # Verify insight
                assert insight.action_type == "optimize_title"
                assert insight.confidence == 0.75
                assert "suggested_title" in insight.details
                assert "suggested_tags" in insight.details
                
                # Save to database
                client.save_video_insights_to_db(insight, "video_123")
                
                # Verify database operations
                assert mocks['session'].add.call_count == 1
                assert mocks['session'].commit.call_count == 1

if __name__ == "__main__":
    pytest.main([__file__])