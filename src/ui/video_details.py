#!/usr/bin/env python3
"""
Video Details Page - Detailed analytics and insights for individual videos
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional, List

from ..storage import get_storage_adapter
from ..ai.gemini_client import get_insight_generator
from ..auth.youtube_auth import get_authenticator
from ..database.models import get_db_session, Video, VideoMetrics, Insight

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

@st.cache_data(ttl=300)
def get_video_details(video_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed information for a specific video."""
    session = get_db_session()
    
    try:
        # Get video basic info
        video = session.query(Video).filter(Video.video_id == video_id).first()
        
        if not video:
            return None
        
        video_data = {
            'video_id': video.video_id,
            'title': video.title,
            'description': video.description,
            'published_at': video.published_at,
            'thumbnail_url': video.thumbnail_url,
            'channel_id': video.channel_id
        }
        
        return video_data
        
    except Exception as e:
        st.error(f"Error loading video details: {e}")
        return None
    finally:
        session.close()

@st.cache_data(ttl=300)
def get_video_metrics_timeseries(video_id: str, start_date: date, end_date: date) -> pd.DataFrame:
    """Get time series metrics for a specific video."""
    session = get_db_session()
    
    try:
        metrics = session.query(VideoMetrics).filter(
            VideoMetrics.video_id == video_id,
            VideoMetrics.date >= start_date,
            VideoMetrics.date <= end_date
        ).order_by(VideoMetrics.date).all()
        
        if not metrics:
            return pd.DataFrame()
        
        data = []
        for metric in metrics:
            data.append({
                'date': metric.date,
                'impressions': metric.impressions,
                'views': metric.views,
                'ctr': (metric.views / metric.impressions * 100) if metric.impressions > 0 else 0,
                'avg_view_duration': metric.average_view_duration_seconds,
                'watch_time': metric.watch_time_minutes,
                'likes': metric.likes,
                'comments': metric.comments,
                'shares': metric.shares,
                'subscribers_gained': metric.subscribers_gained,
                'subscribers_lost': metric.subscribers_lost
            })
        
        return pd.DataFrame(data)
        
    except Exception as e:
        st.error(f"Error loading video metrics: {e}")
        return pd.DataFrame()
    finally:
        session.close()

@st.cache_data(ttl=300)
def get_video_insights(video_id: str) -> List[Dict[str, Any]]:
    """Get insights for a specific video."""
    session = get_db_session()
    
    try:
        insights = session.query(Insight).filter(
            Insight.video_id == video_id
        ).order_by(Insight.created_at.desc()).all()
        
        insights_data = []
        for insight in insights:
            insights_data.append({
                'id': insight.id,
                'action_type': insight.action_type,
                'priority': insight.priority,
                'confidence': insight.confidence,
                'rationale': insight.rationale,
                'payload_json': insight.payload_json,
                'created_at': insight.created_at
            })
        
        return insights_data
        
    except Exception as e:
        st.error(f"Error loading video insights: {e}")
        return []
    finally:
        session.close()

def render_video_header(video_data: Dict[str, Any]):
    """Render video header with basic info."""
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if video_data.get('thumbnail_url'):
            st.image(video_data['thumbnail_url'], width=300)
        else:
            st.write("🖼️ No thumbnail available")
    
    with col2:
        st.title(video_data['title'])
        
        if video_data.get('published_at'):
            published_date = video_data['published_at']
            if isinstance(published_date, str):
                published_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
            st.caption(f"📅 Published: {published_date.strftime('%B %d, %Y at %I:%M %p')}")
            
            days_ago = (datetime.now() - published_date.replace(tzinfo=None)).days
            st.caption(f"⏰ {days_ago} days ago")
        
        st.caption(f"🆔 Video ID: `{video_data['video_id']}`")
        
        if video_data.get('description'):
            with st.expander("📝 Description"):
                st.write(video_data['description'])

