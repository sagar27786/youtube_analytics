#!/usr/bin/env python3
"""
YouTube OAuth2 Authentication Module

Handles secure authentication with YouTube APIs using OAuth2 flow.
"""

import os
import json
import pickle
from typing import Optional, Dict, Any
from pathlib import Path
from cryptography.fernet import Fernet

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..utils.config import get_config

class YouTubeAuthenticator:
    """Handles YouTube OAuth2 authentication and API client creation."""
    
    def __init__(self):
        self.config = get_config()
        self.credentials_file = Path("credentials.encrypted")
        self.token_file = Path("token.encrypted")
        self._encryption_key = self._get_or_create_encryption_key()
        self._credentials: Optional[Credentials] = None
        
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for secure token storage."""
        key_file = Path("encryption.key")
        
        if key_file.exists():
            with open(key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            return key
    
    def _encrypt_data(self, data: Dict[Any, Any]) -> bytes:
        """Encrypt sensitive data."""
        fernet = Fernet(self._encryption_key)
        json_data = json.dumps(data).encode()
        return fernet.encrypt(json_data)
    
    def _decrypt_data(self, encrypted_data: bytes) -> Dict[Any, Any]:
        """Decrypt sensitive data."""
        fernet = Fernet(self._encryption_key)
        decrypted_data = fernet.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode())
    
    def _save_credentials(self, credentials: Credentials) -> None:
        """Save credentials securely to encrypted file."""
        creds_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes
        }
        
        encrypted_data = self._encrypt_data(creds_data)
        with open(self.token_file, "wb") as f:
            f.write(encrypted_data)
    
    def _load_credentials(self) -> Optional[Credentials]:
        """Load credentials from encrypted file."""
        if not self.token_file.exists():
            return None
        
        try:
            with open(self.token_file, "rb") as f:
                encrypted_data = f.read()
            
            creds_data = self._decrypt_data(encrypted_data)
            
            credentials = Credentials(
                token=creds_data["token"],
                refresh_token=creds_data["refresh_token"],
                token_uri=creds_data["token_uri"],
                client_id=creds_data["client_id"],
                client_secret=creds_data["client_secret"],
                scopes=creds_data["scopes"]
            )
            
            return credentials
            
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return None
    
    def _create_oauth_flow(self) -> Flow:
        """Create OAuth2 flow for authentication."""
        client_config = {
            "web": {
                "client_id": self.config.youtube_client_id,
                "client_secret": self.config.youtube_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.config.youtube_redirect_uri]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=self.config.youtube_scopes,
            redirect_uri=self.config.youtube_redirect_uri
        )
        
        return flow
    
    def get_authorization_url(self) -> str:
        """Get the authorization URL for OAuth2 flow."""
        flow = self._create_oauth_flow()
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return auth_url
    
    def handle_oauth_callback(self, authorization_code: str) -> bool:
        """Handle OAuth2 callback and exchange code for credentials."""
        try:
            flow = self._create_oauth_flow()
            flow.fetch_token(code=authorization_code)
            
            self._credentials = flow.credentials
            self._save_credentials(self._credentials)
            
            return True
            
        except Exception as e:
            print(f"Error handling OAuth callback: {e}")
            return False
    
    def refresh_credentials(self) -> bool:
        """Refresh expired credentials."""
        if not self._credentials:
            self._credentials = self._load_credentials()
        
        if not self._credentials:
            return False
        
        try:
            if self._credentials.expired and self._credentials.refresh_token:
                self._credentials.refresh(Request())
                self._save_credentials(self._credentials)
                return True
            return True
            
        except Exception as e:
            print(f"Error refreshing credentials: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        if not self._credentials:
            self._credentials = self._load_credentials()
        
        if not self._credentials:
            return False
        
        if self._credentials.expired:
            return self.refresh_credentials()
        
        return True
    
    def get_credentials(self) -> Optional[Credentials]:
        """Get current credentials."""
        if self.is_authenticated():
            return self._credentials
        return None
    
    def get_youtube_service(self, api_name: str = "youtube", api_version: str = "v3"):
        """Get authenticated YouTube API service."""
        if not self.is_authenticated():
            raise ValueError("Not authenticated. Please authenticate first.")
        
        try:
            service = build(
                api_name,
                api_version,
                credentials=self._credentials,
                cache_discovery=False
            )
            return service
            
        except HttpError as e:
            print(f"Error creating YouTube service: {e}")
            raise
    
    def get_youtube_analytics_service(self):
        """Get authenticated YouTube Analytics API service."""
        return self.get_youtube_service("youtubeAnalytics", "v2")
    
    def revoke_credentials(self) -> bool:
        """Revoke and delete stored credentials."""
        try:
            if self._credentials:
                # Revoke the credentials
                revoke_url = f"https://oauth2.googleapis.com/revoke?token={self._credentials.token}"
                import requests
                response = requests.post(revoke_url)
                
            # Delete stored files
            if self.token_file.exists():
                self.token_file.unlink()
            
            self._credentials = None
            return True
            
        except Exception as e:
            print(f"Error revoking credentials: {e}")
            return False
    
    def get_channel_info(self) -> Optional[Dict[str, Any]]:
        """Get authenticated user's channel information."""
        try:
            youtube = self.get_youtube_service()
            
            # Get channel info
            request = youtube.channels().list(
                part="snippet,statistics,contentDetails",
                mine=True
            )
            response = request.execute()
            
            if response.get("items"):
                return response["items"][0]
            
            return None
            
        except HttpError as e:
            print(f"Error getting channel info: {e}")
            return None

# Global authenticator instance
_authenticator: Optional[YouTubeAuthenticator] = None

def get_authenticator() -> YouTubeAuthenticator:
    """Get the global authenticator instance."""
    global _authenticator
    if _authenticator is None:
        _authenticator = YouTubeAuthenticator()
    return _authenticator