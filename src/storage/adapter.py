#!/usr/bin/env python3
"""
Storage Adapter

Provides a unified interface that automatically chooses between database and local storage.
"""

from typing import List, Optional, Dict, Any
from ..utils.config import get_config
from .local_storage import (
    LocalStorage, VideoData, VideoMetricsData, 
    ChannelMetricsData, InsightData, get_storage, init_storage
)

class StorageAdapter:
    """Unified storage adapter that switches between database and local storage."""
    
    def __init__(self):
        self.config = get_config()
        self._storage = None
        self._db_session = None
        
        if self.config.use_local_storage:
            self._storage = init_storage(self.config.local_storage_dir)
        else:
            # Import database modules only if needed
            try:
                from ..database.models import get_db_session
                self._db_session = get_db_session()
            except ImportError:
                # Fallback to local storage if database modules are not available
                self._storage = init_storage(self.config.local_storage_dir)
    
    @property
    def is_local_storage(self) -> bool:
        """Check if using local storage."""
        return self._storage is not None
    
    # Video operations
    def save_video(self, video_data: Dict[str, Any]) -> None:
        """Save video data."""
        if self.is_local_storage:
            video = VideoData(
                video_id=video_data['video_id'],
                channel_id=video_data['channel_id'],
                title=video_data['title'],
                description=video_data.get('description', ''),
                published_at=video_data.get('published_at', ''),
                thumbnail_url=video_data.get('thumbnail_url', ''),
                duration=video_data.get('duration', ''),
                tags=video_data.get('tags', []),
                category_id=video_data.get('category_id', '')
            )
            self._storage.save_video(video)
        else:
            # Database implementation would go here
            from ..database.models import Video
            video = Video(**video_data)
            self._db_session.add(video)
            self._db_session.commit()
    
    def get_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get video data by ID."""
        if self.is_local_storage:
            video = self._storage.get_video(video_id)
            return video.__dict__ if video else None
        else:
            # Database implementation would go here
            from ..database.models import Video
            video = self._db_session.query(Video).filter(Video.video_id == video_id).first()
            return video.__dict__ if video else None
    
    def get_all_videos(self) -> List[Dict[str, Any]]:
        """Get all videos."""
        if self.is_local_storage:
            videos = self._storage.get_all_videos()
            return [video.__dict__ for video in videos]
        else:
            # Database implementation would go here
            from ..database.models import Video
            videos = self._db_session.query(Video).all()
            return [video.__dict__ for video in videos]
    
    def get_videos_by_channel(self, channel_id: str) -> List[Dict[str, Any]]:
        """Get videos by channel ID."""
        if self.is_local_storage:
            videos = self._storage.get_videos_by_channel(channel_id)
            return [video.__dict__ for video in videos]
        else:
            # Database implementation would go here
            from ..database.models import Video
            videos = self._db_session.query(Video).filter(Video.channel_id == channel_id).all()
            return [video.__dict__ for video in videos]
    
    # Video metrics operations
    def save_video_metrics(self, metrics_data: Dict[str, Any]) -> None:
        """Save video metrics."""
        if self.is_local_storage:
            metrics = VideoMetricsData(
                video_id=metrics_data['video_id'],
                views=metrics_data.get('views', 0),
                likes=metrics_data.get('likes', 0),
                comments=metrics_data.get('comments', 0),
                shares=metrics_data.get('shares', 0),
                watch_time_minutes=metrics_data.get('watch_time_minutes', 0.0),
                average_view_duration=metrics_data.get('average_view_duration', 0.0),
                click_through_rate=metrics_data.get('click_through_rate', 0.0),
                subscriber_gain=metrics_data.get('subscriber_gain', 0),
                revenue=metrics_data.get('revenue', 0.0),
                date_recorded=metrics_data.get('date_recorded', '')
            )
            self._storage.save_video_metrics(metrics)
        else:
            # Database implementation would go here
            from ..database.models import VideoMetrics
            metrics = VideoMetrics(**metrics_data)
            self._db_session.add(metrics)
            self._db_session.commit()
    
    def get_video_metrics(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get video metrics by video ID."""
        if self.is_local_storage:
            metrics = self._storage.get_video_metrics(video_id)
            return metrics.__dict__ if metrics else None
        else:
            # Database implementation would go here
            from ..database.models import VideoMetrics
            metrics = self._db_session.query(VideoMetrics).filter(VideoMetrics.video_id == video_id).first()
            return metrics.__dict__ if metrics else None
    
    def get_all_video_metrics(self) -> List[Dict[str, Any]]:
        """Get all video metrics."""
        if self.is_local_storage:
            metrics = self._storage.get_all_video_metrics()
            return [metric.__dict__ for metric in metrics]
        else:
            # Database implementation
            from ..database.models import VideoMetrics
            metrics = self._db_session.query(VideoMetrics).all()
            return [metric.__dict__ for metric in metrics]
    
    # Channel metrics operations
    def save_channel_metrics(self, metrics_data: Dict[str, Any]) -> None:
        """Save channel metrics."""
        if self.is_local_storage:
            metrics = ChannelMetricsData(
                channel_id=metrics_data['channel_id'],
                subscribers=metrics_data.get('subscribers', 0),
                total_views=metrics_data.get('total_views', 0),
                total_videos=metrics_data.get('total_videos', 0),
                average_views_per_video=metrics_data.get('average_views_per_video', 0.0),
                engagement_rate=metrics_data.get('engagement_rate', 0.0),
                upload_frequency=metrics_data.get('upload_frequency', 0.0),
                date_recorded=metrics_data.get('date_recorded', '')
            )
            self._storage.save_channel_metrics(metrics)
        else:
            # Database implementation would go here
            from ..database.models import ChannelMetrics
            metrics = ChannelMetrics(**metrics_data)
            self._db_session.add(metrics)
            self._db_session.commit()
    
    def get_channel_metrics(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel metrics by channel ID."""
        if self.is_local_storage:
            metrics = self._storage.get_channel_metrics(channel_id)
            return metrics.__dict__ if metrics else None
        else:
            # Database implementation would go here
            from ..database.models import ChannelMetrics
            metrics = self._db_session.query(ChannelMetrics).filter(ChannelMetrics.channel_id == channel_id).first()
            return metrics.__dict__ if metrics else None
    
    # Insights operations
    def save_insight(self, insight_data: Dict[str, Any]) -> None:
        """Save AI insight."""
        if self.is_local_storage:
            insight = InsightData(
                insight_id=insight_data['insight_id'],
                video_id=insight_data.get('video_id', ''),
                channel_id=insight_data.get('channel_id', ''),
                insight_type=insight_data.get('insight_type', ''),
                content=insight_data.get('content', ''),
                confidence_score=insight_data.get('confidence_score', 0.0),
                created_at=insight_data.get('created_at', ''),
                metadata=insight_data.get('metadata', {})
            )
            self._storage.save_insight(insight)
        else:
            # Database implementation would go here
            from ..database.models import Insight
            insight = Insight(**insight_data)
            self._db_session.add(insight)
            self._db_session.commit()
    
    def get_insights_by_video(self, video_id: str) -> List[Dict[str, Any]]:
        """Get insights by video ID."""
        if self.is_local_storage:
            insights = self._storage.get_insights_by_video(video_id)
            return [insight.__dict__ for insight in insights]
        else:
            # Database implementation would go here
            from ..database.models import Insight
            insights = self._db_session.query(Insight).filter(Insight.video_id == video_id).all()
            return [insight.__dict__ for insight in insights]
    
    def get_insights_by_channel(self, channel_id: str) -> List[Dict[str, Any]]:
        """Get insights by channel ID."""
        if self.is_local_storage:
            insights = self._storage.get_insights_by_channel(channel_id)
            return [insight.__dict__ for insight in insights]
        else:
            # Database implementation would go here
            from ..database.models import Insight
            insights = self._db_session.query(Insight).filter(Insight.channel_id == channel_id).all()
            return [insight.__dict__ for insight in insights]
    
    def get_all_insights(self) -> List[Dict[str, Any]]:
        """Get all insights."""
        if self.is_local_storage:
            insights = self._storage.get_all_insights()
            return [insight.__dict__ for insight in insights]
        else:
            # Database implementation would go here
            from ..database.models import Insight
            insights = self._db_session.query(Insight).all()
            return [insight.__dict__ for insight in insights]
    
    # Utility operations
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        if self.is_local_storage:
            return {
                'storage_type': 'local_files',
                'storage_location': str(self._storage.storage_dir),
                **self._storage.get_storage_stats()
            }
        else:
            return {
                'storage_type': 'database',
                'database_url': self.config.database_url
            }
    
    def clear_all_data(self) -> None:
        """Clear all stored data."""
        if self.is_local_storage:
            self._storage.clear_all_data()
        else:
            # Database implementation would go here
            from ..database.models import Video, VideoMetrics, ChannelMetrics, Insight
            self._db_session.query(Video).delete()
            self._db_session.query(VideoMetrics).delete()
            self._db_session.query(ChannelMetrics).delete()
            self._db_session.query(Insight).delete()
            self._db_session.commit()

# Global adapter instance
_adapter: Optional[StorageAdapter] = None

def get_storage_adapter() -> StorageAdapter:
    """Get the global storage adapter instance."""
    global _adapter
    if _adapter is None:
        _adapter = StorageAdapter()
    return _adapter