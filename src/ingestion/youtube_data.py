#!/usr/bin/env python3
"""
YouTube Data Ingestion Module

Fetches data from YouTube Data API and YouTube Analytics API.
"""

import time
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from googleapiclient.errors import HttpError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..auth.youtube_auth import get_authenticator
from ..storage import get_storage_adapter
from ..utils.config import get_config
from ..database.models import get_db_session, APIQuota, Video, VideoMetrics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class IngestionResult:
    """Result of data ingestion operation."""
    success: bool
    videos_processed: int
    metrics_updated: int
    errors: List[str]
    quota_used: int

class YouTubeDataIngester:
    """Handles data ingestion from YouTube APIs."""
    
    def __init__(self):
        self.config = get_config()
        self.authenticator = get_authenticator()
        self.quota_used = 0
        
    def _track_quota_usage(self, api_name: str, cost: int):
        """Track API quota usage."""
        self.quota_used += cost
        
        session = get_db_session()
        try:
            today = date.today()
            
            # Get or create quota record
            quota_record = session.query(APIQuota).filter_by(
                api_name=api_name,
                date=today
            ).first()
            
            if quota_record:
                quota_record.quota_used += cost
            else:
                quota_record = APIQuota(
                    api_name=api_name,
                    date=today,
                    quota_used=cost,
                    quota_limit=self.config.youtube_api_quota_limit
                )
                session.add(quota_record)
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Error tracking quota usage: {e}")
            session.rollback()
        finally:
            session.close()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(HttpError)
    )
    def _make_api_request(self, request, quota_cost: int = 1):
        """Make API request with retry logic and quota tracking."""
        try:
            response = request.execute()
            self._track_quota_usage("youtube_data", quota_cost)
            return response
        except HttpError as e:
            if e.resp.status == 403:  # Quota exceeded
                logger.error(f"API quota exceeded: {e}")
                raise
            elif e.resp.status == 429:  # Rate limit
                logger.warning(f"Rate limit hit, retrying: {e}")
                time.sleep(2)
                raise
            else:
                logger.error(f"API error: {e}")
                raise
    
    def get_channel_info(self) -> Optional[Dict[str, Any]]:
        """Get authenticated user's channel information."""
        try:
            youtube = self.authenticator.get_youtube_service()
            
            request = youtube.channels().list(
                part="snippet,statistics,contentDetails,brandingSettings",
                mine=True
            )
            
            response = self._make_api_request(request, quota_cost=1)
            
            if response.get("items"):
                return response["items"][0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting channel info: {e}")
            return None
    
    def get_channel_videos(self, channel_id: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Get all videos from a channel."""
        try:
            youtube = self.authenticator.get_youtube_service()
            videos = []
            next_page_token = None
            
            while len(videos) < max_results:
                # Get uploads playlist ID
                request = youtube.channels().list(
                    part="contentDetails",
                    id=channel_id
                )
                response = self._make_api_request(request, quota_cost=1)
                
                if not response.get("items"):
                    break
                
                uploads_playlist_id = response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
                
                # Get videos from uploads playlist
                request = youtube.playlistItems().list(
                    part="snippet,contentDetails",
                    playlistId=uploads_playlist_id,
                    maxResults=min(50, max_results - len(videos)),
                    pageToken=next_page_token
                )
                
                response = self._make_api_request(request, quota_cost=1)
                
                for item in response.get("items", []):
                    video_id = item["contentDetails"]["videoId"]
                    videos.append({
                        "video_id": video_id,
                        "title": item["snippet"]["title"],
                        "description": item["snippet"].get("description", ""),
                        "published_at": datetime.fromisoformat(
                            item["snippet"]["publishedAt"].replace("Z", "+00:00")
                        ),
                        "thumbnail_url": item["snippet"]["thumbnails"].get("maxres", {}).get(
                            "url", item["snippet"]["thumbnails"].get("high", {}).get("url")
                        )
                    })
                
                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break
            
            # Get additional video details
            if videos:
                video_ids = [v["video_id"] for v in videos]
                video_details = self.get_video_details(video_ids)
                
                # Merge details
                for video in videos:
                    details = video_details.get(video["video_id"], {})
                    video.update(details)
            
            return videos
            
        except Exception as e:
            logger.error(f"Error getting channel videos: {e}")
            return []
    
    def get_video_details(self, video_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get detailed information for multiple videos."""
        try:
            youtube = self.authenticator.get_youtube_service()
            video_details = {}
            
            # Process videos in batches of 50 (API limit)
            for i in range(0, len(video_ids), 50):
                batch_ids = video_ids[i:i+50]
                
                request = youtube.videos().list(
                    part="snippet,statistics,contentDetails,status",
                    id=",".join(batch_ids)
                )
                
                response = self._make_api_request(request, quota_cost=1)
                
                for item in response.get("items", []):
                    video_id = item["id"]
                    snippet = item.get("snippet", {})
                    statistics = item.get("statistics", {})
                    content_details = item.get("contentDetails", {})
                    
                    # Parse duration
                    duration_str = content_details.get("duration", "PT0S")
                    duration_seconds = self._parse_duration(duration_str)
                    
                    video_details[video_id] = {
                        "duration_seconds": duration_seconds,
                        "tags": snippet.get("tags", []),
                        "category_id": snippet.get("categoryId"),
                        "default_language": snippet.get("defaultLanguage"),
                        "default_audio_language": snippet.get("defaultAudioLanguage"),
                        "view_count": int(statistics.get("viewCount", 0)),
                        "like_count": int(statistics.get("likeCount", 0)),
                        "comment_count": int(statistics.get("commentCount", 0))
                    }
            
            return video_details
            
        except Exception as e:
            logger.error(f"Error getting video details: {e}")
            return {}
    
    def _parse_duration(self, duration_str: str) -> int:
        """Parse ISO 8601 duration to seconds."""
        import re
        
        # Remove PT prefix
        duration_str = duration_str.replace("PT", "")
        
        # Extract hours, minutes, seconds
        hours = 0
        minutes = 0
        seconds = 0
        
        if "H" in duration_str:
            hours = int(re.search(r'(\d+)H', duration_str).group(1))
        if "M" in duration_str:
            minutes = int(re.search(r'(\d+)M', duration_str).group(1))
        if "S" in duration_str:
            seconds = int(re.search(r'(\d+)S', duration_str).group(1))
        
        return hours * 3600 + minutes * 60 + seconds
    
    def get_video_analytics(self, video_ids: List[str], start_date: date, end_date: date) -> Dict[str, List[Dict[str, Any]]]:
        """Get analytics data for videos."""
        try:
            analytics = self.authenticator.get_youtube_analytics_service()
            video_analytics = {}
            
            # Process videos in smaller batches for analytics API
            for i in range(0, len(video_ids), 10):
                batch_ids = video_ids[i:i+10]
                
                request = analytics.reports().query(
                    ids="channel==MINE",
                    startDate=start_date.strftime("%Y-%m-%d"),
                    endDate=end_date.strftime("%Y-%m-%d"),
                    metrics="impressions,impressionClickThroughRate,views,uniqueViewers,averageViewDuration,watchTime,likes,comments,shares,subscribersGained,subscribersLost",
                    dimensions="day,video",
                    filters=f"video=={','.join(batch_ids)}",
                    sort="day"
                )
                
                response = self._make_api_request(request, quota_cost=5)
                
                # Process response
                headers = response.get("columnHeaders", [])
                rows = response.get("rows", [])
                
                for row in rows:
                    row_data = dict(zip([h["name"] for h in headers], row))
                    video_id = row_data.get("video")
                    
                    if video_id not in video_analytics:
                        video_analytics[video_id] = []
                    
                    video_analytics[video_id].append({
                        "date": datetime.strptime(row_data["day"], "%Y-%m-%d").date(),
                        "impressions": int(row_data.get("impressions", 0)),
                        "impressions_ctr": float(row_data.get("impressionClickThroughRate", 0)),
                        "views": int(row_data.get("views", 0)),
                        "unique_viewers": int(row_data.get("uniqueViewers", 0)),
                        "average_view_duration_seconds": float(row_data.get("averageViewDuration", 0)),
                        "watch_time_minutes": float(row_data.get("watchTime", 0)) / 60,
                        "likes": int(row_data.get("likes", 0)),
                        "comments": int(row_data.get("comments", 0)),
                        "shares": int(row_data.get("shares", 0)),
                        "subscribers_gained": int(row_data.get("subscribersGained", 0)),
                        "subscribers_lost": int(row_data.get("subscribersLost", 0))
                    })
            
            return video_analytics
            
        except Exception as e:
            logger.error(f"Error getting video analytics: {e}")
            return {}
    
    def get_channel_analytics(self, channel_id: str, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get channel-level analytics data."""
        try:
            analytics = self.authenticator.get_youtube_analytics_service()
            
            request = analytics.reports().query(
                ids="channel==MINE",
                startDate=start_date.strftime("%Y-%m-%d"),
                endDate=end_date.strftime("%Y-%m-%d"),
                metrics="views,impressions,watchTime,subscribersGained,subscribersLost",
                dimensions="day",
                sort="day"
            )
            
            response = self._make_api_request(request, quota_cost=5)
            
            # Process response
            headers = response.get("columnHeaders", [])
            rows = response.get("rows", [])
            
            channel_analytics = []
            for row in rows:
                row_data = dict(zip([h["name"] for h in headers], row))
                
                channel_analytics.append({
                    "date": datetime.strptime(row_data["day"], "%Y-%m-%d").date(),
                    "views_gained": int(row_data.get("views", 0)),
                    "total_impressions": int(row_data.get("impressions", 0)),
                    "total_watch_time_minutes": float(row_data.get("watchTime", 0)) / 60,
                    "subscribers_gained": int(row_data.get("subscribersGained", 0)),
                    "subscribers_lost": int(row_data.get("subscribersLost", 0))
                })
            
            return channel_analytics
            
        except Exception as e:
            logger.error(f"Error getting channel analytics: {e}")
            return []
    
    def save_videos_to_db(self, videos: List[Dict[str, Any]], channel_id: str) -> int:
        """Save video data to database."""
        session = get_db_session()
        saved_count = 0
        
        try:
            for video_data in videos:
                # Check if video exists
                existing_video = session.query(Video).filter_by(
                    video_id=video_data["video_id"]
                ).first()
                
                if existing_video:
                    # Update existing video
                    for key, value in video_data.items():
                        if hasattr(existing_video, key):
                            setattr(existing_video, key, value)
                else:
                    # Create new video
                    video = Video(
                        video_id=video_data["video_id"],
                        channel_id=channel_id,
                        title=video_data["title"],
                        description=video_data.get("description", ""),
                        published_at=video_data["published_at"],
                        thumbnail_url=video_data.get("thumbnail_url"),
                        duration_seconds=video_data.get("duration_seconds"),
                        tags=video_data.get("tags", []),
                        category_id=video_data.get("category_id"),
                        default_language=video_data.get("default_language"),
                        default_audio_language=video_data.get("default_audio_language")
                    )
                    session.add(video)
                
                saved_count += 1
            
            session.commit()
            return saved_count
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving videos to database: {e}")
            raise
        finally:
            session.close()
    
    def save_metrics_to_db(self, video_analytics: Dict[str, List[Dict[str, Any]]]) -> int:
        """Save video metrics to database."""
        session = get_db_session()
        saved_count = 0
        
        try:
            for video_id, metrics_list in video_analytics.items():
                # Get video duration for derived metrics
                video = session.query(Video).filter_by(video_id=video_id).first()
                video_duration = video.duration_seconds if video else None
                
                for metrics_data in metrics_list:
                    # Check if metrics exist for this date
                    existing_metrics = session.query(VideoMetrics).filter_by(
                        video_id=video_id,
                        date=metrics_data["date"]
                    ).first()
                    
                    if existing_metrics:
                        # Update existing metrics
                        for key, value in metrics_data.items():
                            if hasattr(existing_metrics, key):
                                setattr(existing_metrics, key, value)
                        existing_metrics.calculate_derived_metrics(video_duration)
                    else:
                        # Create new metrics
                        metrics = VideoMetrics(
                            video_id=video_id,
                            **metrics_data
                        )
                        metrics.calculate_derived_metrics(video_duration)
                        session.add(metrics)
                    
                    saved_count += 1
            
            session.commit()
            return saved_count
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving metrics to database: {e}")
            raise
        finally:
            session.close()
    
    def ingest_channel_data(self, date_range_days: int = 90) -> IngestionResult:
        """Ingest all channel data for the specified date range."""
        errors = []
        videos_processed = 0
        metrics_updated = 0
        
        try:
            # Get channel info
            channel_info = self.get_channel_info()
            if not channel_info:
                errors.append("Could not retrieve channel information")
                return IngestionResult(False, 0, 0, errors, self.quota_used)
            
            channel_id = channel_info["id"]
            logger.info(f"Ingesting data for channel: {channel_info['snippet']['title']}")
            
            # Get videos
            videos = self.get_channel_videos(channel_id, max_results=100)
            if videos:
                videos_processed = self.save_videos_to_db(videos, channel_id)
                logger.info(f"Processed {videos_processed} videos")
            
            # Get analytics data
            end_date = date.today()
            start_date = end_date - timedelta(days=date_range_days)
            
            video_ids = [v["video_id"] for v in videos]
            if video_ids:
                video_analytics = self.get_video_analytics(video_ids, start_date, end_date)
                if video_analytics:
                    metrics_updated = self.save_metrics_to_db(video_analytics)
                    logger.info(f"Updated {metrics_updated} metric records")
            
            return IngestionResult(
                success=True,
                videos_processed=videos_processed,
                metrics_updated=metrics_updated,
                errors=errors,
                quota_used=self.quota_used
            )
            
        except Exception as e:
            error_msg = f"Error during data ingestion: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            
            return IngestionResult(
                success=False,
                videos_processed=videos_processed,
                metrics_updated=metrics_updated,
                errors=errors,
                quota_used=self.quota_used
            )

def get_ingester() -> YouTubeDataIngester:
    """Get a YouTube data ingester instance."""
    return YouTubeDataIngester()