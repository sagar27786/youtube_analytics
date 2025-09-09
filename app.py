#!/usr/bin/env python3
"""
YouTube Analytics Dashboard with Gemini AI Insights

Main Streamlit application entry point.
"""

import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Streamlit page
st.set_page_config(
    page_title="YouTube Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import pages after Streamlit config
from src.ui import overview, videos, video_details, channel_insights, settings
from src.utils.config import Config
from src.database.models import init_database

def main():
    """Main application entry point."""
    
    # Initialize configuration
    config = Config()
    
    # Initialize database
    init_database(config.database_url)
    
    # Sidebar navigation
    st.sidebar.title("📊 YouTube Analytics")
    
    # Page selection
    selected_page = st.sidebar.selectbox(
        "Navigate to:",
        ["📊 Overview", "📹 Videos", "🎬 Video Details", "📈 Channel Insights", "⚙️ Settings"],
        index=0
    )
    
    # Display selected page
    if selected_page == "📊 Overview":
        overview.render_overview_page()
    elif selected_page == "📹 Videos":
        videos.render_videos_page()
    elif selected_page == "🎬 Video Details":
        video_details.render_video_details_page()
    elif selected_page == "📈 Channel Insights":
        channel_insights.render_channel_insights_page()
    elif selected_page == "⚙️ Settings":
        settings.render_settings_page()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "💡 **YouTube Analytics Dashboard**\n\n"
        "Powered by YouTube Data API & Gemini AI"
    )

if __name__ == "__main__":
    main()