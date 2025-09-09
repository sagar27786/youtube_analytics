#!/usr/bin/env python3
"""
Settings Page - Authentication, configuration, and database management
"""

import streamlit as st
import os
from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional
import json
import pandas as pd

from ..auth.youtube_auth import get_authenticator
from ..utils.config import get_config
from ..storage import get_storage_adapter
from ..ingestion.youtube_data import get_ingester
from ..database.models import DatabaseManager

def render_youtube_auth_section():
    """Render YouTube authentication section."""
    st.subheader("🔐 YouTube Authentication")
    
    authenticator = get_authenticator()
    
    # Check for OAuth callback parameters in URL
    query_params = st.query_params
    if "code" in query_params and not st.session_state.get('oauth_processed', False):
        auth_code = query_params["code"]
        st.info("🔄 Processing OAuth callback...")
        
        with st.spinner("Completing authentication..."):
            success = authenticator.handle_oauth_callback(auth_code)
            if success:
                st.success("✅ Successfully connected to YouTube!")
                st.session_state['oauth_processed'] = True
                # Clear the URL parameters by rerunning
                st.query_params.clear()
                st.rerun()
            else:
                st.error("❌ Failed to complete authentication. Please try again.")
    
    # Check authentication status
    is_authenticated = authenticator.is_authenticated()
    
    if is_authenticated:
        st.success("✅ Connected to YouTube")
        
        # Get channel info
        try:
            channel_info = authenticator.get_channel_info()
            if channel_info:
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if channel_info.get('thumbnail'):
                        st.image(channel_info['thumbnail'], width=100)
                
                with col2:
                    st.write(f"**Channel:** {channel_info.get('title', 'Unknown')}")
                    st.write(f"**Channel ID:** `{channel_info.get('id', 'Unknown')}`")
                    st.write(f"**Subscribers:** {channel_info.get('subscriber_count', 'Unknown')}")
                    st.write(f"**Videos:** {channel_info.get('video_count', 'Unknown')}")
        except Exception as e:
            st.warning(f"Could not fetch channel info: {e}")
        
        # Disconnect button
        if st.button("🔌 Disconnect from YouTube", type="secondary"):
            try:
                authenticator.revoke_credentials()
                st.success("✅ Disconnected from YouTube")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error disconnecting: {e}")
    
    else:
        st.warning("❌ Not connected to YouTube")
        st.info("To connect to YouTube, you need to set up OAuth2 credentials first.")
        
        # Instructions for setup
        with st.expander("📋 Setup Instructions"):
            st.markdown("""
            **Step 1: Create Google Cloud Project**
            1. Go to [Google Cloud Console](https://console.cloud.google.com/)
            2. Create a new project or select an existing one
            3. Enable the YouTube Data API v3 and YouTube Analytics API
            
            **Step 2: Create OAuth2 Credentials**
            1. Go to "Credentials" in the Google Cloud Console
            2. Click "Create Credentials" → "OAuth 2.0 Client IDs"
            3. Choose "Desktop application" as the application type
            4. Download the JSON file
            
            **Step 3: Configure Environment**
            1. Copy the client ID and client secret from the JSON file
            2. Set them in your `.env` file:
               ```
               YOUTUBE_CLIENT_ID=your_client_id_here
               YOUTUBE_CLIENT_SECRET=your_client_secret_here
               ```
            3. Restart the application
            """)
        
        # Connect button
        config = get_config()
        if config.youtube_client_id and config.youtube_client_secret:
            if st.button("🔗 Connect to YouTube", type="primary"):
                try:
                    # Get authorization URL and redirect user
                    auth_url = authenticator.get_authorization_url()
                    st.info("🔗 Please click the link below to authorize the application:")
                    st.markdown(f"[**Authorize YouTube Access**]({auth_url})")
                    
                    # Input field for authorization code
                    st.markdown("---")
                    st.info("📋 After authorization, copy the authorization code and paste it below:")
                    auth_code = st.text_input("Authorization Code:", placeholder="Paste the authorization code here...")
                    
                    if auth_code and st.button("Complete Authentication"):
                        with st.spinner("Completing authentication..."):
                            success = authenticator.handle_oauth_callback(auth_code)
                            if success:
                                st.success("✅ Successfully connected to YouTube!")
                                st.rerun()
                            else:
                                st.error("❌ Failed to complete authentication. Please check the authorization code.")
                                
                except Exception as e:
                    st.error(f"❌ Authentication error: {e}")
        else:
            st.error("❌ YouTube credentials not configured. Please check your `.env` file.")

