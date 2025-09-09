#!/usr/bin/env python3
"""
Unit tests for Streamlit UI components
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ui.components import (
    format_number, create_kpi_card, create_time_series_chart,
    create_dual_axis_chart, create_distribution_chart, create_correlation_heatmap,
    create_top_n_chart, create_gauge_chart, create_funnel_chart,
    create_performance_summary_cards, create_engagement_metrics_chart,
    display_video_thumbnail, create_data_quality_indicator, create_trend_indicator
)

class TestNumberFormatting:
    """Test cases for number formatting utilities."""
    
    def test_format_number_basic(self):
        """Test basic number formatting."""
        assert format_number(1234) == "1.2K"
        assert format_number(1234567) == "1.2M"
        assert format_number(1234567890) == "1.2B"
        assert format_number(123) == "123"
    
    def test_format_number_edge_cases(self):
        """Test edge cases for number formatting."""
        assert format_number(0) == "0"
        assert format_number(999) == "999"
        assert format_number(1000) == "1.0K"
        assert format_number(1500) == "1.5K"
        assert format_number(999999) == "1000.0K"
        assert format_number(1000000) == "1.0M"
    
    def test_format_number_negative(self):
        """Test negative number formatting."""
        assert format_number(-1234) == "-1.2K"
        assert format_number(-1234567) == "-1.2M"
    
    def test_format_number_float(self):
        """Test float number formatting."""
        assert format_number(1234.56) == "1.2K"
        assert format_number(1234567.89) == "1.2M"
    
    def test_format_number_precision(self):
        """Test number formatting with different precision."""
        assert format_number(1234, precision=0) == "1K"
        assert format_number(1234, precision=2) == "1.23K"
        assert format_number(1234567, precision=3) == "1.235M"

class TestKPICards:
    """Test cases for KPI card creation."""
    
    @patch('src.ui.components.st')
    def test_create_kpi_card_basic(self, mock_st):
        """Test basic KPI card creation."""
        # Mock streamlit components
        mock_col = Mock()
        mock_st.columns.return_value = [mock_col]
        
        create_kpi_card("Views", 12345, "👁️")
        
        # Verify streamlit functions were called
        mock_st.columns.assert_called_once_with(1)
        mock_col.metric.assert_called_once_with(
            label="👁️ Views",
            value="12.3K",
            delta=None
        )
    
    @patch('src.ui.components.st')
    def test_create_kpi_card_with_delta(self, mock_st):
        """Test KPI card creation with delta value."""
        mock_col = Mock()
        mock_st.columns.return_value = [mock_col]
        
        create_kpi_card("Subscribers", 1000, "👥", delta=50)
        
        mock_col.metric.assert_called_once_with(
            label="👥 Subscribers",
            value="1.0K",
            delta="50"
        )
    
    @patch('src.ui.components.st')
    def test_create_kpi_card_with_percentage_delta(self, mock_st):
        """Test KPI card creation with percentage delta."""
        mock_col = Mock()
        mock_st.columns.return_value = [mock_col]
        
        create_kpi_card("CTR", 0.05, "📊", delta=0.01, delta_format="percentage")
        
        mock_col.metric.assert_called_once_with(
            label="📊 CTR",
            value="5.0%",
            delta="1.0%"
        )
    
    @patch('src.ui.components.st')
    def test_create_kpi_card_custom_format(self, mock_st):
        """Test KPI card creation with custom value format."""
        mock_col = Mock()
        mock_st.columns.return_value = [mock_col]
        
        create_kpi_card("Duration", 125.5, "⏱️", value_format="duration")
        
        mock_col.metric.assert_called_once_with(
            label="⏱️ Duration",
            value="2:05",
            delta=None
        )

class TestChartCreation:
    """Test cases for chart creation functions."""
    
    def test_create_time_series_chart_basic(self):
        """Test basic time series chart creation."""
        # Create sample data
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        data = pd.DataFrame({
            'date': dates,
            'views': np.random.randint(100, 1000, 10),
            'impressions': np.random.randint(1000, 5000, 10)
        })
        
        fig = create_time_series_chart(
            data=data,
            x_col='date',
            y_cols=['views', 'impressions'],
            title="Test Chart"
        )
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2  # Two traces
        assert fig.layout.title.text == "Test Chart"
    
    def test_create_time_series_chart_single_metric(self):
        """Test time series chart with single metric."""
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        data = pd.DataFrame({
            'date': dates,
            'views': [100, 150, 200, 180, 220]
        })
        
        fig = create_time_series_chart(
            data=data,
            x_col='date',
            y_cols=['views'],
            title="Views Over Time"
        )
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert fig.data[0].name == 'views'
    
    def test_create_dual_axis_chart(self):
        """Test dual axis chart creation."""
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        data = pd.DataFrame({
            'date': dates,
            'views': np.random.randint(100, 1000, 10),
            'ctr': np.random.uniform(0.01, 0.1, 10)
        })
        
        fig = create_dual_axis_chart(
            data=data,
            x_col='date',
            y1_col='views',
            y2_col='ctr',
            title="Views vs CTR"
        )
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2
        assert fig.layout.title.text == "Views vs CTR"
        # Check for secondary y-axis
        assert fig.layout.yaxis2 is not None
    
    def test_create_distribution_chart(self):
        """Test distribution chart creation."""
        data = pd.DataFrame({
            'category': ['A', 'B', 'C', 'D'],
            'values': [25, 35, 20, 20]
        })
        
        fig = create_distribution_chart(
            data=data,
            labels_col='category',
            values_col='values',
            title="Distribution Test"
        )
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert fig.data[0].type == 'pie'
        assert fig.layout.title.text == "Distribution Test"
    
    def test_create_correlation_heatmap(self):
        """Test correlation heatmap creation."""
        data = pd.DataFrame({
            'views': np.random.randint(100, 1000, 50),
            'likes': np.random.randint(10, 100, 50),
            'comments': np.random.randint(1, 20, 50),
            'shares': np.random.randint(0, 10, 50)
        })
        
        fig = create_correlation_heatmap(
            data=data,
            columns=['views', 'likes', 'comments', 'shares'],
            title="Correlation Matrix"
        )
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert fig.data[0].type == 'heatmap'
        assert fig.layout.title.text == "Correlation Matrix"
    
    def test_create_top_n_chart(self):
        """Test top N chart creation."""
        data = pd.DataFrame({
            'video_title': [f'Video {i}' for i in range(10)],
            'views': np.random.randint(100, 1000, 10)
        })
        
        fig = create_top_n_chart(
            data=data,
            x_col='video_title',
            y_col='views',
            title="Top Videos",
            n=5
        )
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert fig.data[0].type == 'bar'
        assert len(fig.data[0].x) == 5  # Top 5 only
    
    def test_create_gauge_chart(self):
        """Test gauge chart creation."""
        fig = create_gauge_chart(
            value=75,
            title="Engagement Rate",
            min_val=0,
            max_val=100,
            unit="%"
        )
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert fig.data[0].type == 'indicator'
        assert fig.data[0].value == 75
        assert fig.data[0].gauge.axis.range == [0, 100]
    
    def test_create_funnel_chart(self):
        """Test funnel chart creation."""
        data = pd.DataFrame({
            'stage': ['Impressions', 'Clicks', 'Views', 'Likes'],
            'values': [10000, 500, 450, 50]
        })
        
        fig = create_funnel_chart(
            data=data,
            x_col='stage',
            y_col='values',
            title="Engagement Funnel"
        )
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert fig.data[0].type == 'funnel'
        assert fig.layout.title.text == "Engagement Funnel"

class TestPerformanceComponents:
    """Test cases for performance-related UI components."""
    
    @patch('src.ui.components.st')
    def test_create_performance_summary_cards(self, mock_st):
        """Test performance summary cards creation."""
        mock_cols = [Mock() for _ in range(4)]
        mock_st.columns.return_value = mock_cols
        
        metrics = {
            'total_views': 50000,
            'total_impressions': 200000,
            'avg_ctr': 0.05,
            'avg_duration': 125.5
        }
        
        create_performance_summary_cards(metrics)
        
        # Verify columns were created
        mock_st.columns.assert_called_once_with(4)
        
        # Verify each metric card was created
        for col in mock_cols:
            col.metric.assert_called_once()
    
    def test_create_engagement_metrics_chart(self):
        """Test engagement metrics chart creation."""
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10, freq='D'),
            'likes': np.random.randint(10, 100, 10),
            'comments': np.random.randint(1, 20, 10),
            'shares': np.random.randint(0, 10, 10)
        })
        
        fig = create_engagement_metrics_chart(
            data=data,
            date_col='date',
            title="Engagement Over Time"
        )
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 3  # likes, comments, shares
        assert fig.layout.title.text == "Engagement Over Time"

class TestUtilityComponents:
    """Test cases for utility UI components."""
    
    @patch('src.ui.components.st')
    def test_display_video_thumbnail(self, mock_st):
        """Test video thumbnail display."""
        thumbnail_url = "https://example.com/thumbnail.jpg"
        video_title = "Test Video"
        
        display_video_thumbnail(thumbnail_url, video_title)
        
        # Verify image was displayed
        mock_st.image.assert_called_once_with(
            thumbnail_url,
            caption=video_title,
            width=120
        )
    
    @patch('src.ui.components.st')
    def test_display_video_thumbnail_with_custom_width(self, mock_st):
        """Test video thumbnail display with custom width."""
        thumbnail_url = "https://example.com/thumbnail.jpg"
        video_title = "Test Video"
        
        display_video_thumbnail(thumbnail_url, video_title, width=200)
        
        mock_st.image.assert_called_once_with(
            thumbnail_url,
            caption=video_title,
            width=200
        )
    
    @patch('src.ui.components.st')
    def test_create_data_quality_indicator_good(self, mock_st):
        """Test data quality indicator for good quality data."""
        data = pd.DataFrame({
            'views': [100, 200, 300, 400, 500],
            'likes': [10, 20, 30, 40, 50],
            'comments': [1, 2, 3, 4, 5]
        })
        
        create_data_quality_indicator(data)
        
        # Should show success message for complete data
        mock_st.success.assert_called_once()
    
    @patch('src.ui.components.st')
    def test_create_data_quality_indicator_missing_data(self, mock_st):
        """Test data quality indicator with missing data."""
        data = pd.DataFrame({
            'views': [100, None, 300, None, 500],
            'likes': [10, 20, None, 40, 50],
            'comments': [1, 2, 3, 4, 5]
        })
        
        create_data_quality_indicator(data)
        
        # Should show warning for missing data
        mock_st.warning.assert_called_once()
    
    @patch('src.ui.components.st')
    def test_create_data_quality_indicator_empty_data(self, mock_st):
        """Test data quality indicator with empty data."""
        data = pd.DataFrame()
        
        create_data_quality_indicator(data)
        
        # Should show error for empty data
        mock_st.error.assert_called_once()
    
    @patch('src.ui.components.st')
    def test_create_trend_indicator_positive(self, mock_st):
        """Test trend indicator for positive trend."""
        current_value = 1000
        previous_value = 800
        metric_name = "Views"
        
        create_trend_indicator(current_value, previous_value, metric_name)
        
        # Should show positive trend
        mock_st.success.assert_called_once()
    
    @patch('src.ui.components.st')
    def test_create_trend_indicator_negative(self, mock_st):
        """Test trend indicator for negative trend."""
        current_value = 800
        previous_value = 1000
        metric_name = "Views"
        
        create_trend_indicator(current_value, previous_value, metric_name)
        
        # Should show negative trend
        mock_st.error.assert_called_once()
    
    @patch('src.ui.components.st')
    def test_create_trend_indicator_no_change(self, mock_st):
        """Test trend indicator for no change."""
        current_value = 1000
        previous_value = 1000
        metric_name = "Views"
        
        create_trend_indicator(current_value, previous_value, metric_name)
        
        # Should show neutral trend
        mock_st.info.assert_called_once()
    
    @patch('src.ui.components.st')
    def test_create_trend_indicator_no_previous_data(self, mock_st):
        """Test trend indicator with no previous data."""
        current_value = 1000
        previous_value = None
        metric_name = "Views"
        
        create_trend_indicator(current_value, previous_value, metric_name)
        
        # Should show info message for no comparison data
        mock_st.info.assert_called_once()

class TestChartCustomization:
    """Test cases for chart customization options."""
    
    def test_time_series_chart_custom_colors(self):
        """Test time series chart with custom colors."""
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        data = pd.DataFrame({
            'date': dates,
            'views': [100, 150, 200, 180, 220],
            'likes': [10, 15, 20, 18, 22]
        })
        
        custom_colors = ['#FF6B6B', '#4ECDC4']
        
        fig = create_time_series_chart(
            data=data,
            x_col='date',
            y_cols=['views', 'likes'],
            title="Custom Colors Test",
            colors=custom_colors
        )
        
        assert isinstance(fig, go.Figure)
        assert fig.data[0].line.color == custom_colors[0]
        assert fig.data[1].line.color == custom_colors[1]
    
    def test_chart_height_customization(self):
        """Test chart height customization."""
        data = pd.DataFrame({
            'category': ['A', 'B', 'C'],
            'values': [10, 20, 30]
        })
        
        custom_height = 600
        
        fig = create_distribution_chart(
            data=data,
            labels_col='category',
            values_col='values',
            title="Height Test",
            height=custom_height
        )
        
        assert isinstance(fig, go.Figure)
        assert fig.layout.height == custom_height
    
    def test_gauge_chart_color_ranges(self):
        """Test gauge chart with custom color ranges."""
        fig = create_gauge_chart(
            value=75,
            title="Custom Gauge",
            min_val=0,
            max_val=100,
            color_ranges=[
                {'range': [0, 50], 'color': 'red'},
                {'range': [50, 80], 'color': 'yellow'},
                {'range': [80, 100], 'color': 'green'}
            ]
        )
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data[0].gauge.steps) == 3

class TestErrorHandling:
    """Test cases for error handling in UI components."""
    
    def test_empty_dataframe_handling(self):
        """Test handling of empty dataframes."""
        empty_data = pd.DataFrame()
        
        # Should not raise an exception
        fig = create_time_series_chart(
            data=empty_data,
            x_col='date',
            y_cols=['views'],
            title="Empty Data Test"
        )
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0
    
    def test_missing_columns_handling(self):
        """Test handling of missing columns."""
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=5, freq='D'),
            'views': [100, 150, 200, 180, 220]
        })
        
        # Try to create chart with non-existent column
        with pytest.raises(KeyError):
            create_time_series_chart(
                data=data,
                x_col='date',
                y_cols=['non_existent_column'],
                title="Missing Column Test"
            )
    
    def test_invalid_data_types(self):
        """Test handling of invalid data types."""
        data = pd.DataFrame({
            'date': ['not_a_date', 'also_not_a_date'],
            'views': ['not_a_number', 'also_not_a_number']
        })
        
        # Should handle gracefully or raise appropriate error
        try:
            fig = create_time_series_chart(
                data=data,
                x_col='date',
                y_cols=['views'],
                title="Invalid Data Test"
            )
            # If it doesn't raise an error, it should still create a figure
            assert isinstance(fig, go.Figure)
        except (ValueError, TypeError):
            # Expected behavior for invalid data
            pass

class TestComponentIntegration:
    """Integration tests for UI components."""
    
    @patch('src.ui.components.st')
    def test_dashboard_layout_simulation(self, mock_st):
        """Test simulated dashboard layout with multiple components."""
        # Mock streamlit layout functions
        mock_cols = [Mock() for _ in range(4)]
        mock_st.columns.return_value = mock_cols
        
        # Sample data
        metrics = {
            'total_views': 50000,
            'total_impressions': 200000,
            'avg_ctr': 0.05,
            'avg_duration': 125.5
        }
        
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        time_series_data = pd.DataFrame({
            'date': dates,
            'views': np.random.randint(100, 1000, 30),
            'impressions': np.random.randint(1000, 5000, 30)
        })
        
        # Create performance summary
        create_performance_summary_cards(metrics)
        
        # Create time series chart
        fig = create_time_series_chart(
            data=time_series_data,
            x_col='date',
            y_cols=['views', 'impressions'],
            title="Performance Over Time"
        )
        
        # Verify components were created
        assert mock_st.columns.called
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2
    
    def test_multi_chart_creation(self):
        """Test creating multiple charts with consistent styling."""
        # Sample data
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        data = pd.DataFrame({
            'date': dates,
            'views': np.random.randint(100, 1000, 10),
            'likes': np.random.randint(10, 100, 10),
            'comments': np.random.randint(1, 20, 10),
            'ctr': np.random.uniform(0.01, 0.1, 10)
        })
        
        # Create multiple charts
        charts = [
            create_time_series_chart(
                data=data,
                x_col='date',
                y_cols=['views'],
                title="Views Over Time"
            ),
            create_engagement_metrics_chart(
                data=data,
                date_col='date',
                title="Engagement Metrics"
            ),
            create_dual_axis_chart(
                data=data,
                x_col='date',
                y1_col='views',
                y2_col='ctr',
                title="Views vs CTR"
            )
        ]
        
        # Verify all charts were created successfully
        for chart in charts:
            assert isinstance(chart, go.Figure)
            assert chart.layout.title.text is not None

if __name__ == "__main__":
    pytest.main([__file__])