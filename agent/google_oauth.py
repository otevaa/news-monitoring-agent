import os
import json
import tempfile
from flask import session, redirect, request, url_for
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from .secure_credentials import GoogleCredentialsManager
from .integrations import IntegrationManager

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile", 
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # autorise HTTP (test uniquement)

# Initialize secure credentials manager
credentials_manager = GoogleCredentialsManager()

def get_auth_flow():
    """Get OAuth flow with secure credentials"""
    try:
        # Get client configuration securely
        client_config = credentials_manager.get_client_config()
        
        # Create a temporary client secrets file for google-auth-oauthlib
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(client_config, temp_file)
            temp_file_path = temp_file.name
        
        flow = Flow.from_client_secrets_file(
            temp_file_path,
            scopes=SCOPES,
            redirect_uri=url_for("oauth2callback", _external=True)
        )
        
        # Clean up temporary file
        os.unlink(temp_file_path)
        
        return flow
    except Exception as e:
        print(f"Error creating auth flow: {e}")
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
            prompt="consent"  # Force consent to ensure refresh_token is provided
        )
        session["state"] = state
        return redirect(auth_url)
    except Exception as e:
        print(f"Error starting auth: {e}")
        raise e

def finish_auth():
    """Finish OAuth flow and store credentials securely"""
    try:
        flow = get_auth_flow()
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        # Get client configuration
        client_config = credentials_manager.get_client_config()
        client_info = client_config['web']
        
        # Debug: Check what we got from OAuth
        print(f"OAuth token: {credentials.token is not None}")
        print(f"OAuth refresh_token: {credentials.refresh_token is not None}")
        print(f"OAuth scopes: {credentials.scopes}")
        
        if not credentials.refresh_token:
            print("WARNING: No refresh token received. User may need to revoke access and re-authorize.")
            raise Exception("No refresh token received. Please revoke access in Google account settings and try again.")
        
        # Prepare credentials data
        credentials_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": client_info['token_uri'],
            "client_id": client_info['client_id'],
            "client_secret": client_info['client_secret'],
            "scopes": credentials.scopes
        }
        
        # Store credentials securely
        credentials_manager.store_user_credentials(credentials_data)
        
        # Also store in session for immediate use
        session["credentials"] = credentials_data
        
        # Debug: Verify what we stored
        print(f"Stored credentials keys: {list(credentials_data.keys())}")
        print(f"All required fields present: {all(field in credentials_data for field in ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret'])}")
        
        # Update integration manager with Google Sheets connection status
        integration_manager = IntegrationManager()
        integration_manager.update_google_sheets_status(True)
        
        return True
    except Exception as e:
        print(f"Error in finish_auth: {e}")
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
        
    except Exception as e:
        print(f"Error getting user info: {e}")
        return None
