import time
from flask import Blueprint, redirect, request, session, url_for, jsonify
from services.oauth_service import get_authorization_url, get_credentials_from_code
from database.mongodb import get_db
from utils.helpers import logger

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/auth/login")
def login():
    """Redirects the user to the Google OAuth Login screen."""
    try:
        auth_url, state = get_authorization_url()
        session["oauth_state"] = state
        return redirect(auth_url)
    except Exception as e:
        logger.error(f"Error starting OAuth login: {e}")
        return jsonify({"error": "Failed to start Google OAuth process", "details": str(e)}), 500

@auth_bp.route("/auth/callback")
def callback():
    """Handles the redirect back from Google OAuth, exchanges the authorization code."""
    db = get_db()
    
    # Check for mock parameter or standard oauth callback
    is_mock = request.args.get("mock") == "true" or request.args.get("state") == "mock-state"
    
    code = request.args.get("code")
    state = request.args.get("state")
    
    # In standard OAuth flow, we check the state parameter to prevent CSRF
    if not is_mock and (not state or state != session.get("oauth_state")):
        logger.warning(f"OAuth state mismatch. Received state: {state}, Expected: {session.get('oauth_state')}")
        return redirect(url_for("dashboard.index", login_error="CSRF validation failed"))
        
    try:
        # If mock mode, bypass actual token exchange
        if is_mock:
            credentials_dict, user_info = get_credentials_from_code("mock_code", "mock-state")
        else:
            credentials_dict, user_info = get_credentials_from_code(code, state)
            
        email = user_info.get("email")
        if not email:
            raise ValueError("Google user profile did not return an email address.")
            
        # Save or update user credentials in MongoDB
        # If the user already has a refresh_token, preserve it if the new credentials_dict lacks one
        existing_user = db.users.find_one({"email": email})
        if existing_user and not credentials_dict.get("refresh_token"):
            old_creds = existing_user.get("credentials", {})
            if old_creds.get("refresh_token"):
                credentials_dict["refresh_token"] = old_creds.get("refresh_token")

        db.users.update_one(
            {"email": email},
            {
                "$set": {
                    "email": email,
                    "name": user_info.get("name"),
                    "picture": user_info.get("picture"),
                    "credentials": credentials_dict,
                    "updated_at": time.time()
                }
            },
            upsert=True
        )
        
        # Log user into local session
        session["user_email"] = email
        session["user_name"] = user_info.get("name", "User")
        session["user_picture"] = user_info.get("picture", "")
        
        logger.info(f"User {email} logged in successfully via OAuth.")
        
        # Clean up session state variable
        session.pop("oauth_state", None)
        
        return redirect(url_for("dashboard.dashboard_page"))
        
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        return redirect(url_for("dashboard.index", login_error="OAuth token exchange failed"))

@auth_bp.route("/auth/logout")
def logout():
    """Clears the user session and logs the user out."""
    email = session.get("user_email")
    session.clear()
    logger.info(f"User {email} logged out.")
    return redirect(url_for("dashboard.index"))

@auth_bp.route("/auth/status")
def status():
    """API endpoint to check if the current session is authenticated."""
    if "user_email" in session:
        return jsonify({
            "authenticated": True,
            "user": {
                "email": session["user_email"],
                "name": session.get("user_name"),
                "picture": session.get("user_picture")
            }
        })
    return jsonify({"authenticated": False})
