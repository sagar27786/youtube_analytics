#!/usr/bin/env python3
"""
Overview Page - Main dashboard with KPI cards and summary metrics
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional, Tuple

from ..storage import get_storage_adapter
from ..ingestion.youtube_data import get_ingester
from ..ai.gemini_client import get_insight_generator
from ..auth.youtube_auth import get_authenticator

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

def get_date_range_data(start_date: date, end_date: date) -> Dict[str, Any]:
    """Get aggregated data for the specified date range."""
    storage = get_storage_adapter()
    
    try:
        # Get all video metrics from storage
        all_metrics = []
        all_videos = storage.get_all_videos()
        
        for video in all_videos:
            metrics = storage.get_video_metrics(video['video_id'])
            if metrics and metrics.get('date_recorded'):
                # Parse date and filter by range
                try:
                    metric_date = datetime.fromisoformat(metrics['date_recorded']).date()
                    if start_date <= metric_date <= end_date:
                        all_metrics.append(metrics)
                except (ValueError, TypeError):
                    continue
        
        if not all_metrics:
            return {
                'total_impressions': 0,
                'total_views': 0,
                'avg_ctr': 0,
                'avg_view_duration': 0,
                'total_watch_time': 0,
                'total_likes': 0,
                'total_comments': 0,
                'total_shares': 0,
                'net_subscribers': 0,
                'video_count': 0,
                'daily_metrics': pd.DataFrame(),
                'top_videos': pd.DataFrame()
            }
        
        # Convert to DataFrame for easier processing
        metrics_df = pd.DataFrame(all_metrics)
        
        # Calculate aggregated metrics
        total_views = metrics_df['views'].sum()
        total_watch_time = metrics_df['watch_time_minutes'].sum()
        total_likes = metrics_df['likes'].sum()
        total_comments = metrics_df['comments'].sum()
        total_shares = metrics_df['shares'].sum()
        avg_view_duration = metrics_df['average_view_duration'].mean()
        avg_ctr = metrics_df['click_through_rate'].mean()
        net_subscribers = metrics_df['subscriber_gain'].sum()
        video_count = metrics_df['video_id'].nunique()
        
        # Create daily metrics (simplified for local storage)
        metrics_df['date'] = pd.to_datetime(metrics_df['date_recorded']).dt.date
        daily_metrics = metrics_df.groupby('date').agg({
            'views': 'sum',
            'watch_time_minutes': 'sum',
            'likes': 'sum',
            'comments': 'sum'
        }).reset_index()
        
        # Top performing videos
        video_performance = metrics_df.groupby('video_id').agg({
            'views': 'sum',
            'watch_time_minutes': 'sum',
            'average_view_duration': 'mean'
        }).reset_index()
        
        # Get video details and merge
        videos_data = []
        for video in all_videos:
            if video['video_id'] in video_performance['video_id'].values:
                videos_data.append(video)
        
        videos_df = pd.DataFrame(videos_data)
        
        if not videos_df.empty:
            top_videos = video_performance.merge(videos_df, on='video_id', how='left')
            top_videos = top_videos.sort_values('views', ascending=False).head(10)
        else:
            top_videos = pd.DataFrame()
        
        return {
            'total_impressions': total_views,  # Using views as impressions for simplicity
            'total_views': total_views,
            'avg_ctr': avg_ctr,
            'avg_view_duration': avg_view_duration,
            'total_watch_time': total_watch_time,
            'total_likes': total_likes,
            'total_comments': total_comments,
            'total_shares': total_shares,
            'net_subscribers': net_subscribers,
            'video_count': video_count,
            'daily_metrics': daily_metrics,
            'top_videos': top_videos
        }
        
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return {}

def render_kpi_cards(data: Dict[str, Any]):
    """Render KPI cards."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📊 Total Impressions",
            value=format_number(data.get('total_impressions', 0))
        )
        st.metric(
            label="👀 Total Views",
            value=format_number(data.get('total_views', 0))
        )
    
    with col2:
        st.metric(
            label="🎯 Average CTR",
            value=f"{data.get('avg_ctr', 0):.2f}%"
        )
        st.metric(
            label="⏱️ Avg View Duration",
            value=format_duration(data.get('avg_view_duration', 0))
        )
    
    with col3:
        st.metric(
            label="⏰ Total Watch Time",
            value=format_duration(data.get('total_watch_time', 0))
        )
        st.metric(
            label="👍 Total Likes",
            value=format_number(data.get('total_likes', 0))
        )
    
    with col4:
        st.metric(
            label="💬 Total Comments",
            value=format_number(data.get('total_comments', 0))
        )
        st.metric(
            label="📈 Net Subscribers",
            value=f"+{data.get('net_subscribers', 0):,}" if data.get('net_subscribers', 0) >= 0 else f"{data.get('net_subscribers', 0):,}",
            delta=data.get('net_subscribers', 0)
        )

