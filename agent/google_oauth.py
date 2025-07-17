import os
from flask import session, redirect, request, url_for
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]
CLIENT_SECRET_FILE = "client_secret.json"

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # autorise HTTP (test uniquement)

def get_auth_flow():
    return Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri=url_for("oauth2callback", _external=True)
    )

def start_auth():
    # Clear any existing credentials to force fresh consent
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

def finish_auth():
    try:
        flow = get_auth_flow()
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        # Read client secrets to get client_id and client_secret
        import json
        with open(CLIENT_SECRET_FILE, 'r') as f:
            client_secrets = json.load(f)
        
        client_info = client_secrets['web']
        
        # Debug: Check what we got from OAuth
        print(f"OAuth token: {credentials.token is not None}")
        print(f"OAuth refresh_token: {credentials.refresh_token is not None}")
        print(f"OAuth scopes: {credentials.scopes}")
        
        if not credentials.refresh_token:
            print("WARNING: No refresh token received. User may need to revoke access and re-authorize.")
            raise Exception("No refresh token received. Please revoke access in Google account settings and try again.")
        
        # Ensure all required fields are present
        session["credentials"] = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": client_info['token_uri'],
            "client_id": client_info['client_id'],
            "client_secret": client_info['client_secret'],
            "scopes": credentials.scopes
        }
        
        # Debug: Verify what we stored
        stored_creds = session["credentials"]
        print(f"Stored credentials keys: {list(stored_creds.keys())}")
        print(f"All required fields present: {all(field in stored_creds for field in ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret'])}")
        
        # Update integration manager with Google Sheets connection status
        from agent.integrations import IntegrationManager
        integration_manager = IntegrationManager()
        integration_manager.update_google_sheets_status(True)
        
        return True
    except Exception as e:
        print(f"Error in finish_auth: {e}")
        raise e

def get_sheets_service():
    from google.oauth2.credentials import Credentials
    creds = Credentials(**session["credentials"])
    return build("sheets", "v4", credentials=creds)
