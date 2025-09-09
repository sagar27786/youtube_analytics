#!/usr/bin/env python3
"""
UI Components - Reusable Streamlit components for charts, KPIs, and visualizations
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import numpy as np

def format_number(value: Union[int, float], format_type: str = "auto") -> str:
    """Format numbers for display with appropriate units."""
    if pd.isna(value) or value is None:
        return "N/A"
    
    if format_type == "percentage":
        return f"{value:.1%}"
    elif format_type == "duration":
        # Convert seconds to readable format
        if value < 60:
            return f"{value:.0f}s"
        elif value < 3600:
            return f"{value/60:.1f}m"
        else:
            return f"{value/3600:.1f}h"
    elif format_type == "currency":
        return f"${value:,.2f}"
    else:
        # Auto format based on magnitude
        if abs(value) >= 1_000_000:
            return f"{value/1_000_000:.1f}M"
        elif abs(value) >= 1_000:
            return f"{value/1_000:.1f}K"
        else:
            return f"{value:,.0f}"

def create_kpi_card(title: str, value: Union[int, float], 
                   delta: Optional[Union[int, float]] = None,
                   format_type: str = "auto",
                   help_text: Optional[str] = None) -> None:
    """Create a KPI card with title, value, and optional delta."""
    
    formatted_value = format_number(value, format_type)
    
    if delta is not None:
        formatted_delta = format_number(delta, format_type)
        delta_color = "normal" if delta >= 0 else "inverse"
        
        st.metric(
            label=title,
            value=formatted_value,
            delta=formatted_delta,
            delta_color=delta_color,
            help=help_text
        )
    else:
        st.metric(
            label=title,
            value=formatted_value,
            help=help_text
        )

def create_time_series_chart(df: pd.DataFrame, 
                           x_col: str, 
                           y_cols: Union[str, List[str]],
                           title: str,
                           y_title: Optional[str] = None,
                           chart_type: str = "line",
                           height: int = 400) -> go.Figure:
    """Create a time series chart with one or multiple y-axis variables."""
    
    if isinstance(y_cols, str):
        y_cols = [y_cols]
    
    fig = go.Figure()
    
    colors = px.colors.qualitative.Set1
    
    for i, y_col in enumerate(y_cols):
        if chart_type == "line":
            fig.add_trace(go.Scatter(
                x=df[x_col],
                y=df[y_col],
                mode='lines+markers',
                name=y_col.replace('_', ' ').title(),
                line=dict(color=colors[i % len(colors)]),
                hovertemplate=f'<b>{y_col.replace("_", " ").title()}</b><br>' +
                             f'{x_col}: %{{x}}<br>' +
                             f'Value: %{{y:,.0f}}<extra></extra>'
            ))
        elif chart_type == "bar":
            fig.add_trace(go.Bar(
                x=df[x_col],
                y=df[y_col],
                name=y_col.replace('_', ' ').title(),
                marker_color=colors[i % len(colors)],
                hovertemplate=f'<b>{y_col.replace("_", " ").title()}</b><br>' +
                             f'{x_col}: %{{x}}<br>' +
                             f'Value: %{{y:,.0f}}<extra></extra>'
            ))
    
    fig.update_layout(
        title=title,
        xaxis_title=x_col.replace('_', ' ').title(),
        yaxis_title=y_title or 'Value',
        height=height,
        hovermode='x unified',
        showlegend=len(y_cols) > 1
    )
    
    return fig

def create_dual_axis_chart(df: pd.DataFrame,
                          x_col: str,
                          y1_col: str,
                          y2_col: str,
                          title: str,
                          y1_title: str,
                          y2_title: str,
                          height: int = 400) -> go.Figure:
    """Create a chart with dual y-axes."""
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add first trace
    fig.add_trace(
        go.Scatter(
            x=df[x_col],
            y=df[y1_col],
            mode='lines+markers',
            name=y1_title,
            line=dict(color='#1f77b4'),
            hovertemplate=f'<b>{y1_title}</b><br>' +
                         f'{x_col}: %{{x}}<br>' +
                         f'Value: %{{y:,.2f}}<extra></extra>'
        ),
        secondary_y=False,
    )
    
    # Add second trace
    fig.add_trace(
        go.Scatter(
            x=df[x_col],
            y=df[y2_col],
            mode='lines+markers',
            name=y2_title,
            line=dict(color='#ff7f0e'),
            hovertemplate=f'<b>{y2_title}</b><br>' +
                         f'{x_col}: %{{x}}<br>' +
                         f'Value: %{{y:,.2f}}<extra></extra>'
        ),
        secondary_y=True,
    )
    
    # Set y-axes titles
    fig.update_yaxes(title_text=y1_title, secondary_y=False)
    fig.update_yaxes(title_text=y2_title, secondary_y=True)
    
    fig.update_layout(
        title=title,
        xaxis_title=x_col.replace('_', ' ').title(),
        height=height,
        hovermode='x unified'
    )
    
    return fig

def create_distribution_chart(df: pd.DataFrame,
                            value_col: str,
                            title: str,
                            chart_type: str = "histogram",
                            bins: int = 20,
                            height: int = 400) -> go.Figure:
    """Create a distribution chart (histogram or box plot)."""
    
    fig = go.Figure()
    
    if chart_type == "histogram":
        fig.add_trace(go.Histogram(
            x=df[value_col],
            nbinsx=bins,
            name="Distribution",
            marker_color='#1f77b4',
            opacity=0.7,
            hovertemplate='Range: %{x}<br>Count: %{y}<extra></extra>'
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title=value_col.replace('_', ' ').title(),
            yaxis_title='Count',
            height=height
        )
        
    elif chart_type == "box":
        fig.add_trace(go.Box(
            y=df[value_col],
            name="Distribution",
            marker_color='#1f77b4',
            hovertemplate='Value: %{y:,.2f}<extra></extra>'
        ))
        
        fig.update_layout(
            title=title,
            yaxis_title=value_col.replace('_', ' ').title(),
            height=height
        )
    
    return fig

def create_correlation_heatmap(df: pd.DataFrame,
                              columns: List[str],
                              title: str,
                              height: int = 500) -> go.Figure:
    """Create a correlation heatmap."""
    
    # Calculate correlation matrix
    corr_matrix = df[columns].corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=[col.replace('_', ' ').title() for col in corr_matrix.columns],
        y=[col.replace('_', ' ').title() for col in corr_matrix.index],
        colorscale='RdBu',
        zmid=0,
        text=np.round(corr_matrix.values, 2),
        texttemplate="%{text}",
        textfont={"size": 10},
        hovertemplate='%{x} vs %{y}<br>Correlation: %{z:.3f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=title,
        height=height,
        xaxis_title="",
        yaxis_title=""
    )
    
    return fig

def create_top_n_chart(df: pd.DataFrame,
                       category_col: str,
                       value_col: str,
                       title: str,
                       n: int = 10,
                       orientation: str = "horizontal",
                       height: int = 400) -> go.Figure:
    """Create a top N chart (bar chart)."""
    
    # Sort and take top N
    top_df = df.nlargest(n, value_col)
    
    if orientation == "horizontal":
        fig = go.Figure(go.Bar(
            x=top_df[value_col],
            y=top_df[category_col],
            orientation='h',
            marker_color='#1f77b4',
            hovertemplate='<b>%{y}</b><br>' +
                         f'{value_col.replace("_", " ").title()}: %{{x:,.0f}}<extra></extra>'
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title=value_col.replace('_', ' ').title(),
            yaxis_title="",
            height=height,
            yaxis={'categoryorder': 'total ascending'}
        )
    else:
        fig = go.Figure(go.Bar(
            x=top_df[category_col],
            y=top_df[value_col],
            marker_color='#1f77b4',
            hovertemplate='<b>%{x}</b><br>' +
                         f'{value_col.replace("_", " ").title()}: %{{y:,.0f}}<extra></extra>'
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="",
            yaxis_title=value_col.replace('_', ' ').title(),
            height=height,
            xaxis={'categoryorder': 'total descending'}
        )
    
    return fig

def create_gauge_chart(value: float,
                      title: str,
                      min_val: float = 0,
                      max_val: float = 100,
                      threshold_good: float = 70,
                      threshold_fair: float = 40,
                      height: int = 300) -> go.Figure:
    """Create a gauge chart for KPI visualization."""
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title},
        gauge={
            'axis': {'range': [None, max_val]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [min_val, threshold_fair], 'color': "lightgray"},
                {'range': [threshold_fair, threshold_good], 'color': "yellow"},
                {'range': [threshold_good, max_val], 'color': "green"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': threshold_good
            }
        }
    ))
    
    fig.update_layout(height=height)
    
    return fig

def create_funnel_chart(df: pd.DataFrame,
                       stage_col: str,
                       value_col: str,
                       title: str,
                       height: int = 400) -> go.Figure:
    """Create a funnel chart for conversion analysis."""
    
    fig = go.Figure(go.Funnel(
        y=df[stage_col],
        x=df[value_col],
        textinfo="value+percent initial",
        hovertemplate='<b>%{y}</b><br>' +
                     f'Value: %{{x:,.0f}}<br>' +
                     'Percent of Initial: %{percentInitial}<br>' +
                     'Percent of Previous: %{percentPrevious}<extra></extra>'
    ))
    
    fig.update_layout(
        title=title,
        height=height
    )
    
    return fig

def create_performance_summary_cards(df: pd.DataFrame, 
                                    date_col: str = 'date',
                                    comparison_days: int = 7) -> None:
    """Create a set of performance summary KPI cards with period comparison."""
    
    if df.empty:
        st.warning("No data available for performance summary.")
        return
    
    # Calculate current period and comparison period
    df[date_col] = pd.to_datetime(df[date_col])
    latest_date = df[date_col].max()
    comparison_date = latest_date - timedelta(days=comparison_days)
    
    current_period = df[df[date_col] > comparison_date]
    previous_period = df[
        (df[date_col] <= comparison_date) & 
        (df[date_col] > comparison_date - timedelta(days=comparison_days))
    ]
    
    # Define metrics to display
    metrics = [
        ('views', 'Views', 'auto'),
        ('impressions', 'Impressions', 'auto'),
        ('impressions_ctr', 'CTR', 'percentage'),
        ('average_view_duration', 'Avg View Duration', 'duration'),
        ('watch_time', 'Watch Time', 'duration'),
        ('likes', 'Likes', 'auto'),
        ('comments', 'Comments', 'auto'),
        ('subscribers_gained', 'Subscribers Gained', 'auto')
    ]
    
    # Create columns for KPI cards
    cols = st.columns(4)
    
    for i, (metric, title, format_type) in enumerate(metrics):
        if metric in df.columns:
            current_value = current_period[metric].sum() if not current_period.empty else 0
            previous_value = previous_period[metric].sum() if not previous_period.empty else 0
            
            delta = current_value - previous_value if previous_value > 0 else None
            
            with cols[i % 4]:
                create_kpi_card(
                    title=title,
                    value=current_value,
                    delta=delta,
                    format_type=format_type,
                    help_text=f"Compared to previous {comparison_days} days"
                )

def create_engagement_metrics_chart(df: pd.DataFrame,
                                  date_col: str = 'date',
                                  height: int = 400) -> go.Figure:
    """Create a comprehensive engagement metrics chart."""
    
    # Calculate engagement rate
    df['engagement_rate'] = (df['likes'] + df['comments'] + df['shares']) / df['views']
    
    # Create subplot with secondary y-axis
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Engagement Actions', 'Engagement Rate'),
        vertical_spacing=0.1,
        specs=[[{"secondary_y": False}],
               [{"secondary_y": False}]]
    )
    
    # Add engagement actions (stacked bar)
    fig.add_trace(
        go.Bar(x=df[date_col], y=df['likes'], name='Likes', marker_color='#1f77b4'),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(x=df[date_col], y=df['comments'], name='Comments', marker_color='#ff7f0e'),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(x=df[date_col], y=df['shares'], name='Shares', marker_color='#2ca02c'),
        row=1, col=1
    )
    
    # Add engagement rate line
    fig.add_trace(
        go.Scatter(
            x=df[date_col], 
            y=df['engagement_rate'], 
            mode='lines+markers',
            name='Engagement Rate',
            line=dict(color='#d62728'),
            hovertemplate='Date: %{x}<br>Engagement Rate: %{y:.2%}<extra></extra>'
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=height,
        title_text="Engagement Metrics Overview",
        showlegend=True
    )
    
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Count", row=1, col=1)
    fig.update_yaxes(title_text="Engagement Rate", row=2, col=1)
    
    return fig

def display_video_thumbnail(video_id: str, 
                          thumbnail_url: Optional[str] = None,
                          width: int = 120) -> None:
    """Display video thumbnail with fallback."""
    
    if thumbnail_url:
        try:
            st.image(thumbnail_url, width=width)
        except Exception:
            # Fallback to YouTube thumbnail
            fallback_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
            st.image(fallback_url, width=width)
    else:
        # Use YouTube thumbnail
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
        st.image(thumbnail_url, width=width)

def create_data_quality_indicators(df: pd.DataFrame) -> None:
    """Display data quality indicators."""
    
    if df.empty:
        st.error("❌ No data available")
        return
    
    total_records = len(df)
    missing_data = df.isnull().sum().sum()
    completeness = (1 - missing_data / (total_records * len(df.columns))) * 100
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Records", f"{total_records:,}")
    
    with col2:
        st.metric("Missing Values", f"{missing_data:,}")
    
    with col3:
        st.metric("Data Completeness", f"{completeness:.1f}%")
    
    with col4:
        if 'date' in df.columns:
            date_range = (pd.to_datetime(df['date']).max() - pd.to_datetime(df['date']).min()).days
            st.metric("Date Range", f"{date_range} days")
        else:
            st.metric("Columns", len(df.columns))

def create_trend_indicator(current_value: float, 
                         previous_value: float,
                         format_type: str = "auto") -> str:
    """Create a trend indicator with emoji and formatted change."""
    
    if previous_value == 0:
        return "🆕 New"
    
    change = current_value - previous_value
    percent_change = (change / previous_value) * 100
    
    if abs(percent_change) < 1:
        emoji = "➡️"
        trend = "Stable"
    elif percent_change > 0:
        emoji = "📈"
        trend = f"+{percent_change:.1f}%"
    else:
        emoji = "📉"
        trend = f"{percent_change:.1f}%"
    
    return f"{emoji} {trend}"