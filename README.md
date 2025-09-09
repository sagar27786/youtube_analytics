# YouTube Analytics Dashboard

A comprehensive YouTube analytics dashboard built with Streamlit, featuring AI-powered insights using Google's Gemini AI.

## Features

### 📊 Analytics Dashboard
- **Overview Page**: Key performance indicators and channel summary
- **Videos Table**: Searchable, sortable table with video metrics
- **Video Details**: In-depth analysis of individual videos
- **Channel Insights**: Performance trends and AI-generated insights
- **Settings**: Configuration and data management

### 🤖 AI-Powered Insights
- Automated insight generation using Google Gemini AI
- Performance analysis and recommendations
- Trend identification and content optimization suggestions
- Priority-based insight categorization

### 🔐 Secure Authentication
- YouTube OAuth2 integration
- Encrypted credential storage
- Automatic token refresh

### 📈 Data Visualization
- Interactive Plotly charts
- Time series analysis
- Performance metrics visualization
- Engagement trend analysis

### ⚡ Performance Optimization
- Intelligent caching system
- Rate limiting for API calls
- Background task scheduling
- Efficient data processing

## Prerequisites

- Python 3.9 or higher
- YouTube Data API v3 credentials
- Google Gemini AI API key

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd foundryx
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` file with your credentials:
   ```env
   YOUTUBE_CLIENT_ID=your_youtube_client_id
   YOUTUBE_CLIENT_SECRET=your_youtube_client_secret
   GEMINI_API_KEY=your_gemini_api_key
   DATABASE_URL=sqlite:///youtube_analytics.db
   SECRET_KEY=your_secret_key_for_encryption
   ```

4. **Initialize the database**
   ```bash
   python -c "from src.database.models import init_db; init_db()"
   ```

## Getting Started

### 1. Obtain YouTube API Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the YouTube Data API v3
4. Create OAuth2 credentials (Desktop application)
5. Download the credentials and add them to your `.env` file

### 2. Get Gemini AI API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add it to your `.env` file

### 3. Run the Application

```bash
streamlit run app.py
```

The application will be available at `http://localhost:8501`

## Usage

### Initial Setup

1. **Authentication**: Go to Settings → YouTube Authentication and connect your YouTube account
2. **Data Ingestion**: Use the "Refresh Data" button to fetch your channel's analytics
3. **AI Insights**: Generate insights from the Channel Insights page

### Navigation

- **Overview**: Dashboard with key metrics and recent performance
- **Videos**: Browse and analyze individual video performance
- **Video Details**: Deep dive into specific video analytics
- **Channel Insights**: AI-powered analysis and recommendations
- **Settings**: Manage authentication, database, and application settings

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd foundryx
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your API credentials:

   **YouTube API Setup:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable YouTube Data API v3 and YouTube Analytics API
   - Create OAuth2 credentials (Web application)
   - Add `http://localhost:8080/oauth2callback` to authorized redirect URIs

   **Gemini AI Setup:**
   - Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

### 5. Initialize Database

```bash
python -m src.database.migrate
```

## 🚀 Usage

### Running the Application

```bash
streamlit run app.py
```

The application will be available at `http://localhost:8501`

### First Time Setup

1. Navigate to **Settings** page
2. Click "Connect YouTube Account"
3. Complete OAuth2 authentication
4. Configure Gemini AI settings
5. Set up data refresh preferences

### Using the Dashboard

- **Overview**: View key metrics and KPI cards
- **Videos**: Browse all videos with sortable metrics
- **Video Details**: Deep dive into individual video performance
- **Channel Insights**: AI-generated recommendations and actions
- **Settings**: Manage connections and preferences

## 🏗️ Architecture

```
src/
├── auth/           # YouTube OAuth2 authentication
├── database/       # SQLAlchemy models and migrations
├── ingestion/      # YouTube API data fetching
├── ai/            # Gemini AI integration and prompts
├── ui/            # Streamlit pages and components
└── utils/         # Configuration and utilities

tests/             # Unit and integration tests
migrations/        # Database migration scripts
.github/workflows/ # CI/CD configuration
```

## 📊 Data Model

### Core Tables

- **videos**: Video metadata (title, description, published date, etc.)
- **metrics**: Time-series metrics per video (views, impressions, CTR, etc.)
- **insights**: AI-generated insights and recommendations

### Key Metrics Tracked

- Impressions & Click-through Rate (CTR)
- Views & Unique Viewers
- Watch Time & Average View Duration
- Engagement (likes, comments, shares)
- Subscriber Changes
- Traffic Sources

## 🤖 AI Insights

The application uses structured prompts to generate actionable insights:

### Channel-Level Insights
- Video reindexing recommendations
- Upload schedule optimization
- Topic suggestions
- Promotion prioritization

### Video-Level Insights
- Title/description optimization
- Tag suggestions
- Retention analysis
- Performance flags

## 🧪 Testing

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=src --cov-report=html
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/
```

## 🔧 Development

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

## 🐳 Docker Support

```bash
# Build image
docker build -t youtube-analytics .

# Run container
docker run -p 8501:8501 --env-file .env youtube-analytics
```

## 📈 Performance Considerations

- **Rate Limiting**: Automatic quota management for YouTube APIs
- **Caching**: Intelligent caching of API responses
- **Batch Processing**: Efficient bulk data operations
- **Database Indexing**: Optimized queries for large datasets

## 🔒 Security

- OAuth2 secure token handling
- Encrypted local token storage
- No hardcoded secrets
- Environment-based configuration
- Input validation and sanitization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:

1. Check the [Issues](https://github.com/your-repo/issues) page
2. Review the troubleshooting section below
3. Create a new issue with detailed information

## 🔧 Troubleshooting

### Common Issues

**Authentication Errors:**
- Verify OAuth2 credentials in Google Cloud Console
- Check redirect URI configuration
- Ensure APIs are enabled

**API Quota Exceeded:**
- Monitor usage in Google Cloud Console
- Adjust refresh frequency
- Implement additional caching

**Database Issues:**
- Check database URL in .env
- Run migrations: `alembic upgrade head`
- Verify file permissions for SQLite

**Gemini AI Errors:**
- Verify API key is valid
- Check rate limiting settings
- Review prompt templates

## 📚 API Documentation

- [YouTube Data API v3](https://developers.google.com/youtube/v3)
- [YouTube Analytics API](https://developers.google.com/youtube/analytics)
- [Google Gemini AI](https://ai.google.dev/docs)

---

**Built with ❤️ using Streamlit, YouTube APIs, and Gemini AI**