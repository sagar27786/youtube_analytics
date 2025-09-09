# 🚀 Quick Start Guide - YouTube Analytics Dashboard

## What You Need (APIs)

### 1. YouTube Data API v3
**What it does:** Gets your YouTube channel data (videos, views, likes, etc.)

**How to get it:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project
3. Enable "YouTube Data API v3"
4. Create OAuth2 credentials (Desktop app)
5. Download the JSON file
6. Copy `client_id` and `client_secret`

### 2. Google Gemini AI API
**What it does:** Creates smart insights about your YouTube performance

**How to get it:**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create API key
3. Copy the key

## Setup (5 Minutes)

### Step 1: Install Python Packages
```bash
pip install -r requirements.txt
```

### Step 2: Add Your API Keys
Edit the `.env` file:
```env
YOUTUBE_CLIENT_ID=your_youtube_client_id
YOUTUBE_CLIENT_SECRET=your_youtube_client_secret
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=sqlite:///youtube_analytics.db
SECRET_KEY=any_random_text_here
```

### Step 3: Setup Database
```bash
python -c "from src.database.models import init_db; init_db()"
```

### Step 4: Run the App
```bash
streamlit run app.py
```

## First Time Use

1. **Open your browser:** Go to `http://localhost:8501`
2. **Connect YouTube:** Go to Settings → Click "Connect YouTube Account"
3. **Get your data:** Click "Refresh Data" to fetch your videos
4. **See insights:** Go to Channel Insights → Click "Generate Insights"

## What Each Page Does

- **Overview:** Your main dashboard with key numbers
- **Videos:** List of all your videos with stats
- **Video Details:** Deep dive into one video
- **Channel Insights:** AI recommendations for your channel
- **Settings:** Connect accounts and manage data

## Troubleshooting

**"Invalid credentials"**
- Check your API keys in `.env` file
- Make sure YouTube API is enabled

**"No data found"**
- Click "Refresh Data" in Settings
- Make sure your YouTube channel is public

**"Quota exceeded"**
- YouTube gives you 10,000 API calls per day
- Wait until tomorrow or upgrade your quota

## API Limits

- **YouTube API:** 10,000 calls/day (free)
- **Gemini AI:** 60 calls/minute (free)

That's it! Your YouTube Analytics Dashboard is ready to use! 🎉

---

**Need help?** Check the full [README.md](README.md) for detailed instructions.