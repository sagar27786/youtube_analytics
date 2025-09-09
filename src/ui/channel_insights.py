#!/usr/bin/env python3
"""
Channel Insights Page - AI-generated channel-level recommendations and analytics
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional, List
import json

from ..storage import get_storage_adapter
from ..ai.gemini_client import get_insight_generator
from ..auth.youtube_auth import get_authenticator
from ..ingestion.youtube_data import get_ingester
from ..database.models import get_db_session, VideoMetrics, Insight, Video

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
def get_channel_summary(start_date: date, end_date: date) -> Dict[str, Any]:
    """Get channel-level summary data for the specified date range."""
    session = get_db_session()
    
    try:
        # Get aggregated metrics
        metrics_query = session.query(VideoMetrics).filter(
            VideoMetrics.date >= start_date,
            VideoMetrics.date <= end_date
        )
        
        metrics_df = pd.read_sql(metrics_query.statement, session.bind)
        
        if metrics_df.empty:
            return {}
        
        # Get channel ID (assuming all videos belong to the same channel)
        channel_id = metrics_df['channel_id'].iloc[0] if 'channel_id' in metrics_df.columns else "unknown"
        
        # Calculate aggregated metrics
        total_impressions = metrics_df['impressions'].sum()
        total_views = metrics_df['views'].sum()
        avg_ctr = (total_views / total_impressions * 100) if total_impressions > 0 else 0
        avg_view_duration = metrics_df['average_view_duration_seconds'].mean()
        total_watch_time = metrics_df['watch_time_minutes'].sum()
        total_likes = metrics_df['likes'].sum()
        total_comments = metrics_df['comments'].sum()
        total_shares = metrics_df['shares'].sum()
        subscribers_gained = metrics_df['subscribers_gained'].sum()
        subscribers_lost = metrics_df['subscribers_lost'].sum()
        net_subscribers = subscribers_gained - subscribers_lost
        
        # Get top performing videos
        video_performance = metrics_df.groupby('video_id').agg({
            'impressions': 'sum',
            'views': 'sum',
            'watch_time_minutes': 'sum',
            'average_view_duration_seconds': 'mean',
            'likes': 'sum',
            'comments': 'sum'
        }).reset_index()
        
        # Get video details
        video_ids = video_performance['video_id'].tolist()
        videos_query = session.query(Video).filter(Video.video_id.in_(video_ids))
        videos_df = pd.read_sql(videos_query.statement, session.bind)
        
        top_videos = video_performance.merge(videos_df, on='video_id', how='left')
        top_videos['ctr'] = (top_videos['views'] / top_videos['impressions'] * 100).fillna(0)
        top_videos = top_videos.sort_values('views', ascending=False).head(10)
        
        # Convert to list of dicts for Gemini
        top_videos_list = []
        for _, row in top_videos.iterrows():
            top_videos_list.append({
                "video_id": row['video_id'],
                "title": row['title'],
                "impressions": int(row['impressions']),
                "views": int(row['views']),
                "ctr": float(row['ctr']),
                "watch_time": int(row['watch_time_minutes'] * 60),  # Convert minutes to seconds
                "avg_view_duration": float(row['average_view_duration_seconds']),
                "likes": int(row['likes']),
                "comments": int(row['comments'])
            })
        
        return {
            'channel_id': channel_id,
            'date_range': f"{start_date} to {end_date}",
            'aggregates': {
                'impressions': int(total_impressions),
                'views': int(total_views),
                'ctr': float(avg_ctr),
                'avg_view_duration_sec': float(avg_view_duration),
                'watch_time': int(total_watch_time * 60),  # Convert minutes to seconds for format_duration
                'likes': int(total_likes),
                'comments': int(total_comments),
                'shares': int(total_shares),
                'subscribers_gained': int(subscribers_gained),
                'subscribers_lost': int(subscribers_lost),
                'subs_change': int(net_subscribers)
            },
            'top_videos': top_videos_list,
            'video_count': len(video_performance),
            'metrics_df': metrics_df
        }
        
    except Exception as e:
        st.error(f"Error loading channel summary: {e}")
        return {}
    finally:
        session.close()

@st.cache_data(ttl=300)
def get_channel_insights() -> List[Dict[str, Any]]:
    """Get channel-level insights from the database."""
    session = get_db_session()
    
    try:
        insights = session.query(Insight).filter(
            Insight.video_id.is_(None)  # Channel-level insights have no video_id
        ).order_by(Insight.created_at.desc()).limit(20).all()
        
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
        st.error(f"Error loading channel insights: {e}")
        return []
    finally:
        session.close()

def generate_channel_insights(channel_data: Dict[str, Any]) -> bool:
    """Generate new channel-level insights using Gemini AI."""
    try:
        insight_generator = get_insight_generator()
        response = insight_generator.generate_insights_for_channel(channel_data)
        return response.success
    except Exception as e:
        st.error(f"Error generating channel insights: {e}")
        return False

def render_channel_overview(channel_data: Dict[str, Any]):
    """Render channel overview metrics."""
    if not channel_data or not channel_data.get('aggregates'):
        st.warning("No channel data available for the selected date range.")
        return
    
    aggregates = channel_data['aggregates']
    
    st.subheader("📊 Channel Performance Overview")
    
    # KPI cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Impressions", format_number(aggregates['impressions']))
        st.metric("Total Views", format_number(aggregates['views']))
    
    with col2:
        st.metric("Average CTR", f"{aggregates['ctr']:.2f}%")
        st.metric("Avg View Duration", format_duration(aggregates['avg_view_duration_sec']))
    
    with col3:
        st.metric("Total Watch Time", format_duration(aggregates['watch_time']))
        st.metric("Total Likes", format_number(aggregates['likes']))
    
    with col4:
        st.metric("Total Comments", format_number(aggregates['comments']))
        st.metric(
            "Net Subscribers", 
            f"+{aggregates['subs_change']}" if aggregates['subs_change'] >= 0 else str(aggregates['subs_change']),
            delta=aggregates['subs_change']
        )
    
    # Performance indicators
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if aggregates['impressions'] > 0:
            reach_efficiency = aggregates['views'] / aggregates['impressions'] * 100
            st.info(f"🎯 **Reach Efficiency:** {reach_efficiency:.2f}%")
    
    with col2:
        if aggregates['views'] > 0:
            engagement_rate = (aggregates['likes'] + aggregates['comments']) / aggregates['views'] * 100
            st.info(f"💬 **Engagement Rate:** {engagement_rate:.2f}%")
    
    with col3:
        video_count = channel_data.get('video_count', 0)
        if video_count > 0:
            avg_views_per_video = aggregates['views'] / video_count
            st.info(f"📹 **Avg Views/Video:** {format_number(avg_views_per_video)}")

def render_top_videos_analysis(channel_data: Dict[str, Any]):
    """Render top videos analysis."""
    top_videos = channel_data.get('top_videos', [])
    
    if not top_videos:
        st.info("No video data available.")
        return
    
    st.subheader("🏆 Top Performing Videos Analysis")
    
    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(top_videos)
    
    # Performance distribution charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📊 Views Distribution**")
        fig = px.bar(
            df.head(10),
            x='title',
            y='views',
            title='Top 10 Videos by Views',
            labels={'views': 'Views', 'title': 'Video Title'}
        )
        fig.update_xaxes(tickangle=45)
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.write("**🎯 CTR vs Views**")
        fig = px.scatter(
            df,
            x='views',
            y='ctr',
            size='watch_time',
            hover_data=['title'],
            title='CTR vs Views (bubble size = watch time)',
            labels={'views': 'Views', 'ctr': 'CTR (%)'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Top videos table
    st.write("**📋 Top Videos Details**")
    
    display_df = df[['title', 'views', 'impressions', 'ctr', 'watch_time', 'likes', 'comments']].copy()
    display_df['views'] = display_df['views'].apply(format_number)
    display_df['impressions'] = display_df['impressions'].apply(format_number)
    display_df['ctr'] = display_df['ctr'].apply(lambda x: f"{x:.2f}%")
    display_df['watch_time'] = display_df['watch_time'].apply(format_duration)
    display_df['likes'] = display_df['likes'].apply(format_number)
    display_df['comments'] = display_df['comments'].apply(format_number)
    
    display_df.columns = ['Title', 'Views', 'Impressions', 'CTR', 'Watch Time', 'Likes', 'Comments']
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

def render_channel_trends(channel_data: Dict[str, Any]):
    """Render channel performance trends."""
    metrics_df = channel_data.get('metrics_df')
    
    if metrics_df is None or metrics_df.empty:
        return
    
    st.subheader("📈 Channel Performance Trends")
    
    # Daily aggregated metrics
    daily_metrics = metrics_df.groupby('date').agg({
        'impressions': 'sum',
        'views': 'sum',
        'watch_time_minutes': 'sum',
        'likes': 'sum',
        'comments': 'sum',
        'subscribers_gained': 'sum',
        'subscribers_lost': 'sum'
    }).reset_index()
    
    daily_metrics['ctr'] = (daily_metrics['views'] / daily_metrics['impressions'] * 100).fillna(0)
    daily_metrics['net_subscribers'] = daily_metrics['subscribers_gained'] - daily_metrics['subscribers_lost']
    
    # Performance trends
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**👀 Daily Views & Impressions**")
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
        st.write("**📈 Subscriber Growth**")
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=daily_metrics['date'],
            y=daily_metrics['subscribers_gained'],
            mode='lines+markers',
            name='Gained',
            line=dict(color='#2ca02c')
        ))
        
        fig.add_trace(go.Scatter(
            x=daily_metrics['date'],
            y=daily_metrics['subscribers_lost'],
            mode='lines+markers',
            name='Lost',
            line=dict(color='#d62728')
        ))
        
        fig.add_trace(go.Scatter(
            x=daily_metrics['date'],
            y=daily_metrics['net_subscribers'],
            mode='lines+markers',
            name='Net Change',
            line=dict(color='#9467bd', width=3)
        ))
        
        fig.update_layout(
            title="Daily Subscriber Changes",
            xaxis_title="Date",
            yaxis_title="Subscribers",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Engagement trends
    st.write("**💬 Engagement Trends**")
    
    engagement_fig = go.Figure()
    
    engagement_fig.add_trace(go.Scatter(
        x=daily_metrics['date'],
        y=daily_metrics['likes'],
        mode='lines+markers',
        name='Likes',
        line=dict(color='#ff6b6b')
    ))
    
    engagement_fig.add_trace(go.Scatter(
        x=daily_metrics['date'],
        y=daily_metrics['comments'],
        mode='lines+markers',
        name='Comments',
        line=dict(color='#4ecdc4')
    ))
    
    engagement_fig.update_layout(
        title="Daily Engagement Metrics",
        xaxis_title="Date",
        yaxis_title="Count",
        hovermode='x unified',
        height=400
    )
    
    st.plotly_chart(engagement_fig, use_container_width=True)

def render_insights_section(insights: List[Dict[str, Any]], channel_data: Dict[str, Any]):
    """Render AI insights section."""
    st.subheader("🤖 AI-Generated Channel Insights")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("🔄 Generate New Insights", type="primary"):
            authenticator = get_authenticator()
            if not authenticator.is_authenticated():
                st.error("Please authenticate with YouTube first.")
            else:
                if channel_data:
                    with st.spinner("Generating channel insights..."):
                        if generate_channel_insights(channel_data):
                            st.success("✅ New insights generated!")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("❌ Failed to generate insights")
                else:
                    st.error("No channel data available for insight generation.")
    
    if not insights:
        st.info("No channel insights available. Generate some insights to see AI recommendations for your channel!")
        return
    
    # Group insights by priority
    high_priority = [i for i in insights if i['priority'] == 'high']
    medium_priority = [i for i in insights if i['priority'] == 'medium']
    low_priority = [i for i in insights if i['priority'] == 'low']
    
    # Priority tabs
    tab1, tab2, tab3 = st.tabs([f"🔴 High Priority ({len(high_priority)})", f"🟡 Medium Priority ({len(medium_priority)})", f"🟢 Low Priority ({len(low_priority)})"])
    
    def render_insights_list(insights_list: List[Dict[str, Any]]):
        if not insights_list:
            st.info("No insights in this priority category.")
            return
        
        for insight in insights_list:
            with st.container():
                col1, col2, col3 = st.columns([2, 3, 1])
                
                with col1:
                    st.write(f"**{insight['action_type'].replace('_', ' ').title()}**")
                    st.write(f"🎯 Confidence: {insight['confidence']:.0%}")
                
                with col2:
                    st.write(insight['rationale'])
                
                with col3:
                    created_at = insight['created_at']
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    st.caption(f"Generated: {created_at.strftime('%Y-%m-%d %H:%M')}")
                
                # Show details and recommended videos
                if insight.get('payload_json'):
                    payload = insight['payload_json']
                    
                    with st.expander("📋 Detailed Recommendations"):
                        if payload.get('details'):
                            details = payload['details']
                            for key, value in details.items():
                                if isinstance(value, (list, dict)):
                                    st.write(f"**{key.replace('_', ' ').title()}:**")
                                    st.json(value)
                                else:
                                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                        
                        if payload.get('recommended_videos'):
                            st.write("**🎬 Recommended Videos:**")
                            for video_id in payload['recommended_videos']:
                                st.write(f"- `{video_id}`")
                
                st.divider()
    
    with tab1:
        render_insights_list(high_priority)
    
    with tab2:
        render_insights_list(medium_priority)
    
    with tab3:
        render_insights_list(low_priority)

def render_channel_insights_page():
    """Render the channel insights page."""
    st.title("🏢 Channel Insights & Analytics")
    
    # Date range selector
    col1, col2, col3 = st.columns([2, 2, 2])
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=date.today() - timedelta(days=30),
            max_value=date.today(),
            key="channel_insights_start_date"
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=date.today(),
            max_value=date.today(),
            key="channel_insights_end_date"
        )
    
    with col3:
        st.write("")
        st.write("")
        if st.button("🔄 Refresh Channel Data"):
            st.cache_data.clear()
            st.rerun()
    
    # Validate date range
    if start_date > end_date:
        st.error("Start date must be before end date.")
        return
    
    # Load data
    with st.spinner("Loading channel analytics..."):
        channel_data = get_channel_summary(start_date, end_date)
        insights = get_channel_insights()
    
    # Render sections
    render_channel_overview(channel_data)
    
    st.divider()
    
    render_top_videos_analysis(channel_data)
    
    st.divider()
    
    render_channel_trends(channel_data)
    
    st.divider()
    
    render_insights_section(insights, channel_data)

if __name__ == "__main__":
    render_channel_insights_page()