def render_video_metrics_summary(metrics_df: pd.DataFrame):
    """Render summary metrics for the video."""
    if metrics_df.empty:
        st.warning("No metrics data available for this video.")
        return
    
    # Calculate totals and averages
    total_impressions = metrics_df['impressions'].sum()
    total_views = metrics_df['views'].sum()
    avg_ctr = metrics_df['ctr'].mean()
    avg_view_duration = metrics_df['avg_view_duration'].mean()
    total_watch_time = metrics_df['watch_time'].sum()
    total_likes = metrics_df['likes'].sum()
    total_comments = metrics_df['comments'].sum()
    total_shares = metrics_df['shares'].sum()
    net_subscribers = metrics_df['subscribers_gained'].sum() - metrics_df['subscribers_lost'].sum()
    
    st.subheader("📊 Performance Summary")
    
    # KPI cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Impressions", format_number(total_impressions))
        st.metric("Total Views", format_number(total_views))
    
    with col2:
        st.metric("Average CTR", f"{avg_ctr:.2f}%")
        st.metric("Avg View Duration", format_duration(avg_view_duration))
    
    with col3:
        st.metric("Total Watch Time", format_duration(total_watch_time))
        st.metric("Total Likes", format_number(total_likes))
    
    with col4:
        st.metric("Total Comments", format_number(total_comments))
        st.metric("Net Subscribers", f"+{net_subscribers}" if net_subscribers >= 0 else str(net_subscribers))
    
    # Performance indicators
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if total_impressions > 0:
            reach_efficiency = total_views / total_impressions * 100
            st.info(f"🎯 **Reach Efficiency:** {reach_efficiency:.2f}%")
    
    with col2:
        if total_views > 0:
            engagement_rate = (total_likes + total_comments) / total_views * 100
            st.info(f"💬 **Engagement Rate:** {engagement_rate:.2f}%")
    
    with col3:
        if total_views > 0 and total_watch_time > 0:
            avg_session = total_watch_time / total_views
            st.info(f"⏰ **Avg Session:** {format_duration(avg_session)}")