def render_gemini_config_section():
    """Render Gemini AI configuration section."""
    st.subheader("🤖 Gemini AI Configuration")
    
    config = get_config()
    
    if config.gemini_api_key:
        st.success("✅ Gemini API key configured")
        
        # Test API connection
        if st.button("🧪 Test Gemini Connection"):
            try:
                from ..ai.gemini_client import GeminiClient
                
                with st.spinner("Testing Gemini connection..."):
                    client = GeminiClient()
                    
                    # Simple test prompt
                    test_response = client._generate_content("Hello, respond with 'Connection successful!'")
                    
                    if "successful" in test_response.lower():
                        st.success("✅ Gemini connection successful!")
                    else:
                        st.warning(f"⚠️ Unexpected response: {test_response}")
                        
            except Exception as e:
                st.error(f"❌ Gemini connection failed: {e}")
        
        # API usage info
        st.info("💡 **Tip:** Monitor your Gemini API usage in the [Google AI Studio](https://aistudio.google.com/)")
        
    else:
        st.warning("❌ Gemini API key not configured")
        
        with st.expander("📋 Setup Instructions"):
            st.markdown("""
            **Step 1: Get Gemini API Key**
            1. Go to [Google AI Studio](https://aistudio.google.com/)
            2. Sign in with your Google account
            3. Click "Get API key" and create a new key
            
            **Step 2: Configure Environment**
            1. Copy your API key
            2. Add it to your `.env` file:
               ```
               GEMINI_API_KEY=your_api_key_here
               ```
            3. Restart the application
            """)

def render_database_section():
    """Render database configuration and management section."""
    st.subheader("🗄️ Database Management")
    
    config = get_config()
    
    # Database info
    st.write(f"**Database URL:** `{config.database_url}`")
    
    # Database operations
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔧 Initialize Database"):
            try:
                with st.spinner("Initializing database..."):
                    from ..database.models import init_database
                    config = get_config()
                    db_manager = init_database(config.database_url)
                    st.success("✅ Database initialized successfully!")
            except Exception as e:
                st.error(f"❌ Database initialization failed: {e}")
    
    with col2:
        if st.button("📊 Load Sample Data"):
            try:
                with st.spinner("Loading sample data..."):
                    from ..database.migrate import load_sample_data
                    load_sample_data()
                    st.success("✅ Sample data loaded successfully!")
            except Exception as e:
                st.error(f"❌ Failed to load sample data: {e}")
    
    with col3:
        if st.button("⚠️ Reset Database", type="secondary"):
            if st.session_state.get('confirm_reset', False):
                try:
                    with st.spinner("Resetting database..."):
                        from ..database.migrate import reset_database
                        reset_database()
                        st.success("✅ Database reset successfully!")
                        st.session_state['confirm_reset'] = False
                except Exception as e:
                    st.error(f"❌ Database reset failed: {e}")
            else:
                st.session_state['confirm_reset'] = True
                st.warning("⚠️ Click again to confirm database reset (this will delete all data!)")
    
    # Database statistics
    try:
        storage = get_storage_adapter()
        
        # Get storage statistics
        stats = storage.get_storage_stats()
        video_count = stats.get('videos', 0)
        metrics_count = stats.get('metrics', 0)
        insights_count = stats.get('insights', 0)
        
        st.write("**Database Statistics:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Videos", video_count)
        
        with col2:
            st.metric("Metrics Records", metrics_count)
        
        with col3:
            st.metric("Insights", insights_count)
            
    except Exception as e:
        st.warning(f"Could not fetch database statistics: {e}")

def render_data_ingestion_section():
    """Render data ingestion configuration section."""
    st.subheader("📥 Data Ingestion Settings")
    
    authenticator = get_authenticator()
    
    if not authenticator.is_authenticated():
        st.warning("❌ Please connect to YouTube first to configure data ingestion.")
        return
    
    # Manual data refresh
    st.write("**Manual Data Refresh**")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=date.today() - timedelta(days=30),
            max_value=date.today(),
            key="settings_start_date"
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=date.today(),
            max_value=date.today(),
            key="settings_end_date"
        )
    
    with col3:
        st.write("")
        st.write("")
        if st.button("🔄 Refresh Data", type="primary"):
            if start_date > end_date:
                st.error("Start date must be before end date.")
            else:
                try:
                    with st.spinner("Refreshing data from YouTube..."):
                        ingester = get_ingester()
                        result = ingester.ingest_data(
                            start_date=start_date,
                            end_date=end_date
                        )
                        
                        if result.success:
                            st.success(f"✅ Data refreshed successfully!")
                            st.info(f"📊 Processed {result.videos_processed} videos and saved {result.metrics_saved} metrics")
                            
                            if result.errors:
                                st.warning(f"⚠️ Some errors occurred: {'; '.join(result.errors)}")
                        else:
                            st.error(f"❌ Data refresh failed: {'; '.join(result.errors)}")
                            
                except Exception as e:
                    st.error(f"❌ Error during data refresh: {e}")
    
    # Quota information
    st.write("**API Quota Information**")
    
    try:
        # For local storage, show simplified quota information
        config = get_config()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Data API Quota Limit", f"{config.youtube_api_quota_limit:,}")
        
        with col2:
            st.metric("Gemini API Rate Limit", f"{config.gemini_api_rate_limit:,}/min")
            
        with col3:
            st.metric("Estimated Remaining", "10,000")  # Simplified for local storage
        
        session.close()
        
    except Exception as e:
        st.warning(f"Could not fetch quota information: {e}")

