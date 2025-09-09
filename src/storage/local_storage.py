#!/usr/bin/env python3
"""
Local File Storage Implementation

Provides JSON-based file storage for YouTube analytics data.
"""

import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import threading
from dataclasses import dataclass, asdict
from ..utils.config import get_config

@dataclass
class VideoData:
    """Video data structure."""
    video_id: str
    channel_id: str
    title: str
    description: str = ""
    published_at: str = ""
    thumbnail_url: str = ""
    duration: str = ""
    tags: List[str] = None
    category_id: str = ""
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

@dataclass
class VideoMetricsData:
    """Video metrics data structure."""
    video_id: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    watch_time_minutes: float = 0.0
    average_view_duration: float = 0.0
    click_through_rate: float = 0.0
    subscriber_gain: int = 0
    revenue: float = 0.0
    date_recorded: str = ""

@dataclass
class ChannelMetricsData:
    """Channel metrics data structure."""
    channel_id: str
    subscribers: int = 0
    total_views: int = 0
    total_videos: int = 0
    average_views_per_video: float = 0.0
    engagement_rate: float = 0.0
    upload_frequency: float = 0.0
    date_recorded: str = ""

@dataclass
class InsightData:
    """AI insight data structure."""
    insight_id: str
    video_id: str = ""
    channel_id: str = ""
    insight_type: str = ""
    content: str = ""
    confidence_score: float = 0.0
    created_at: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class LocalStorage:
    """Local file-based storage for YouTube analytics data."""
    
    def __init__(self, storage_dir: str = "data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self._lock = threading.RLock()
        
        # Create subdirectories
        (self.storage_dir / "videos").mkdir(exist_ok=True)
        (self.storage_dir / "metrics").mkdir(exist_ok=True)
        (self.storage_dir / "channels").mkdir(exist_ok=True)
        (self.storage_dir / "insights").mkdir(exist_ok=True)
    
    def _serialize_datetime(self, obj):
        """JSON serializer for datetime objects."""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Load data from JSON file."""
        if not file_path.exists():
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading {file_path}: {e}")
            return {}
    
    def _save_json_file(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Save data to JSON file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=self._serialize_datetime)
        except IOError as e:
            print(f"Error saving {file_path}: {e}")
    
    # Video operations
    def save_video(self, video: VideoData) -> None:
        """Save video data."""
        with self._lock:
            file_path = self.storage_dir / "videos" / f"{video.video_id}.json"
            self._save_json_file(file_path, asdict(video))
    
    def get_video(self, video_id: str) -> Optional[VideoData]:
        """Get video data by ID."""
        with self._lock:
            file_path = self.storage_dir / "videos" / f"{video_id}.json"
            data = self._load_json_file(file_path)
            return VideoData(**data) if data else None
    
    def get_all_videos(self) -> List[VideoData]:
        """Get all videos."""
        with self._lock:
            videos = []
            videos_dir = self.storage_dir / "videos"
            for file_path in videos_dir.glob("*.json"):
                data = self._load_json_file(file_path)
                if data:
                    videos.append(VideoData(**data))
            return videos
    
    def get_videos_by_channel(self, channel_id: str) -> List[VideoData]:
        """Get videos by channel ID."""
        all_videos = self.get_all_videos()
        return [video for video in all_videos if video.channel_id == channel_id]
    
    # Video metrics operations
    def save_video_metrics(self, metrics: VideoMetricsData) -> None:
        """Save video metrics."""
        with self._lock:
            file_path = self.storage_dir / "metrics" / f"{metrics.video_id}_metrics.json"
            self._save_json_file(file_path, asdict(metrics))
    
    def get_video_metrics(self, video_id: str) -> Optional[VideoMetricsData]:
        """Get video metrics by video ID."""
        with self._lock:
            file_path = self.storage_dir / "metrics" / f"{video_id}_metrics.json"
            data = self._load_json_file(file_path)
            return VideoMetricsData(**data) if data else None
    
    def get_all_video_metrics(self) -> List[VideoMetricsData]:
        """Get all video metrics."""
        with self._lock:
            metrics = []
            metrics_dir = self.storage_dir / "metrics"
            for file_path in metrics_dir.glob("*_metrics.json"):
                data = self._load_json_file(file_path)
                if data:
                    metrics.append(VideoMetricsData(**data))
            return metrics
    
    # Channel metrics operations
    def save_channel_metrics(self, metrics: ChannelMetricsData) -> None:
        """Save channel metrics."""
        with self._lock:
            file_path = self.storage_dir / "channels" / f"{metrics.channel_id}_metrics.json"
            self._save_json_file(file_path, asdict(metrics))
    
    def get_channel_metrics(self, channel_id: str) -> Optional[ChannelMetricsData]:
        """Get channel metrics by channel ID."""
        with self._lock:
            file_path = self.storage_dir / "channels" / f"{channel_id}_metrics.json"
            data = self._load_json_file(file_path)
            return ChannelMetricsData(**data) if data else None
    
    def get_all_channel_metrics(self) -> List[ChannelMetricsData]:
        """Get all channel metrics."""
        with self._lock:
            metrics = []
            channels_dir = self.storage_dir / "channels"
            for file_path in channels_dir.glob("*_metrics.json"):
                data = self._load_json_file(file_path)
                if data:
                    metrics.append(ChannelMetricsData(**data))
            return metrics
    
    # Insights operations
    def save_insight(self, insight: InsightData) -> None:
        """Save AI insight."""
        with self._lock:
            file_path = self.storage_dir / "insights" / f"{insight.insight_id}.json"
            self._save_json_file(file_path, asdict(insight))
    
    def get_insight(self, insight_id: str) -> Optional[InsightData]:
        """Get insight by ID."""
        with self._lock:
            file_path = self.storage_dir / "insights" / f"{insight_id}.json"
            data = self._load_json_file(file_path)
            return InsightData(**data) if data else None
    
    def get_insights_by_video(self, video_id: str) -> List[InsightData]:
        """Get insights by video ID."""
        all_insights = self.get_all_insights()
        return [insight for insight in all_insights if insight.video_id == video_id]
    
    def get_insights_by_channel(self, channel_id: str) -> List[InsightData]:
        """Get insights by channel ID."""
        all_insights = self.get_all_insights()
        return [insight for insight in all_insights if insight.channel_id == channel_id]
    
    def get_all_insights(self) -> List[InsightData]:
        """Get all insights."""
        with self._lock:
            insights = []
            insights_dir = self.storage_dir / "insights"
            for file_path in insights_dir.glob("*.json"):
                data = self._load_json_file(file_path)
                if data:
                    insights.append(InsightData(**data))
            return insights
    
    # Utility operations
    def clear_all_data(self) -> None:
        """Clear all stored data."""
        with self._lock:
            for subdir in ["videos", "metrics", "channels", "insights"]:
                dir_path = self.storage_dir / subdir
                for file_path in dir_path.glob("*.json"):
                    file_path.unlink()
    
    def get_storage_stats(self) -> Dict[str, int]:
        """Get storage statistics."""
        with self._lock:
            stats = {}
            for subdir in ["videos", "metrics", "channels", "insights"]:
                dir_path = self.storage_dir / subdir
                stats[subdir] = len(list(dir_path.glob("*.json")))
            return stats

# Global storage instance
_storage: Optional[LocalStorage] = None

def get_storage() -> LocalStorage:
    """Get the global storage instance."""
    global _storage
    if _storage is None:
        _storage = LocalStorage()
    return _storage

def init_storage(storage_dir: str = "data") -> LocalStorage:
    """Initialize storage with custom directory."""
    global _storage
    _storage = LocalStorage(storage_dir)
    return _storage