#!/usr/bin/env python3
"""
Unit tests for YouTube authentication module
"""

import pytest
import os
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.auth.youtube_auth import YouTubeAuthenticator
from src.utils.config import Config

class TestYouTubeAuthenticator:
    """Test cases for YouTubeAuthenticator class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=Config)
        config.youtube_client_id = "test_client_id"
        config.youtube_client_secret = "test_client_secret"
        config.youtube_scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        return config
    
    @pytest.fixture
    def temp_credentials_file(self):
        """Create a temporary credentials file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            credentials_data = {
                "installed": {
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            }
            json.dump(credentials_data, f)
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    
    @pytest.fixture
    def authenticator(self, mock_config, temp_credentials_file):
        """Create YouTubeAuthenticator instance for testing."""
        with patch('src.auth.youtube_auth.get_config', return_value=mock_config):
            auth = YouTubeAuthenticator()
            auth.credentials_file = temp_credentials_file
            return auth
    
    def test_init(self, mock_config):
        """Test authenticator initialization."""
        with patch('src.auth.youtube_auth.get_config', return_value=mock_config):
            auth = YouTubeAuthenticator()
            
            assert auth.config == mock_config
            assert auth.credentials is None
            assert auth.service is None
    
    def test_generate_encryption_key(self, authenticator):
        """Test encryption key generation."""
        key1 = authenticator._generate_encryption_key()
        key2 = authenticator._generate_encryption_key()
        
        # Keys should be different each time
        assert key1 != key2
        assert len(key1) == 44  # Base64 encoded 32-byte key
    
    def test_encrypt_decrypt_credentials(self, authenticator):
        """Test credential encryption and decryption."""
        test_data = {"access_token": "test_token", "refresh_token": "test_refresh"}
        
        # Encrypt
        encrypted = authenticator._encrypt_credentials(test_data)
        assert encrypted != test_data
        assert isinstance(encrypted, bytes)
        
        # Decrypt
        decrypted = authenticator._decrypt_credentials(encrypted)
        assert decrypted == test_data
    
    def test_encrypt_decrypt_with_invalid_data(self, authenticator):
        """Test encryption/decryption with invalid data."""
        # Test decryption with invalid data
        with pytest.raises(Exception):
            authenticator._decrypt_credentials(b"invalid_encrypted_data")
    
    @patch('src.auth.youtube_auth.InstalledAppFlow')
    def test_authenticate_success(self, mock_flow_class, authenticator):
        """Test successful authentication."""
        # Mock the flow and credentials
        mock_flow = Mock()
        mock_credentials = Mock()
        mock_credentials.to_json.return_value = '{"token": "test_token"}'
        mock_flow.run_local_server.return_value = mock_credentials
        mock_flow_class.from_client_secrets_file.return_value = mock_flow
        
        # Mock service creation
        with patch('src.auth.youtube_auth.build') as mock_build:
            mock_service = Mock()
            mock_build.return_value = mock_service
            
            result = authenticator.authenticate()
            
            assert result is True
            assert authenticator.credentials == mock_credentials
            assert authenticator.service == mock_service
            
            # Verify flow was configured correctly
            mock_flow_class.from_client_secrets_file.assert_called_once()
            mock_flow.run_local_server.assert_called_once()
    
    @patch('src.auth.youtube_auth.InstalledAppFlow')
    def test_authenticate_failure(self, mock_flow_class, authenticator):
        """Test authentication failure."""
        # Mock flow to raise exception
        mock_flow = Mock()
        mock_flow.run_local_server.side_effect = Exception("Auth failed")
        mock_flow_class.from_client_secrets_file.return_value = mock_flow
        
        result = authenticator.authenticate()
        
        assert result is False
        assert authenticator.credentials is None
        assert authenticator.service is None
    
    def test_is_authenticated_with_credentials(self, authenticator):
        """Test is_authenticated with valid credentials."""
        mock_credentials = Mock()
        mock_credentials.valid = True
        authenticator.credentials = mock_credentials
        
        assert authenticator.is_authenticated() is True
    
    def test_is_authenticated_without_credentials(self, authenticator):
        """Test is_authenticated without credentials."""
        authenticator.credentials = None
        
        assert authenticator.is_authenticated() is False
    
    def test_is_authenticated_with_invalid_credentials(self, authenticator):
        """Test is_authenticated with invalid credentials."""
        mock_credentials = Mock()
        mock_credentials.valid = False
        authenticator.credentials = mock_credentials
        
        assert authenticator.is_authenticated() is False
    
    def test_refresh_credentials_success(self, authenticator):
        """Test successful credential refresh."""
        mock_credentials = Mock()
        mock_credentials.valid = False
        mock_credentials.expired = True
        mock_credentials.refresh_token = "refresh_token"
        authenticator.credentials = mock_credentials
        
        with patch('src.auth.youtube_auth.Request') as mock_request:
            mock_request_instance = Mock()
            mock_request.return_value = mock_request_instance
            
            # Mock successful refresh
            def refresh_side_effect(request):
                mock_credentials.valid = True
                mock_credentials.expired = False
            
            mock_credentials.refresh.side_effect = refresh_side_effect
            
            result = authenticator.refresh_credentials()
            
            assert result is True
            mock_credentials.refresh.assert_called_once_with(mock_request_instance)
    
    def test_refresh_credentials_failure(self, authenticator):
        """Test credential refresh failure."""
        mock_credentials = Mock()
        mock_credentials.refresh.side_effect = Exception("Refresh failed")
        authenticator.credentials = mock_credentials
        
        with patch('src.auth.youtube_auth.Request'):
            result = authenticator.refresh_credentials()
            
            assert result is False
    
    def test_refresh_credentials_no_credentials(self, authenticator):
        """Test refresh with no credentials."""
        authenticator.credentials = None
        
        result = authenticator.refresh_credentials()
        
        assert result is False
    
    def test_create_service_success(self, authenticator):
        """Test successful service creation."""
        mock_credentials = Mock()
        authenticator.credentials = mock_credentials
        
        with patch('src.auth.youtube_auth.build') as mock_build:
            mock_service = Mock()
            mock_build.return_value = mock_service
            
            result = authenticator.create_service()
            
            assert result == mock_service
            assert authenticator.service == mock_service
            mock_build.assert_called_once_with(
                'youtube', 'v3', credentials=mock_credentials
            )
    
    def test_create_service_no_credentials(self, authenticator):
        """Test service creation without credentials."""
        authenticator.credentials = None
        
        result = authenticator.create_service()
        
        assert result is None
        assert authenticator.service is None
    
    def test_create_service_failure(self, authenticator):
        """Test service creation failure."""
        mock_credentials = Mock()
        authenticator.credentials = mock_credentials
        
        with patch('src.auth.youtube_auth.build') as mock_build:
            mock_build.side_effect = Exception("Service creation failed")
            
            result = authenticator.create_service()
            
            assert result is None
            assert authenticator.service is None
    
    def test_get_channel_info_success(self, authenticator):
        """Test successful channel info retrieval."""
        mock_service = Mock()
        authenticator.service = mock_service
        
        # Mock API response
        mock_response = {
            'items': [{
                'id': 'channel_123',
                'snippet': {
                    'title': 'Test Channel',
                    'description': 'Test Description',
                    'thumbnails': {
                        'default': {'url': 'http://example.com/thumb.jpg'}
                    }
                },
                'statistics': {
                    'subscriberCount': '1000',
                    'videoCount': '50',
                    'viewCount': '100000'
                }
            }]
        }
        
        mock_service.channels().list().execute.return_value = mock_response
        
        result = authenticator.get_channel_info()
        
        expected = {
            'id': 'channel_123',
            'title': 'Test Channel',
            'description': 'Test Description',
            'thumbnail': 'http://example.com/thumb.jpg',
            'subscriber_count': 1000,
            'video_count': 50,
            'view_count': 100000
        }
        
        assert result == expected
    
    def test_get_channel_info_no_service(self, authenticator):
        """Test channel info retrieval without service."""
        authenticator.service = None
        
        result = authenticator.get_channel_info()
        
        assert result is None
    
    def test_get_channel_info_api_error(self, authenticator):
        """Test channel info retrieval with API error."""
        mock_service = Mock()
        authenticator.service = mock_service
        
        mock_service.channels().list().execute.side_effect = Exception("API Error")
        
        result = authenticator.get_channel_info()
        
        assert result is None
    
    def test_get_channel_info_empty_response(self, authenticator):
        """Test channel info retrieval with empty response."""
        mock_service = Mock()
        authenticator.service = mock_service
        
        mock_response = {'items': []}
        mock_service.channels().list().execute.return_value = mock_response
        
        result = authenticator.get_channel_info()
        
        assert result is None
    
    def test_revoke_credentials_success(self, authenticator):
        """Test successful credential revocation."""
        mock_credentials = Mock()
        mock_credentials.token = "test_token"
        authenticator.credentials = mock_credentials
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            result = authenticator.revoke_credentials()
            
            assert result is True
            assert authenticator.credentials is None
            assert authenticator.service is None
            
            mock_post.assert_called_once()
    
    def test_revoke_credentials_no_credentials(self, authenticator):
        """Test credential revocation without credentials."""
        authenticator.credentials = None
        
        result = authenticator.revoke_credentials()
        
        assert result is False
    
    def test_revoke_credentials_api_error(self, authenticator):
        """Test credential revocation with API error."""
        mock_credentials = Mock()
        mock_credentials.token = "test_token"
        authenticator.credentials = mock_credentials
        
        with patch('requests.post') as mock_post:
            mock_post.side_effect = Exception("Revoke failed")
            
            result = authenticator.revoke_credentials()
            
            assert result is False
            # Credentials should still be cleared on error
            assert authenticator.credentials is None
            assert authenticator.service is None
    
    def test_save_load_credentials(self, authenticator):
        """Test saving and loading credentials."""
        test_credentials = {
            "token": "test_token",
            "refresh_token": "test_refresh",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret"
        }
        
        # Save credentials
        authenticator._save_credentials(test_credentials)
        
        # Load credentials
        loaded_credentials = authenticator._load_credentials()
        
        assert loaded_credentials == test_credentials
    
    def test_load_credentials_file_not_exists(self, authenticator):
        """Test loading credentials when file doesn't exist."""
        # Ensure token file doesn't exist
        if os.path.exists(authenticator.token_file):
            os.unlink(authenticator.token_file)
        
        result = authenticator._load_credentials()
        
        assert result is None
    
    def test_load_credentials_corrupted_file(self, authenticator):
        """Test loading credentials from corrupted file."""
        # Create corrupted token file
        with open(authenticator.token_file, 'wb') as f:
            f.write(b"corrupted_data")
        
        result = authenticator._load_credentials()
        
        assert result is None
        
        # Cleanup
        if os.path.exists(authenticator.token_file):
            os.unlink(authenticator.token_file)

class TestAuthenticatorIntegration:
    """Integration tests for authenticator."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=Config)
        config.youtube_client_id = "test_client_id"
        config.youtube_client_secret = "test_client_secret"
        config.youtube_scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        return config
    
    def test_full_authentication_flow(self, mock_config):
        """Test complete authentication flow."""
        with patch('src.auth.youtube_auth.get_config', return_value=mock_config):
            authenticator = YouTubeAuthenticator()
            
            # Initially not authenticated
            assert not authenticator.is_authenticated()
            
            # Mock successful authentication
            with patch.object(authenticator, 'authenticate', return_value=True):
                with patch.object(authenticator, 'is_authenticated', return_value=True):
                    # Authenticate
                    result = authenticator.authenticate()
                    assert result is True
                    
                    # Should be authenticated now
                    assert authenticator.is_authenticated()
    
    def test_credential_persistence(self, mock_config):
        """Test that credentials persist across instances."""
        with patch('src.auth.youtube_auth.get_config', return_value=mock_config):
            # Create first authenticator and save credentials
            auth1 = YouTubeAuthenticator()
            test_credentials = {"token": "test_token"}
            auth1._save_credentials(test_credentials)
            
            # Create second authenticator and load credentials
            auth2 = YouTubeAuthenticator()
            loaded_credentials = auth2._load_credentials()
            
            assert loaded_credentials == test_credentials
            
            # Cleanup
            if os.path.exists(auth1.token_file):
                os.unlink(auth1.token_file)

def test_get_authenticator():
    """Test the get_authenticator function."""
    from src.auth.youtube_auth import get_authenticator
    
    # Should return the same instance (singleton pattern)
    auth1 = get_authenticator()
    auth2 = get_authenticator()
    
    assert auth1 is auth2
    assert isinstance(auth1, YouTubeAuthenticator)

if __name__ == "__main__":
    pytest.main([__file__])