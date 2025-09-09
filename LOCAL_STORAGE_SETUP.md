# Local Storage Setup Guide

The YouTube Analytics Dashboard has been configured to use local file storage instead of a database. This makes setup simpler and eliminates the need for database management.

## What Changed

### Storage System
- **Before**: SQLite database with SQLAlchemy ORM
- **After**: JSON files stored locally in the `data/` directory

### Configuration
- Added `USE_LOCAL_STORAGE=true` to `.env` file
- Added `LOCAL_STORAGE_DIR=data` to specify storage location
- Commented out database dependencies in `requirements.txt`

### File Structure
Data is now stored in the following structure:
```
data/
├── videos/          # Video metadata (*.json)
├── metrics/         # Video metrics (*_metrics.json)
├── channels/        # Channel metrics (*_metrics.json)
└── insights/        # AI insights (*.json)
```

## Benefits

1. **Simplified Setup**: No database initialization required
2. **Portable**: Data files can be easily backed up or moved
3. **Transparent**: Data is stored in human-readable JSON format
4. **No Dependencies**: Removed SQLAlchemy and Alembic requirements

## Running the Application

1. Install dependencies (database packages are now optional):
   ```bash
   pip install -r requirements.txt
   ```

2. Configure your `.env` file with API keys (already done)

3. Run the application:
   ```bash
   streamlit run app.py
   ```

4. The `data/` directory will be created automatically when you first use the app

## Data Management

- **Export**: Use the Settings page to export data as CSV files
- **Backup**: Simply copy the entire `data/` directory
- **Clear Data**: Use the "Clear All Data" button in Settings, or delete files in `data/`
- **Migration**: To switch back to database, set `USE_LOCAL_STORAGE=false` in `.env`

## Storage Statistics

The Settings page now shows:
- Storage type (local_files)
- Storage location
- Count of videos, metrics, channels, and insights

## Notes

- Data is stored immediately when fetched from YouTube API
- No database migrations needed
- Thread-safe file operations with locking
- Automatic directory creation
- JSON format with proper datetime serialization