def render_app_settings_section():
    """Render application settings section."""
    st.subheader("⚙️ Application Settings")
    
    config = get_config()
    
    # Environment info
    st.write("**Environment Information**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"🏠 **Environment:** {'Production' if config.is_production else 'Development'}")
        st.info(f"🔧 **Debug Mode:** {'Enabled' if config.debug else 'Disabled'}")
    
    with col2:
        st.info(f"⏱️ **Cache TTL:** {config.cache_ttl_seconds} seconds")
        st.info(f"🚦 **Rate Limit:** {config.gemini_api_rate_limit} requests/minute")
    
    # Cache management
    st.write("**Cache Management**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Clear All Caches"):
            st.cache_data.clear()
            st.success("✅ All caches cleared!")
    
    with col2:
        if st.button("🔄 Restart Session"):
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("✅ Session restarted!")
            st.rerun()
    
    # Configuration display
    with st.expander("🔍 View Configuration"):
        config_dict = {
            "Database URL": config.database_url,
            "YouTube Client ID": config.youtube_client_id[:10] + "..." if config.youtube_client_id else "Not set",
            "Gemini API Key": "Set" if config.gemini_api_key else "Not set",
            "Debug": config.debug,
            "Cache TTL": config.cache_ttl_seconds,
            "Rate Limit": f"{config.gemini_api_rate_limit} requests/minute",
            "Schedule Enabled": config.auto_refresh_enabled,
            "Schedule Interval": config.auto_refresh_interval_hours
        }
        
        st.json(config_dict)

def render_export_import_section():
    """Render data export/import section."""
    st.subheader("📤 Data Export & Import")
    
    # Export data
    st.write("**Export Data**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export Videos"):
            try:
                storage = get_storage_adapter()
                
                videos_data = storage.get_all_videos()
                videos_df = pd.DataFrame(videos_data)
                
                if not videos_df.empty:
                    csv = videos_df.to_csv(index=False)
                    st.download_button(
                        label="Download Videos CSV",
                        data=csv,
                        file_name=f"videos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No video data available to export.")
                
            except Exception as e:
                st.error(f"❌ Export failed: {e}")
    
    with col2:
        if st.button("📈 Export Metrics"):
            try:
                storage = get_storage_adapter()
                
                # Get all video metrics
                all_videos = storage.get_all_videos()
                metrics_data = []
                for video in all_videos:
                    metrics = storage.get_video_metrics(video['video_id'])
                    if metrics:
                        metrics_data.append(metrics)
                
                if metrics_data:
                    metrics_df = pd.DataFrame(metrics_data)
                    csv = metrics_df.to_csv(index=False)
                    st.download_button(
                        label="Download Metrics CSV",
                        data=csv,
                        file_name=f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No metrics data available to export.")
                
            except Exception as e:
                st.error(f"❌ Export failed: {e}")
    
    with col3:
        if st.button("🤖 Export Insights"):
            try:
                storage = get_storage_adapter()
                
                insights_data = storage.get_all_insights()
                
                if insights_data:
                    insights_df = pd.DataFrame(insights_data)
                    csv = insights_df.to_csv(index=False)
                    st.download_button(
                        label="Download Insights CSV",
                        data=csv,
                        file_name=f"insights_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No insights data available to export.")
                
            except Exception as e:
                st.error(f"❌ Export failed: {e}")

def render_settings_page():
    """Render the settings page."""
    st.title("⚙️ Settings & Configuration")
    
    # Create tabs for different settings sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔐 Authentication",
        "🗄️ Database", 
        "📥 Data Ingestion",
        "⚙️ App Settings",
        "📤 Export/Import"
    ])
    
    with tab1:
        render_youtube_auth_section()
        st.divider()
        render_gemini_config_section()
    
    with tab2:
        render_database_section()
    
    with tab3:
        render_data_ingestion_section()
    
    with tab4:
        render_app_settings_section()
    
    with tab5:
        render_export_import_section()

if __name__ == "__main__":
    render_settings_page()