def render_charts(data: Dict[str, Any]):
    """Render performance charts."""
    daily_metrics = data.get('daily_metrics', pd.DataFrame())
    
    if daily_metrics.empty:
        st.info("No data available for the selected date range.")
        return
    
    # Views and Impressions over time
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Views & Impressions Over Time")
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=daily_metrics['date'],
            y=daily_metrics['views'],
            mode='lines+markers',
            name='Views',
            line=dict(color='#1f77b4')
        ))
        
        fig.add_trace(go.Scatter(
            x=daily_metrics['date'],
            y=daily_metrics['impressions'],
            mode='lines+markers',
            name='Impressions',
            yaxis='y2',
            line=dict(color='#ff7f0e')
        ))
        
        fig.update_layout(
            xaxis_title="Date",
            yaxis=dict(title="Views", side="left"),
            yaxis2=dict(title="Impressions", side="right", overlaying="y"),
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🎯 Click-Through Rate Over Time")
        fig = px.line(
            daily_metrics,
            x='date',
            y='ctr',
            title='CTR Trend',
            labels={'ctr': 'CTR (%)', 'date': 'Date'}
        )
        fig.update_traces(line_color='#2ca02c')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Engagement metrics
    st.subheader("💬 Engagement Metrics Over Time")
    
    engagement_fig = go.Figure()
    
    engagement_fig.add_trace(go.Scatter(
        x=daily_metrics['date'],
        y=daily_metrics['likes'],
        mode='lines+markers',
        name='Likes',
        line=dict(color='#d62728')
    ))
    
    engagement_fig.add_trace(go.Scatter(
        x=daily_metrics['date'],
        y=daily_metrics['comments'],
        mode='lines+markers',
        name='Comments',
        yaxis='y2',
        line=dict(color='#9467bd')
    ))
    
    engagement_fig.update_layout(
        xaxis_title="Date",
        yaxis=dict(title="Likes", side="left"),
        yaxis2=dict(title="Comments", side="right", overlaying="y"),
        hovermode='x unified',
        height=400
    )
    
    st.plotly_chart(engagement_fig, use_container_width=True)

def render_top_videos(data: Dict[str, Any]):
    """Render top performing videos table."""
    top_videos = data.get('top_videos', pd.DataFrame())
    
    if top_videos.empty:
        st.info("No video data available.")
        return
    
    st.subheader("🏆 Top Performing Videos")
    
    # Format the dataframe for display
    display_df = top_videos[[
        'title', 'views', 'impressions', 'ctr', 'watch_time', 'avg_view_duration'
    ]].copy()
    
    display_df['views'] = display_df['views'].apply(format_number)
    display_df['impressions'] = display_df['impressions'].apply(format_number)
    display_df['ctr'] = display_df['ctr'].apply(lambda x: f"{x:.2f}%")
    display_df['watch_time'] = display_df['watch_time'].apply(format_duration)
    display_df['avg_view_duration'] = display_df['avg_view_duration'].apply(format_duration)
    
    display_df.columns = ['Title', 'Views', 'Impressions', 'CTR', 'Watch Time', 'Avg Duration']
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

def handle_data_refresh():
    """Handle manual data refresh."""
    authenticator = get_authenticator()
    
    if not authenticator.is_authenticated():
        st.error("Please authenticate with YouTube first in the Settings page.")
        return False
    
    try:
        with st.spinner("Refreshing data from YouTube..."):
            ingester = get_ingester()
            
            # Get date range from session state
            start_date = st.session_state.get('overview_start_date', date.today() - timedelta(days=30))
            end_date = st.session_state.get('overview_end_date', date.today())
            
            # Calculate date range in days
            date_range_days = (end_date - start_date).days + 1
            result = ingester.ingest_channel_data(date_range_days=date_range_days)
            
            if result.success:
                st.success(f"✅ Data refreshed successfully! Fetched {result.videos_processed} videos and {result.metrics_saved} metrics.")
                
                # Clear cache to show updated data
                st.cache_data.clear()
                return True
            else:
                st.error(f"❌ Data refresh failed: {'; '.join(result.errors)}")
                return False
                
    except Exception as e:
        st.error(f"❌ Error during data refresh: {e}")
        return False

def render_overview_page():
    """Render the main overview page."""
    st.title("📊 YouTube Analytics Overview")
    
    # Date range selector
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=date.today() - timedelta(days=30),
            max_value=date.today(),
            key="overview_start_date"
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=date.today(),
            max_value=date.today(),
            key="overview_end_date"
        )
    
    with col3:
        st.write("")
        st.write("")
        if st.button("🔄 Refresh Data", type="primary"):
            handle_data_refresh()
            st.rerun()
    
    # Validate date range
    if start_date > end_date:
        st.error("Start date must be before end date.")
        return
    
    # Get data for the selected date range
    with st.spinner("Loading analytics data..."):
        data = get_date_range_data(start_date, end_date)
    
    if not data:
        st.warning("No data available. Please refresh data or check your date range.")
        return
    
    # Render components
    render_kpi_cards(data)
    
    st.divider()
    
    render_charts(data)
    
    st.divider()
    
    render_top_videos(data)
    
    # Quick insights section
    if data.get('video_count', 0) > 0:
        st.divider()
        st.subheader("🤖 Quick Insights")
        
        col1, col2 = st.columns(2)
        
        with col1:
            avg_views_per_video = data['total_views'] / data['video_count']
            st.info(f"📊 **Average views per video:** {format_number(avg_views_per_video)}")
            
            engagement_rate = ((data['total_likes'] + data['total_comments']) / data['total_views'] * 100) if data['total_views'] > 0 else 0
            st.info(f"💬 **Engagement rate:** {engagement_rate:.2f}%")
        
        with col2:
            if data['total_impressions'] > 0:
                reach_efficiency = data['total_views'] / data['total_impressions'] * 100
                st.info(f"🎯 **Reach efficiency:** {reach_efficiency:.2f}%")
            
            if data['total_watch_time'] > 0 and data['total_views'] > 0:
                avg_session_duration = data['total_watch_time'] / data['total_views']
                st.info(f"⏰ **Avg session duration:** {format_duration(avg_session_duration)}")

if __name__ == "__main__":
    render_overview_page()