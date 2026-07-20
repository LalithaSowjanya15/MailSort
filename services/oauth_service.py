import json
import requests
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from config import Config
from utils.helpers import logger

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly"
]

def get_oauth_flow(state=None):
    """Initializes and returns a Google OAuth Flow object."""
    if Config.MOCK_MODE:
        return None
        
    client_config = Config.get_google_client_config()
    
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        state=state
    )
    flow.redirect_uri = Config.GOOGLE_REDIRECT_URI
    return flow

def get_authorization_url():
    """Generates the authorization URL and state for user login redirection."""
    if Config.MOCK_MODE:
        # Return mock authorization link that calls our local mock callback
        logger.info("MOCK_MODE: Generating mock authorization URL.")
        return "/auth/callback?mock=true", "mock-state"
        
    flow = get_oauth_flow()
    if not flow:
        raise ValueError("Google OAuth configuration is missing.")
        
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    return authorization_url, state

def get_credentials_from_code(code, state):
    """Exchanges an authorization code for credentials and returns user info."""
    if Config.MOCK_MODE or code == "mock_code" or state == "mock-state":
        # Simulating callback user profile retrieval
        logger.info("MOCK_MODE: Simulating user credentials retrieval.")
        mock_creds = {
            "token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "mock_client_id",
            "client_secret": "mock_client_secret",
            "scopes": SCOPES
        }
        user_info = {
            "email": "demo@mailsort.ai",
            "name": "Demo User",
            "picture": "https://lh3.googleusercontent.com/a/default-user=s96-c"
        }
        return mock_creds, user_info
        
    flow = get_oauth_flow(state=state)
    flow.fetch_token(code=code)
    
    credentials = flow.credentials
    
    # Fetch User Profile info from Google OAuth endpoint
    session = flow.authorized_session()
    user_info_resp = session.get("https://www.googleapis.com/oauth2/v3/userinfo")
    user_info_resp.raise_for_status()
    user_info = user_info_resp.json()
    
    # Structure credentials data
    credentials_dict = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }
    
    return credentials_dict, user_info

def build_google_credentials(credentials_dict, user_email=None):
    """Reconstructs the google.oauth2.credentials.Credentials object from a dictionary."""
    if Config.MOCK_MODE or not credentials_dict or credentials_dict.get("token") == "mock_access_token":
        return None
        
    creds = Credentials(
        token=credentials_dict.get("token"),
        refresh_token=credentials_dict.get("refresh_token"),
        token_uri=credentials_dict.get("token_uri"),
        client_id=credentials_dict.get("client_id"),
        client_secret=credentials_dict.get("client_secret"),
        scopes=credentials_dict.get("scopes")
    )
    
    # If the access token has expired, refresh it
    if creds.expired and creds.refresh_token:
        try:
            logger.info("Access token expired. Refreshing...")
            creds.refresh(Request())
            # Update the source dict with refreshed token
            credentials_dict["token"] = creds.token
            logger.info("Successfully refreshed Google OAuth token.")
            
            # Save back to database if user_email is provided
            if user_email:
                try:
                    from database.mongodb import get_db
                    db = get_db()
                    db.users.update_one(
                        {"email": user_email},
                        {"$set": {"credentials.token": creds.token}}
                    )
                    logger.info(f"Refreshed token saved to database for user {user_email}.")
                except Exception as db_e:
                    logger.error(f"Failed to update refreshed token in database: {db_e}")
        except Exception as e:
            logger.error(f"Error refreshing access token: {e}")
            
    return creds
