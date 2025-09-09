#!/usr/bin/env python3
"""
Database Models for YouTube Analytics Dashboard

Defines SQLAlchemy models for storing YouTube analytics data.
"""

from datetime import datetime, date
from typing import Optional, Dict, Any
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, Date,
    Text, JSON, Boolean, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.sql import func

Base = declarative_base()

class Video(Base):
    """Video metadata table."""
    __tablename__ = "videos"
    
    video_id = Column(String(20), primary_key=True)
    channel_id = Column(String(30), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    published_at = Column(DateTime, nullable=False, index=True)
    thumbnail_url = Column(String(500))
    duration_seconds = Column(Integer)
    tags = Column(JSON)  # List of tags
    category_id = Column(String(10))
    default_language = Column(String(10))
    default_audio_language = Column(String(10))
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    metrics = relationship("VideoMetrics", back_populates="video", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="video", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Video(video_id='{self.video_id}', title='{self.title[:50]}...')>"

class VideoMetrics(Base):
    """Video metrics table for time-series data."""
    __tablename__ = "video_metrics"
    
    id = Column(Integer, primary_key=True)
    video_id = Column(String(20), ForeignKey("videos.video_id"), nullable=False)
    date = Column(Date, nullable=False)
    
    # Core metrics from YouTube Analytics API
    impressions = Column(Integer, default=0)
    impressions_ctr = Column(Float, default=0.0)  # Click-through rate
    views = Column(Integer, default=0)
    unique_viewers = Column(Integer, default=0)
    average_view_duration_seconds = Column(Float, default=0.0)
    watch_time_minutes = Column(Float, default=0.0)
    
    # Engagement metrics
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    
    # Subscriber metrics
    subscribers_gained = Column(Integer, default=0)
    subscribers_lost = Column(Integer, default=0)
    
    # Traffic source data (JSON)
    traffic_sources = Column(JSON)  # {"source_type": count, ...}
    
    # Geography data (JSON)
    top_geographies = Column(JSON)  # {"country_code": {"views": count, "watch_time": minutes}, ...}
    
    # Derived KPIs
    engagement_rate = Column(Float, default=0.0)  # (likes + comments + shares) / views
    retention_rate = Column(Float, default=0.0)  # avg_view_duration / video_duration
    effective_watch_time = Column(Float, default=0.0)  # watch_time * engagement_rate
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    video = relationship("Video", back_populates="metrics")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('video_id', 'date', name='uq_video_date'),
        Index('idx_video_date', 'video_id', 'date'),
        Index('idx_date_views', 'date', 'views'),
    )
    
    def calculate_derived_metrics(self, video_duration_seconds: Optional[int] = None):
        """Calculate derived KPIs from raw metrics."""
        # Engagement rate
        if self.views > 0:
            total_engagement = (self.likes or 0) + (self.comments or 0) + (self.shares or 0)
            self.engagement_rate = total_engagement / self.views
        
        # Retention rate
        if video_duration_seconds and video_duration_seconds > 0:
            self.retention_rate = self.average_view_duration_seconds / video_duration_seconds
        
        # Effective watch time
        self.effective_watch_time = (self.watch_time_minutes or 0) * (1 + self.engagement_rate)
    
    def __repr__(self):
        return f"<VideoMetrics(video_id='{self.video_id}', date='{self.date}', views={self.views})>"

class ChannelMetrics(Base):
    """Channel-level metrics table."""
    __tablename__ = "channel_metrics"
    
    id = Column(Integer, primary_key=True)
    channel_id = Column(String(30), nullable=False, index=True)
    date = Column(Date, nullable=False)
    
    # Channel metrics
    total_views = Column(Integer, default=0)
    total_impressions = Column(Integer, default=0)
    total_watch_time_minutes = Column(Float, default=0.0)
    subscriber_count = Column(Integer, default=0)
    video_count = Column(Integer, default=0)
    
    # Daily changes
    views_gained = Column(Integer, default=0)
    subscribers_gained = Column(Integer, default=0)
    subscribers_lost = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('channel_id', 'date', name='uq_channel_date'),
        Index('idx_channel_date', 'channel_id', 'date'),
    )
    
    def __repr__(self):
        return f"<ChannelMetrics(channel_id='{self.channel_id}', date='{self.date}')>"

class Insight(Base):
    """AI-generated insights table."""
    __tablename__ = "insights"
    
    id = Column(Integer, primary_key=True)
    video_id = Column(String(20), ForeignKey("videos.video_id"), nullable=True)  # NULL for channel-level insights
    channel_id = Column(String(30), nullable=False, index=True)
    
    # Insight metadata
    insight_type = Column(String(50), nullable=False)  # "channel" or "video"
    action_type = Column(String(100), nullable=False)  # e.g., "reindex", "retitle", etc.
    priority = Column(String(10), nullable=False)  # "high", "medium", "low"
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    
    # Insight content
    rationale = Column(Text, nullable=False)
    payload_json = Column(JSON)  # Structured data (suggested changes, affected videos, etc.)
    
    # Status tracking
    status = Column(String(20), default="pending")  # "pending", "applied", "dismissed"
    applied_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    video = relationship("Video", back_populates="insights")
    
    # Indexes
    __table_args__ = (
        Index('idx_channel_type_priority', 'channel_id', 'insight_type', 'priority'),
        Index('idx_created_at', 'created_at'),
        Index('idx_status', 'status'),
    )
    
    def __repr__(self):
        return f"<Insight(id={self.id}, action_type='{self.action_type}', priority='{self.priority}')>"

class APIQuota(Base):
    """API quota tracking table."""
    __tablename__ = "api_quota"
    
    id = Column(Integer, primary_key=True)
    api_name = Column(String(50), nullable=False)  # "youtube_data", "youtube_analytics", "gemini"
    date = Column(Date, nullable=False)
    quota_used = Column(Integer, default=0)
    quota_limit = Column(Integer, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('api_name', 'date', name='uq_api_date'),
        Index('idx_api_date', 'api_name', 'date'),
    )
    
    def __repr__(self):
        return f"<APIQuota(api_name='{self.api_name}', date='{self.date}', used={self.quota_used})>"

# Database session management
class DatabaseManager:
    """Database connection and session management."""
    
    def __init__(self, database_url: str):
        self.engine = create_engine(
            database_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,
            pool_recycle=3600
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all tables."""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()
    
    def close(self):
        """Close database connections."""
        self.engine.dispose()

# Global database manager
_db_manager: Optional[DatabaseManager] = None

def init_database(database_url: str) -> DatabaseManager:
    """Initialize the database."""
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    _db_manager.create_tables()
    return _db_manager

def get_db_manager() -> DatabaseManager:
    """Get the global database manager."""
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db_manager

def get_db_session() -> Session:
    """Get a database session."""
    return get_db_manager().get_session()