def render_time_series_charts(metrics_df: pd.DataFrame):
    """Render time series charts for video metrics."""
    if metrics_df.empty:
        return
    
    st.subheader("📈 Performance Over Time")
    
    # Views and Impressions
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**👀 Views & Impressions**")
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=metrics_df['date'],
            y=metrics_df['views'],
            mode='lines+markers',
            name='Views',
            line=dict(color='#1f77b4')
        ))
        
        fig.add_trace(go.Scatter(
            x=metrics_df['date'],
            y=metrics_df['impressions'],
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
        st.write("**🎯 Click-Through Rate**")
        fig = px.line(
            metrics_df,
            x='date',
            y='ctr',
            title='CTR Over Time',
            labels={'ctr': 'CTR (%)', 'date': 'Date'}
        )
        fig.update_traces(line_color='#2ca02c')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Watch time and duration
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**⏰ Watch Time**")
        fig = px.bar(
            metrics_df,
            x='date',
            y='watch_time',
            title='Daily Watch Time',
            labels={'watch_time': 'Watch Time (seconds)', 'date': 'Date'}
        )
        fig.update_traces(marker_color='#d62728')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.write("**⏱️ Average View Duration**")
        fig = px.line(
            metrics_df,
            x='date',
            y='avg_view_duration',
            title='Avg View Duration Over Time',
            labels={'avg_view_duration': 'Duration (seconds)', 'date': 'Date'}
        )
        fig.update_traces(line_color='#9467bd')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Engagement metrics
    st.write("**💬 Engagement Metrics**")
    
    engagement_fig = go.Figure()
    
    engagement_fig.add_trace(go.Scatter(
        x=metrics_df['date'],
        y=metrics_df['likes'],
        mode='lines+markers',
        name='Likes',
        line=dict(color='#ff6b6b')
    ))
    
    engagement_fig.add_trace(go.Scatter(
        x=metrics_df['date'],
        y=metrics_df['comments'],
        mode='lines+markers',
        name='Comments',
        line=dict(color='#4ecdc4')
    ))
    
    engagement_fig.add_trace(go.Scatter(
        x=metrics_df['date'],
        y=metrics_df['shares'],
        mode='lines+markers',
        name='Shares',
        line=dict(color='#45b7d1')
    ))
    
    engagement_fig.update_layout(
        title="Engagement Over Time",
        xaxis_title="Date",
        yaxis_title="Count",
        hovermode='x unified',
        height=400
    )
    
    st.plotly_chart(engagement_fig, use_container_width=True)

def render_insights_section(video_id: str, insights: List[Dict[str, Any]]):
    """Render insights section with AI recommendations."""
    st.subheader("🤖 AI Insights & Recommendations")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("🔄 Generate New Insights", type="primary"):
            authenticator = get_authenticator()
            if not authenticator.is_authenticated():
                st.error("Please authenticate with YouTube first.")
            else:
                with st.spinner("Generating insights..."):
                    # Get video data for insight generation
                    video_data = get_video_details(video_id)
                    if video_data:
                        # Get recent metrics
                        end_date = date.today()
                        start_date = end_date - timedelta(days=30)
                        metrics_df = get_video_metrics_timeseries(video_id, start_date, end_date)
                        
                        if not metrics_df.empty:
                            # Prepare data for Gemini
                            total_impressions = metrics_df['impressions'].sum()
                            total_views = metrics_df['views'].sum()
                            avg_ctr = metrics_df['ctr'].mean()
                            avg_duration = metrics_df['avg_view_duration'].mean()
                            total_watch_time = metrics_df['watch_time'].sum()
                            
                            gemini_data = {
                                "video_id": video_id,
                                "channel_id": video_data["channel_id"],
                                "title": video_data["title"],
                                "impressions": int(total_impressions),
                                "views": int(total_views),
                                "ctr": float(avg_ctr),
                                "avg_view_duration_sec": float(avg_duration),
                                "watch_time": int(total_watch_time),
                                "published_at": video_data["published_at"].isoformat() if video_data.get("published_at") else None
                            }
                            
                            insight_generator = get_insight_generator()
                            response = insight_generator.generate_insights_for_video(gemini_data)
                            
                            if response.success:
                                st.success("✅ New insights generated!")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to generate insights: {'; '.join(response.errors)}")
                        else:
                            st.error("No metrics data available for insight generation.")
                    else:
                        st.error("Could not load video data.")
    
    if not insights:
        st.info("No insights available for this video. Generate some insights to see AI recommendations!")
        return
    
    # Display insights
    for insight in insights:
        with st.container():
            # Priority badge
            priority = insight['priority']
            priority_colors = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }
            
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                st.write(f"{priority_colors.get(priority, '⚪')} **{priority.upper()} Priority**")
                st.write(f"🎯 Confidence: {insight['confidence']:.0%}")
            
            with col2:
                st.write(f"**Action:** {insight['action_type'].replace('_', ' ').title()}")
                st.write(insight['rationale'])
            
            with col3:
                created_at = insight['created_at']
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                st.caption(f"Generated: {created_at.strftime('%Y-%m-%d %H:%M')}")
            
            # Show details if available
            if insight.get('payload_json') and insight['payload_json'].get('details'):
                with st.expander("📋 Detailed Recommendations"):
                    details = insight['payload_json']['details']
                    for key, value in details.items():
                        if isinstance(value, (list, dict)):
                            st.json(value)
                        else:
                            st.write(f"**{key.replace('_', ' ').title()}:** {value}")
            
            st.divider()

def render_video_details_page():
    """Render the video details page."""
    # Check if we have a selected video
    video_id = st.session_state.get('selected_video_id')
    
    if not video_id:
        st.warning("📹 No video selected")
        
        st.markdown("""
        ### How to select a video:
        
        1. **Go to the Videos page** using the sidebar navigation
        2. **Browse your videos** in the table
        3. **Click the "📊 Details" button** next to any video you want to analyze
        4. **You'll be automatically redirected** to this page with the selected video
        
        💡 **Tip**: You can also use the search and filter options on the Videos page to find specific videos quickly.
        """)
        
        # Debug information (can be removed in production)
        with st.expander("🔧 Debug Information", expanded=False):
            st.write("**Current session state:**")
            st.json({
                'current_page': st.session_state.get('current_page', 'Not set'),
                'selected_video_id': st.session_state.get('selected_video_id', 'Not set'),
                'all_session_keys': list(st.session_state.keys())
            })
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔍 Go to Videos Page", use_container_width=True):
                st.session_state['current_page'] = 'videos'
                st.rerun()
        return
    
    # Back button
    if st.button("← Back to Videos"):
        st.session_state['current_page'] = 'videos'
        st.rerun()
    
    # Load video data
    video_data = get_video_details(video_id)
    
    if not video_data:
        st.error(f"Video with ID '{video_id}' not found.")
        return
    
    # Render video header
    render_video_header(video_data)
    
    st.divider()
    
    # Date range selector for metrics
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=date.today() - timedelta(days=30),
            max_value=date.today(),
            key="video_details_start_date"
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=date.today(),
            max_value=date.today(),
            key="video_details_end_date"
        )
    
    if start_date > end_date:
        st.error("Start date must be before end date.")
        return
    
    # Load metrics and insights
    with st.spinner("Loading video analytics..."):
        metrics_df = get_video_metrics_timeseries(video_id, start_date, end_date)
        insights = get_video_insights(video_id)
    
    # Render metrics summary
    render_video_metrics_summary(metrics_df)
    
    st.divider()
    
    # Render time series charts
    render_time_series_charts(metrics_df)
    
    st.divider()
    
    # Render insights section
    render_insights_section(video_id, insights)

if __name__ == "__main__":
    render_video_details_page()