# OAuth 403 Access Denied - Troubleshooting Guide

## Error Details

You're encountering a **403: access_denied** error during YouTube OAuth authentication. This error typically occurs due to OAuth consent screen configuration issues in Google Cloud Console.

**Error Details:**
- **Error Code:** 403
- **Error Type:** access_denied
- **Client ID:** 169154114906-jcqs872v7qgjtb4ces0s1864buo2pemu.apps.googleusercontent.com
- **Redirect URI:** http://localhost:8080/oauth2callback
- **Scopes Requested:**
  - `https://www.googleapis.com/auth/youtube.readonly` <mcreference link="https://www.googleapis.com/auth/youtube.readonly" index="0">0</mcreference>
  - `https://www.googleapis.com/auth/yt-analytics.readonly` <mcreference link="https://www.googleapis.com/auth/yt-analytics.readonly" index="1">1</mcreference>
  - `https://www.googleapis.com/auth/youtube.force-ssl` <mcreference link="https://www.googleapis.com/auth/youtube.force-ssl" index="2">2</mcreference>

---

## Common Causes and Solutions

### 1. OAuth Consent Screen Not Configured Properly

**Problem:** The OAuth consent screen in Google Cloud Console is not set up correctly or is missing required information.

**Solution:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Navigate to **APIs & Services** → **OAuth consent screen**
4. Configure the consent screen:

   **For External Users (Recommended for testing):**
   - **User Type:** External
   - **App name:** FoundryX YouTube Analytics
   - **User support email:** Your email address
   - **Developer contact information:** Your email address
   - **App domain:** Leave blank for testing
   - **Authorized domains:** Leave blank for localhost testing

   **For Internal Users (G Suite/Workspace only):**
   - **User Type:** Internal
   - Fill in required fields as above

### 2. OAuth Client Configuration Issues

**Problem:** The OAuth client is not configured correctly for the application type.

**Solution:**
1. Go to **APIs & Services** → **Credentials**
2. Find your OAuth 2.0 Client ID
3. Click the edit button (pencil icon)
4. Verify the configuration:
   - **Application type:** Desktop application (NOT Web application)
   - **Name:** FoundryX or any descriptive name
   - **Authorized redirect URIs:** Should include `http://localhost:8080/oauth2callback`

### 3. Required APIs Not Enabled

**Problem:** The necessary YouTube APIs are not enabled in your Google Cloud project.

**Solution:**
1. Go to **APIs & Services** → **Library**
2. Search for and enable these APIs:
   - **YouTube Data API v3**
   - **YouTube Analytics API**
   - **YouTube Reporting API** (optional but recommended)

### 4. OAuth Consent Screen in Testing Mode

**Problem:** Your app is in testing mode and your Google account is not added as a test user.

**Solution:**
1. Go to **APIs & Services** → **OAuth consent screen**
2. If your app is in "Testing" status:
   - Click **ADD USERS** in the "Test users" section
   - Add your Google account email address
   - Save the changes

**Alternative:** Publish your app (for personal use):
1. Click **PUBLISH APP** button
2. Confirm the publishing (this makes it available to any Google user)

### 5. Incorrect Redirect URI

**Problem:** The redirect URI in your application doesn't match what's configured in Google Cloud Console.

**Solution:**
1. Verify your `.env` file has the correct redirect URI:
   ```
   YOUTUBE_REDIRECT_URI=http://localhost:8080/oauth2callback
   ```
2. In Google Cloud Console, ensure the OAuth client has this exact URI in the authorized redirect URIs list
3. **Important:** The URI must match exactly (including protocol, port, and path)

### 6. Client Secret Issues

**Problem:** The client secret in your `.env` file doesn't match the one in Google Cloud Console.

**Solution:**
1. Go to **APIs & Services** → **Credentials**
2. Click on your OAuth 2.0 Client ID
3. Copy the **Client Secret**
4. Update your `.env` file:
   ```
   YOUTUBE_CLIENT_SECRET=your_actual_client_secret_here
   ```
5. Restart the application

---

## Step-by-Step Fix Guide

### Step 1: Verify Google Cloud Console Setup

1. **Check Project Selection:**
   - Ensure you're in the correct Google Cloud project
   - The project should have billing enabled (free tier is sufficient)

2. **Enable Required APIs:**
   ```
   ✅ YouTube Data API v3
   ✅ YouTube Analytics API
   ```

3. **Configure OAuth Consent Screen:**
   - User Type: External (for testing)
   - Fill in all required fields
   - Add your email as a test user if in testing mode

