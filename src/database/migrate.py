#!/usr/bin/env python3
"""
Database Migration Script

Handles database initialization and schema migrations.
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, date, timedelta
import random

from sqlalchemy import text
from .models import (
    init_database, get_db_session, Video, VideoMetrics, 
    ChannelMetrics, Insight, APIQuota
)
from ..utils.config import get_config

def create_database():
    """Create database tables."""
    config = get_config()
    print(f"Creating database with URL: {config.database_url}")
    
    try:
        db_manager = init_database(config.database_url)
        print("✅ Database tables created successfully!")
        return db_manager
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        sys.exit(1)

def load_sample_data():
    """Load sample data for testing."""
    print("Loading sample data...")
    
    session = get_db_session()
    
    try:
        # Sample channel ID
        channel_id = "UC_sample_channel_id_123"
        
        # Create sample videos
        sample_videos = [
            {
                "video_id": "abc123def456",
                "title": "How to Build Amazing YouTube Analytics Dashboard",
                "description": "Learn how to create a comprehensive analytics dashboard for YouTube channels using Python, Streamlit, and AI.",
                "published_at": datetime.now() - timedelta(days=30),
                "duration_seconds": 720,
                "tags": ["youtube", "analytics", "python", "streamlit", "ai"]
            },
            {
                "video_id": "xyz789uvw012",
                "title": "Top 10 YouTube Growth Strategies for 2024",
                "description": "Discover the most effective strategies to grow your YouTube channel in 2024.",
                "published_at": datetime.now() - timedelta(days=15),
                "duration_seconds": 900,
                "tags": ["youtube", "growth", "strategy", "2024", "tips"]
            },
            {
                "video_id": "mno345pqr678",
                "title": "AI-Powered Content Optimization Techniques",
                "description": "Learn how to use AI to optimize your content for better engagement and reach.",
                "published_at": datetime.now() - timedelta(days=7),
                "duration_seconds": 600,
                "tags": ["ai", "content", "optimization", "engagement"]
            }
        ]
        
        # Insert videos (handle duplicates)
        for video_data in sample_videos:
            # Check if video already exists
            existing_video = session.query(Video).filter(
                Video.video_id == video_data["video_id"]
            ).first()
            
            if not existing_video:
                video = Video(
                    video_id=video_data["video_id"],
                    channel_id=channel_id,
                    title=video_data["title"],
                    description=video_data["description"],
                    published_at=video_data["published_at"],
                    duration_seconds=video_data["duration_seconds"],
                    tags=video_data["tags"],
                    thumbnail_url=f"https://i.ytimg.com/vi/{video_data['video_id']}/maxresdefault.jpg"
                )
                session.add(video)
            else:
                print(f"Video {video_data['video_id']} already exists, skipping...")
        
        # Create sample metrics for the last 30 days
        for video_data in sample_videos:
            video_id = video_data["video_id"]
            published_date = video_data["published_at"].date()
            
            # Generate metrics from published date to today
            current_date = published_date
            today = date.today()
            
            base_views = random.randint(1000, 10000)
            base_impressions = base_views * random.randint(5, 15)
            
            while current_date <= today:
                # Check if metrics already exist for this video and date
                existing_metrics = session.query(VideoMetrics).filter(
                    VideoMetrics.video_id == video_id,
                    VideoMetrics.date == current_date
                ).first()
                
                if not existing_metrics:
                    # Simulate realistic growth patterns
                    days_since_publish = (current_date - published_date).days
                    decay_factor = max(0.1, 1 - (days_since_publish * 0.05))
                    
                    views = int(base_views * decay_factor * random.uniform(0.8, 1.2))
                    impressions = int(base_impressions * decay_factor * random.uniform(0.9, 1.1))
                    
                    metrics = VideoMetrics(
                        video_id=video_id,
                        date=current_date,
                        impressions=impressions,
                        impressions_ctr=random.uniform(0.03, 0.12),
                        views=views,
                        unique_viewers=int(views * random.uniform(0.7, 0.95)),
                    average_view_duration_seconds=random.uniform(120, 400),
                    watch_time_minutes=views * random.uniform(2, 8),
                    likes=int(views * random.uniform(0.02, 0.08)),
                    comments=int(views * random.uniform(0.005, 0.02)),
                    shares=int(views * random.uniform(0.001, 0.01)),
                    subscribers_gained=random.randint(0, 20),
                    subscribers_lost=random.randint(0, 5),
                    traffic_sources={
                        "YOUTUBE_SEARCH": random.randint(30, 50),
                        "SUGGESTED_VIDEO": random.randint(20, 40),
                        "EXTERNAL": random.randint(5, 15),
                        "BROWSE": random.randint(10, 25)
                    },
                    top_geographies={
                        "US": {"views": int(views * 0.4), "watch_time": random.uniform(100, 300)},
                        "GB": {"views": int(views * 0.15), "watch_time": random.uniform(50, 150)},
                        "CA": {"views": int(views * 0.1), "watch_time": random.uniform(30, 100)}
                    }
                )
                
                    # Calculate derived metrics
                    metrics.calculate_derived_metrics(video_data["duration_seconds"])
                    session.add(metrics)
                else:
                    print(f"Metrics for video {video_id} on {current_date} already exist, skipping...")
                
                current_date += timedelta(days=1)
        
        # Create sample channel metrics (handle duplicates)
        current_date = date.today() - timedelta(days=30)
        today = date.today()
        
        while current_date <= today:
            # Check if channel metrics already exist for this date
            existing_metrics = session.query(ChannelMetrics).filter(
                ChannelMetrics.channel_id == channel_id,
                ChannelMetrics.date == current_date
            ).first()
            
            if not existing_metrics:
                channel_metrics = ChannelMetrics(
                    channel_id=channel_id,
                    date=current_date,
                    total_views=random.randint(50000, 100000),
                    total_impressions=random.randint(200000, 500000),
                    total_watch_time_minutes=random.randint(10000, 30000),
                    subscriber_count=random.randint(5000, 15000),
                    video_count=len(sample_videos),
                    views_gained=random.randint(100, 1000),
                    subscribers_gained=random.randint(10, 50),
                    subscribers_lost=random.randint(0, 20)
                )
                session.add(channel_metrics)
            else:
                print(f"Channel metrics already exist for {current_date}, skipping...")
            current_date += timedelta(days=1)
        
        # Create sample insights
        sample_insights = [
            {
                "video_id": "abc123def456",
                "insight_type": "video",
                "action_type": "suggest_title_change",
                "priority": "high",
                "confidence": 0.85,
                "rationale": "Current title has low CTR. Suggested title includes trending keywords.",
                "payload_json": {
                    "suggested_title": "How to Build AMAZING YouTube Analytics Dashboard (Step-by-Step Tutorial)",
                    "current_ctr": 0.045,
                    "expected_improvement": "25-40%"
                }
            },
            {
                "video_id": None,
                "insight_type": "channel",
                "action_type": "prioritize_promotion",
                "priority": "medium",
                "confidence": 0.72,
                "rationale": "Recent videos show declining engagement. Focus promotion on top-performing content.",
                "payload_json": {
                    "recommended_videos": ["abc123def456", "xyz789uvw012"],
                    "promotion_channels": ["social_media", "community_posts"],
                    "budget_allocation": {"abc123def456": 0.6, "xyz789uvw012": 0.4}
                }
            }
        ]
        
        for insight_data in sample_insights:
            # Check if insight already exists
            existing_insight = session.query(Insight).filter(
                Insight.video_id == insight_data["video_id"],
                Insight.channel_id == channel_id,
                Insight.insight_type == insight_data["insight_type"],
                Insight.action_type == insight_data["action_type"]
            ).first()
            
            if not existing_insight:
                insight = Insight(
                    video_id=insight_data["video_id"],
                    channel_id=channel_id,
                    insight_type=insight_data["insight_type"],
                    action_type=insight_data["action_type"],
                    priority=insight_data["priority"],
                    confidence=insight_data["confidence"],
                    rationale=insight_data["rationale"],
                    payload_json=insight_data["payload_json"]
                )
                session.add(insight)
            else:
                print(f"Insight for {insight_data['insight_type']} {insight_data['action_type']} already exists, skipping...")
        
        # Create API quota tracking (handle duplicates)
        today = date.today()
        existing_quota = session.query(APIQuota).filter(
            APIQuota.api_name == "youtube_data",
            APIQuota.date == today
        ).first()
        
        if not existing_quota:
            api_quota = APIQuota(
                api_name="youtube_data",
                date=today,
                quota_used=1500,
                quota_limit=10000
            )
            session.add(api_quota)
        else:
            print("API quota entry already exists for today, skipping...")
        
        session.commit()
        print("✅ Sample data loaded successfully!")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error loading sample data: {e}")
        raise
    finally:
        session.close()

def reset_database():
    """Reset database (drop and recreate all tables)."""
    print("⚠️  Resetting database (this will delete all data)...")
    
    config = get_config()
    db_manager = init_database(config.database_url)
    
    # Drop all tables
    from .models import Base
    Base.metadata.drop_all(bind=db_manager.engine)
    
    # Recreate tables
    Base.metadata.create_all(bind=db_manager.engine)
    
    print("✅ Database reset successfully!")

def main():
    """Main migration script."""
    parser = argparse.ArgumentParser(description="Database migration script")
    parser.add_argument(
        "action",
        choices=["create", "sample", "reset"],
        help="Action to perform: create (create tables), sample (load sample data), reset (reset database)"
    )
    
    args = parser.parse_args()
    
    if args.action == "create":
        create_database()
    elif args.action == "sample":
        create_database()
        load_sample_data()
    elif args.action == "reset":
        reset_database()

if __name__ == "__main__":
    main()