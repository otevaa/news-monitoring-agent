import os
from flask import session, redirect, request, url_for
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from .secure_credentials import GoogleCredentialsManager

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile", 
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]

# Only allow insecure transport for localhost development
if os.getenv("GOOGLE_REDIRECT_URI", "").startswith("http://127.0.0.1") or os.getenv("GOOGLE_REDIRECT_URI", "").startswith("http://localhost"):
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # Allow HTTP for localhost only
else:
    # For production (HTTPS), remove insecure transport setting
    os.environ.pop("OAUTHLIB_INSECURE_TRANSPORT", None)

# Initialize secure credentials manager
credentials_manager = GoogleCredentialsManager()

def get_auth_flow():
    """Get OAuth flow with environment variables"""
    try:
        # Get redirect URI from environment
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
        
        # Get client configuration from environment variables
        client_config = {
            "web": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        }
        
        # Validate environment variables
        if not client_config["web"]["client_id"] or not client_config["web"]["client_secret"]:
            raise ValueError("Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET in environment")
        
        if not redirect_uri:
            raise ValueError("Missing GOOGLE_REDIRECT_URI in environment")
        
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        
        return flow
    except Exception as e:
        raise ValueError("Google OAuth not properly configured. Please check your .env file.")

def start_auth():
    """Start OAuth flow"""
    try:
        # Clear any existing credentials to force fresh consent
        credentials_manager.clear_user_credentials()
        if "credentials" in session:
            del session["credentials"]
            
        flow = get_auth_flow()
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="select_account consent"  # Force account selection and consent
        )
        session["state"] = state
        return redirect(auth_url)
    except Exception as e:
        raise e

def finish_auth():
    """Finish OAuth flow and store credentials securely"""
    try:
        flow = get_auth_flow()
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        if not credentials.refresh_token:
            raise Exception("No refresh token received. Please revoke access in Google account settings and try again.")
        
        # Get Google user info for account linking
        temp_creds = Credentials(
            token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=credentials.scopes
        )
        
        try:
            oauth_service = build("oauth2", "v2", credentials=temp_creds)
            google_user_info = oauth_service.userinfo().get().execute()
        except Exception:
            google_user_info = None
        
        # Prepare credentials data using environment variables
        credentials_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "scopes": credentials.scopes
        }
        
        # Store credentials securely
        credentials_manager.store_user_credentials(credentials_data)
        
        # Also store in session for immediate use
        session["credentials"] = credentials_data
        session["google_user_info"] = google_user_info
        
        # Update integration manager with Google Sheets connection status
        from database.models import DatabaseManager
        from database.managers import DatabaseIntegrationManager
        
        # We can't update user-specific integration status here without user context
        # This will be handled in the OAuth callback in app.py
        
        return True
    except Exception as e:
        raise e

def get_sheets_service():
    """Get Google Sheets service with secure credentials"""
    
    # Try to get credentials from session first
    creds_data = session.get("credentials")
    
    # If not in session, try to get from secure storage
    if not creds_data:
        creds_data = credentials_manager.get_user_credentials()
        if creds_data:
            session["credentials"] = creds_data
    
    if not creds_data:
        raise ValueError("No valid credentials found. Please authenticate first.")
    
    creds = Credentials(**creds_data)
    return build("sheets", "v4", credentials=creds)

def get_user_info():
    """Get user information from Google OAuth"""
    try:
        
        # Try to get credentials from session first
        creds_data = session.get("credentials")
        
        # If not in session, try to get from secure storage
        if not creds_data:
            creds_data = credentials_manager.get_user_credentials()
            if creds_data:
                session["credentials"] = creds_data
        
        if not creds_data:
            return None
        
        creds = Credentials(**creds_data)
        
        # Get user info from Google OAuth2 API
        service = build("oauth2", "v2", credentials=creds)
        user_info = service.userinfo().get().execute()
        
        return user_info
        
    except Exception:
        return None