4. **Create/Update OAuth Client:**
   - Application type: **Desktop application**
   - Authorized redirect URIs: `http://localhost:8080/oauth2callback`

### Step 2: Update Application Configuration

1. **Update `.env` file with correct credentials:**
   ```env
   YOUTUBE_CLIENT_ID=your_client_id_from_google_console
   YOUTUBE_CLIENT_SECRET=your_client_secret_from_google_console
   YOUTUBE_REDIRECT_URI=http://localhost:8080/oauth2callback
   ```

2. **Restart the application:**
   ```bash
   # Stop the current application (Ctrl+C)
   # Then restart
   streamlit run app.py
   ```

### Step 3: Test Authentication

1. **Clear any existing authentication:**
   - Delete `credentials.encrypted` and `token.encrypted` files if they exist
   - This forces a fresh authentication attempt

2. **Attempt authentication:**
   - Go to Settings → YouTube Authentication
   - Click "Connect to YouTube"
   - Follow the OAuth flow

---

## Advanced Troubleshooting

### Check OAuth Scopes

The application requests these specific scopes:
- `youtube.readonly`: Read access to YouTube data
- `yt-analytics.readonly`: Read access to YouTube Analytics
- `youtube.force-ssl`: Secure access to YouTube APIs

If you're still getting errors, try reducing the scopes temporarily:

1. **Edit `src/utils/config.py`:**
   ```python
   @property
   def youtube_scopes(self) -> list[str]:
       """YouTube API scopes required for the application."""
       return [
           "https://www.googleapis.com/auth/youtube.readonly"
           # Comment out other scopes temporarily
           # "https://www.googleapis.com/auth/yt-analytics.readonly",
           # "https://www.googleapis.com/auth/youtube.force-ssl"
       ]
   ```

2. **Test with minimal scope first**
3. **Gradually add back other scopes**

### Verify Account Permissions

1. **Check if your Google account has YouTube access:**
   - Visit [YouTube.com](https://youtube.com) and ensure you can log in
   - You don't need a YouTube channel, just a Google account

2. **Try with a different Google account:**
   - Sometimes account-specific restrictions can cause issues
   - Test with a fresh Google account

### Network and Firewall Issues

1. **Check if localhost:8080 is accessible:**
   ```bash
   # Test if the port is available
   netstat -an | findstr :8080
   ```

2. **Firewall settings:**
   - Ensure Windows Firewall allows the application
   - Check if any antivirus software is blocking the OAuth callback

---

## Quick Fix Checklist

**Before contacting support, verify:**

- [ ] Google Cloud project has YouTube Data API v3 enabled
- [ ] OAuth consent screen is configured with your email as test user
- [ ] OAuth client is set as "Desktop application" type
- [ ] Redirect URI exactly matches: `http://localhost:8080/oauth2callback`
- [ ] Client ID and secret in `.env` match Google Cloud Console
- [ ] Application has been restarted after configuration changes
- [ ] No existing authentication files are interfering
- [ ] Your Google account can access YouTube.com

---

## Still Having Issues?

### Create a New OAuth Client

If the above steps don't work, create a completely new OAuth client:

1. **In Google Cloud Console:**
   - Go to APIs & Services → Credentials
   - Click "+ CREATE CREDENTIALS" → "OAuth 2.0 Client ID"
   - Choose "Desktop application"
   - Name it "FoundryX-New"
   - Add redirect URI: `http://localhost:8080/oauth2callback`

2. **Update your `.env` file with the new credentials**

3. **Delete old authentication files:**
   ```bash
   rm credentials.encrypted token.encrypted
   ```

4. **Restart and test**

### Alternative: Use Different Port

If port 8080 is causing issues:

1. **Update `.env` file:**
   ```env
   YOUTUBE_REDIRECT_URI=http://localhost:8090/oauth2callback
   ```

2. **Update Google Cloud Console:**
   - Add the new redirect URI to your OAuth client
   - Remove the old one if desired

3. **Restart the application**

---

## Contact Information

If you've tried all the above solutions and are still experiencing issues:

1. **Check the application logs** for more detailed error messages
2. **Verify your Google Cloud Console setup** matches the requirements exactly
3. **Try the authentication flow with a different Google account**
4. **Consider creating a new Google Cloud project** if the current one has configuration issues

**Remember:** OAuth setup can be tricky, but following these steps systematically should resolve the 403 access_denied error.