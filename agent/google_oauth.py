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
    flow = get_auth_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true"
    )
    session["state"] = state
    return redirect(auth_url)

def finish_auth():
    flow = get_auth_flow()
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    session["credentials"] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }
    return True

def get_sheets_service():
    from google.oauth2.credentials import Credentials
    creds = Credentials(**session["credentials"])
    return build("sheets", "v4", credentials=creds)
