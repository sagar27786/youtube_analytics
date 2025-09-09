# Streamlit Cloud Deployment Guide

This guide will help you deploy FoundryX to Streamlit Cloud and fix the configuration errors.

## The Problem

The error you're seeing occurs because Streamlit Cloud doesn't have access to your local `.env` file with API keys and configuration. The app tries to load required environment variables but fails.

## Solution: Configure Secrets in Streamlit Cloud

### Step 1: Access Your App Settings

1. Go to [Streamlit Cloud](https://share.streamlit.io/)
2. Find your deployed app
3. Click the **"⚙️ Settings"** button
4. Navigate to the **"Secrets"** tab

### Step 2: Add Your Secrets

Copy and paste the following into the Secrets section, replacing the placeholder values with your actual API keys:

```toml
# YouTube API Configuration
YOUTUBE_CLIENT_ID = "your_actual_youtube_client_id"
YOUTUBE_CLIENT_SECRET = "your_actual_youtube_client_secret"
YOUTUBE_REDIRECT_URI = "https://your-app-name.streamlit.app/oauth2callback"
YOUTUBE_API_KEY = "your_actual_youtube_api_key"

# Gemini AI Configuration
GEMINI_API_KEY = "your_actual_gemini_api_key"

# Application Configuration
APP_SECRET_KEY = "your_generated_secret_key_here"

# Optional: Database Configuration
DATABASE_URL = "sqlite:///./youtube_analytics.db"
USE_LOCAL_STORAGE = false
LOCAL_STORAGE_DIR = "data"

# Application Settings
DEBUG = false
LOG_LEVEL = "INFO"

# API Limits
YOUTUBE_API_QUOTA_LIMIT = 10000
GEMINI_API_RATE_LIMIT = 60

# Auto Refresh Settings
AUTO_REFRESH_ENABLED = false
AUTO_REFRESH_INTERVAL_HOURS = 24

# Cache Settings
CACHE_TTL_SECONDS = 3600
CACHE_MAX_SIZE = 1000
```

### Step 3: Get Your API Keys

#### YouTube API Keys:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable YouTube Data API v3
4. Create credentials (OAuth 2.0 Client ID and API Key)
5. Set redirect URI to: `https://your-app-name.streamlit.app/oauth2callback`

#### Gemini API Key:
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key

#### App Secret Key:
Generate a random secret key:
```python
import secrets
print(secrets.token_urlsafe(32))
```

### Step 4: Update Redirect URI

**Important**: Update your YouTube OAuth redirect URI to match your Streamlit Cloud URL:
- Replace `your-app-name` with your actual Streamlit app name
- Format: `https://your-app-name.streamlit.app/oauth2callback`

### Step 5: Save and Restart

1. Click **"Save"** in the Secrets tab
2. Your app will automatically restart
3. The configuration errors should be resolved

## Alternative: Quick Fix for Testing

If you want to deploy quickly for testing without full API setup:

1. The app will now start with default placeholder values
2. You'll see warnings instead of errors
3. Some features won't work until you add real API keys
4. You can add API keys later through the Secrets tab

## Troubleshooting

### Error: "Missing required configuration"
- **Solution**: Add the missing keys to Streamlit Cloud Secrets
- **Check**: Ensure no typos in secret names
- **Verify**: Secret values don't have extra quotes or spaces

### Error: "OAuth redirect URI mismatch"
- **Solution**: Update redirect URI in Google Cloud Console
- **Format**: `https://your-app-name.streamlit.app/oauth2callback`
- **Check**: Ensure exact match (no trailing slashes)

### Error: "Invalid API key"
- **Solution**: Regenerate API keys in respective consoles
- **Check**: Ensure APIs are enabled (YouTube Data API v3, Gemini API)
- **Verify**: No extra characters in copied keys

### App Still Not Working?
1. Check Streamlit Cloud logs for specific errors
2. Verify all secret names match exactly (case-sensitive)
3. Ensure API quotas aren't exceeded
4. Try restarting the app from Streamlit Cloud dashboard

## Security Notes

✅ **Safe**: Streamlit Cloud Secrets are encrypted and secure
✅ **Private**: Secrets are not visible in your public repository
✅ **Isolated**: Each app has its own secret storage

❌ **Never**: Commit API keys to your GitHub repository
❌ **Avoid**: Sharing secret values in public channels

## Next Steps After Deployment

1. **Test OAuth Flow**: Try authenticating with YouTube
2. **Verify API Access**: Check if data fetching works
3. **Monitor Usage**: Keep track of API quota consumption
4. **Set Up Monitoring**: Use Streamlit Cloud analytics
5. **Update Documentation**: Add your live app URL to README

## Live App URL

Once deployed, your app will be available at:
`https://your-app-name.streamlit.app`

---

**Need Help?**
- Check [Streamlit Cloud Documentation](https://docs.streamlit.io/streamlit-cloud)
- Review [Google Cloud Console](https://console.cloud.google.com/) for API setup
- Consult [YouTube API Documentation](https://developers.google.com/youtube/v3)