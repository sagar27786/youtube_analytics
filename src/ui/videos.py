#!/usr/bin/env python3
"""
Videos Table Page - Sortable and searchable table of all videos with metrics
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional, List
from PIL import Image
import requests
from io import BytesIO

from ..storage import get_storage_adapter
from ..auth.youtube_auth import get_authenticator
from ..ai.gemini_client import get_insight_generator
from ..database.models import get_db_session

def format_number(num: float) -> str:
    """Format numbers for display."""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return f"{num:,.0f}"

def format_duration(seconds: float) -> str:
    """Format duration in seconds to readable format."""
    if seconds >= 3600:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
    elif seconds >= 60:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        return f"{seconds:.0f}s"

def load_thumbnail(url: str, size: tuple = (120, 90)) -> Optional[Image.Image]:
    """Load and resize thumbnail image."""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            img.thumbnail(size, Image.Resampling.LANCZOS)
            return img
    except Exception:
        pass
    return None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_videos_data(start_date: date, end_date: date, search_term: str = "") -> pd.DataFrame:
    """Get videos data with metrics for the specified date range."""
    session = get_db_session()
    
    try:
        # Base query for videos with their latest metrics
        query = """
        SELECT 
            v.video_id,
            v.title,
            v.description,
            v.published_at,
            v.thumbnail_url,
            v.channel_id,
            COALESCE(SUM(vm.impressions), 0) as total_impressions,
            COALESCE(SUM(vm.views), 0) as total_views,
            CASE 
                WHEN SUM(vm.impressions) > 0 
                THEN (SUM(vm.views) * 100.0 / SUM(vm.impressions))
                ELSE 0 
            END as ctr,
            COALESCE(AVG(vm.average_view_duration_seconds), 0) as avg_view_duration,
            COALESCE(SUM(vm.watch_time_minutes), 0) as total_watch_time,
            COALESCE(SUM(vm.likes), 0) as total_likes,
            COALESCE(SUM(vm.comments), 0) as total_comments,
            COALESCE(SUM(vm.shares), 0) as total_shares,
            COALESCE(SUM(vm.subscribers_gained), 0) as subscribers_gained,
            MAX(i.created_at) as last_insight_timestamp,
            COUNT(DISTINCT i.id) as insight_count
        FROM videos v
        LEFT JOIN video_metrics vm ON v.video_id = vm.video_id 
            AND vm.date BETWEEN :start_date AND :end_date
        LEFT JOIN insights i ON v.video_id = i.video_id
        WHERE 1=1
        """
        
        params = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        # Add search filter if provided
        if search_term:
            query += " AND (LOWER(v.title) LIKE :search OR LOWER(v.description) LIKE :search)"
            params['search'] = f"%{search_term.lower()}%"
        
        query += """
        GROUP BY v.video_id, v.title, v.description, v.published_at, v.thumbnail_url, v.channel_id
        ORDER BY total_views DESC
        """
        
        df = pd.read_sql(query, session.bind, params=params)
        
        # Convert published_at to datetime if it's not already
        if not df.empty and 'published_at' in df.columns:
            df['published_at'] = pd.to_datetime(df['published_at'])
            df['days_since_published'] = (datetime.now() - df['published_at']).dt.days
        
        return df
        
    except Exception as e:
        st.error(f"Error loading videos data: {e}")
        return pd.DataFrame()
    finally:
        session.close()

def get_video_insights_count(video_id: str) -> int:
    """Get the number of insights for a specific video."""
    session = get_db_session()
    
    try:
        count = session.query(Insight).filter(
            Insight.video_id == video_id
        ).count()
        return count
    except Exception:
        return 0
    finally:
        session.close()

def generate_video_insight(video_data: Dict[str, Any]) -> bool:
    """Generate insights for a specific video."""
    try:
        insight_generator = get_insight_generator()
        
        # Prepare video data for Gemini
        gemini_data = {
            "video_id": video_data["video_id"],
            "channel_id": video_data["channel_id"],
            "title": video_data["title"],
            "impressions": int(video_data["total_impressions"]),
            "views": int(video_data["total_views"]),
            "ctr": float(video_data["ctr"]),
            "avg_view_duration_sec": float(video_data["avg_view_duration"]),
            "watch_time": int(video_data["total_watch_time"]),
            "published_at": video_data["published_at"].isoformat() if pd.notna(video_data["published_at"]) else None,
            "likes": int(video_data["total_likes"]),
            "comments": int(video_data["total_comments"]),
            "days_since_published": int(video_data.get("days_since_published", 0))
        }
        
        response = insight_generator.generate_insights_for_video(gemini_data)
        return response.success
        
    except Exception as e:
        st.error(f"Error generating insights: {e}")
        return False

def render_video_row(video_data: Dict[str, Any], show_thumbnail: bool = True) -> None:
    """Render a single video row with metrics."""
    cols = st.columns([1, 3, 1, 1, 1, 1, 1, 1, 1] if show_thumbnail else [4, 1, 1, 1, 1, 1, 1, 1])
    
    col_idx = 0
    
    # Thumbnail column
    if show_thumbnail:
        with cols[col_idx]:
            if video_data.get('thumbnail_url'):
                try:
                    st.image(video_data['thumbnail_url'], width=120)
                except Exception:
                    st.write("🖼️")
            else:
                st.write("🖼️")
        col_idx += 1
    
    # Title and description
    with cols[col_idx]:
        st.write(f"**{video_data['title'][:60]}{'...' if len(video_data['title']) > 60 else ''}**")
        if video_data.get('published_at'):
            st.caption(f"Published: {video_data['published_at'].strftime('%Y-%m-%d')}")
        if video_data.get('description'):
            st.caption(f"{video_data['description'][:100]}{'...' if len(video_data['description']) > 100 else ''}")
    col_idx += 1
    
    # Metrics columns
    with cols[col_idx]:
        st.metric("Impressions", format_number(video_data['total_impressions']))
    col_idx += 1
    
    with cols[col_idx]:
        st.metric("Views", format_number(video_data['total_views']))
    col_idx += 1
    
    with cols[col_idx]:
        st.metric("CTR", f"{video_data['ctr']:.2f}%")
    col_idx += 1
    
    with cols[col_idx]:
        st.metric("Avg Duration", format_duration(video_data['avg_view_duration']))
    col_idx += 1
    
    with cols[col_idx]:
        st.metric("Watch Time", format_duration(video_data['total_watch_time']))
    col_idx += 1
    
    with cols[col_idx]:
        st.metric("Likes", format_number(video_data['total_likes']))
    col_idx += 1
    
    # Actions column
    with cols[col_idx]:
        insight_count = video_data.get('insight_count', 0)
        if insight_count > 0:
            st.success(f"✅ {insight_count} insights")
        else:
            st.info("No insights")
        
        if st.button(f"📊 Details", key=f"details_{video_data['video_id']}"):
            st.session_state['selected_video_id'] = video_data['video_id']
            st.session_state['current_page'] = 'video_details'
            st.rerun()
        
        if st.button(f"🤖 Generate Insight", key=f"insight_{video_data['video_id']}"):
            with st.spinner("Generating insights..."):
                if generate_video_insight(video_data):
                    st.success("✅ Insights generated!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("❌ Failed to generate insights")

def render_videos_table(df: pd.DataFrame, show_thumbnails: bool = True) -> None:
    """Render the videos table."""
    if df.empty:
        st.info("No videos found for the selected criteria.")
        return
    
    st.write(f"**Found {len(df)} videos**")
    
    # Table headers
    header_cols = st.columns([1, 3, 1, 1, 1, 1, 1, 1, 1] if show_thumbnails else [4, 1, 1, 1, 1, 1, 1, 1])
    
    col_idx = 0
    if show_thumbnails:
        header_cols[col_idx].write("**Thumbnail**")
        col_idx += 1
    
    header_cols[col_idx].write("**Title & Info**")
    header_cols[col_idx + 1].write("**Impressions**")
    header_cols[col_idx + 2].write("**Views**")
    header_cols[col_idx + 3].write("**CTR**")
    header_cols[col_idx + 4].write("**Avg Duration**")
    header_cols[col_idx + 5].write("**Watch Time**")
    header_cols[col_idx + 6].write("**Likes**")
    header_cols[col_idx + 7].write("**Actions**")
    
    st.divider()
    
    # Render video rows
    for idx, row in df.iterrows():
        render_video_row(row.to_dict(), show_thumbnails)
        if idx < len(df) - 1:  # Don't add divider after last row
            st.divider()

def render_videos_page():
    """Render the videos table page."""
    st.title("📹 Videos Analytics")
    
    # Filters and controls
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=date.today() - timedelta(days=30),
            max_value=date.today(),
            key="videos_start_date"
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=date.today(),
            max_value=date.today(),
            key="videos_end_date"
        )
    
    with col3:
        search_term = st.text_input(
            "🔍 Search videos",
            placeholder="Search by title or description...",
            key="videos_search"
        )
    
    with col4:
        st.write("")
        st.write("")
        show_thumbnails = st.checkbox("Show thumbnails", value=True)
    
    # Validate date range
    if start_date > end_date:
        st.error("Start date must be before end date.")
        return
    
    # Sort options
    col1, col2, col3 = st.columns([2, 2, 4])
    
    with col1:
        sort_by = st.selectbox(
            "Sort by",
            options=[
                "total_views", "total_impressions", "ctr", "avg_view_duration",
                "total_watch_time", "total_likes", "total_comments", "published_at"
            ],
            format_func=lambda x: {
                "total_views": "Views",
                "total_impressions": "Impressions",
                "ctr": "CTR",
                "avg_view_duration": "Avg Duration",
                "total_watch_time": "Watch Time",
                "total_likes": "Likes",
                "total_comments": "Comments",
                "published_at": "Published Date"
            }.get(x, x),
            key="videos_sort_by"
        )
    
    with col2:
        sort_order = st.selectbox(
            "Order",
            options=["desc", "asc"],
            format_func=lambda x: "Descending" if x == "desc" else "Ascending",
            key="videos_sort_order"
        )
    
    # Load and display data
    with st.spinner("Loading videos data..."):
        df = get_videos_data(start_date, end_date, search_term)
    
    if not df.empty:
        # Apply sorting
        df_sorted = df.sort_values(
            by=sort_by,
            ascending=(sort_order == "asc")
        )
        
        # Pagination
        videos_per_page = 10
        total_pages = (len(df_sorted) + videos_per_page - 1) // videos_per_page
        
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                page = st.selectbox(
                    f"Page (1-{total_pages})",
                    range(1, total_pages + 1),
                    key="videos_page"
                )
            
            start_idx = (page - 1) * videos_per_page
            end_idx = start_idx + videos_per_page
            df_page = df_sorted.iloc[start_idx:end_idx]
        else:
            df_page = df_sorted
        
        # Summary stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Videos", len(df))
        
        with col2:
            total_views = df['total_views'].sum()
            st.metric("Total Views", format_number(total_views))
        
        with col3:
            avg_ctr = df['ctr'].mean()
            st.metric("Average CTR", f"{avg_ctr:.2f}%")
        
        with col4:
            videos_with_insights = df[df['insight_count'] > 0]
            st.metric("Videos with Insights", f"{len(videos_with_insights)}/{len(df)}")
        
        st.divider()
        
        # Bulk actions
        col1, col2, col3 = st.columns([2, 2, 4])
        
        with col1:
            if st.button("🤖 Generate Insights for All", type="secondary"):
                authenticator = get_authenticator()
                if not authenticator.is_authenticated():
                    st.error("Please authenticate with YouTube first.")
                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    success_count = 0
                    total_videos = len(df_page)
                    
                    for idx, row in df_page.iterrows():
                        status_text.text(f"Processing video {idx + 1}/{total_videos}: {row['title'][:50]}...")
                        
                        if generate_video_insight(row.to_dict()):
                            success_count += 1
                        
                        progress_bar.progress((idx + 1) / total_videos)
                    
                    status_text.text(f"✅ Generated insights for {success_count}/{total_videos} videos")
                    st.cache_data.clear()
                    st.rerun()
        
        with col2:
            if st.button("📊 Export Data", type="secondary"):
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"youtube_videos_{start_date}_{end_date}.csv",
                    mime="text/csv"
                )
        
        st.divider()
        
        # Render the videos table
        render_videos_table(df_page, show_thumbnails)
        
    else:
        st.warning("No videos found for the selected criteria. Try adjusting your filters or date range.")

if __name__ == "__main__":
    render_videos_page()