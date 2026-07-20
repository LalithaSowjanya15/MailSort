import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Flask application configuration."""

    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "super-secret-key-change-me")
    ENV = os.environ.get("FLASK_ENV", "development")
    DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")

    # MongoDB
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/mailsort")

    # Google OAuth 2.0
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = os.environ.get(
        "GOOGLE_REDIRECT_URI", "http://localhost:5000/auth/callback"
    )

    # Mock Mode — runs the dashboard with sample data when real credentials are absent
    MOCK_MODE = os.environ.get("MOCK_MODE", "True").lower() in ("true", "1", "yes")

    @classmethod
    def get_google_client_config(cls):
        """Builds the Google OAuth client configuration dict required by the Flow."""
        return {
            "web": {
                "client_id": cls.GOOGLE_CLIENT_ID,
                "client_secret": cls.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": [cls.GOOGLE_REDIRECT_URI],
            }
        }
