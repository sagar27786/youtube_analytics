#!/usr/bin/env python3
"""
Configuration management for YouTube Analytics Dashboard.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config(BaseSettings):
    """Application configuration settings."""
    
    # YouTube API Configuration
    youtube_client_id: str = Field(default="your_youtube_client_id_here", env="YOUTUBE_CLIENT_ID")
    youtube_client_secret: str = Field(default="your_youtube_client_secret_here", env="YOUTUBE_CLIENT_SECRET")
    youtube_redirect_uri: str = Field(
        default="http://localhost:8080/oauth2callback",
        env="YOUTUBE_REDIRECT_URI"
    )
    
    # Gemini AI Configuration
    gemini_api_key: str = Field(default="your_gemini_api_key_here", env="GEMINI_API_KEY")
    
    # Database Configuration
    database_url: str = Field(
        default="sqlite:///./youtube_analytics.db",
        env="DATABASE_URL"
    )
    use_local_storage: bool = Field(default=False, env="USE_LOCAL_STORAGE")
    local_storage_dir: str = Field(default="data", env="LOCAL_STORAGE_DIR")
    
    # Application Configuration
    app_secret_key: str = Field(default="your_app_secret_key_here", env="APP_SECRET_KEY")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Rate Limiting Configuration
    youtube_api_quota_limit: int = Field(default=10000, env="YOUTUBE_API_QUOTA_LIMIT")
    gemini_api_rate_limit: int = Field(default=60, env="GEMINI_API_RATE_LIMIT")
    
    # Scheduling Configuration
    auto_refresh_enabled: bool = Field(default=False, env="AUTO_REFRESH_ENABLED")
    auto_refresh_interval_hours: int = Field(default=24, env="AUTO_REFRESH_INTERVAL_HOURS")
    
    # Cache Configuration
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    cache_max_size: int = Field(default=1000, env="CACHE_MAX_SIZE")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "allow"
    }
    
    @property
    def youtube_scopes(self) -> list[str]:
        """YouTube API scopes required for the application."""
        return [
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/yt-analytics.readonly",
            "https://www.googleapis.com/auth/youtube.force-ssl"
        ]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.debug
    
    def validate_required_settings(self) -> bool:
        """Validate that all required settings are configured."""
        required_fields = [
            "youtube_client_id",
            "youtube_client_secret",
            "gemini_api_key",
            "app_secret_key"
        ]
        
        missing_fields = []
        for field in required_fields:
            value = getattr(self, field, None)
            if not value or value == f"your_{field}_here":
                missing_fields.append(field.upper())
        
        if missing_fields:
            # In cloud environments, just warn instead of raising error
            import os
            if os.getenv('STREAMLIT_SHARING') or os.getenv('STREAMLIT_CLOUD'):
                print(f"Warning: Missing configuration: {', '.join(missing_fields)}. Some features may not work.")
                return False
            else:
                raise ValueError(
                    f"Missing required configuration: {', '.join(missing_fields)}. "
                    "Please check your .env file."
                )
        
        return True

# Global configuration instance
config = Config()

def get_config() -> Config:
    """Get the global configuration instance."""
    return config