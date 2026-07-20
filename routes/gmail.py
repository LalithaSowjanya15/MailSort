from flask import Blueprint, jsonify, session, request
from database.mongodb import get_db
from services.email_processor import process_and_sync_emails
from utils.helpers import logger

gmail_bp = Blueprint("gmail_api", __name__)

@gmail_bp.route("/api/fetch-emails", methods=["GET"])
def fetch_emails():
    """Triggers the synchronization pipeline and returns the updated list of emails."""
    user_email = session.get("user_email")
    if not user_email:
        return jsonify({"error": "Unauthorized session"}), 401
        
    db = get_db()
    user_doc = db.users.find_one({"email": user_email})
    
    if not user_doc:
        return jsonify({"error": "User profile not found in database"}), 404
        
    credentials = user_doc.get("credentials")
    
    try:
        # Run the email sync and NLP analysis pipeline
        emails = process_and_sync_emails(user_email, credentials)
        
        # Strip _id object from MongoDB before returning as JSON
        for em in emails:
            if "_id" in em:
                em["_id"] = str(em["_id"])
                
        return jsonify({"success": True, "emails": emails})
        
    except Exception as e:
        logger.error(f"Error syncing emails for user {user_email}: {e}")
        return jsonify({"error": "Failed to sync and process emails", "details": str(e)}), 500

@gmail_bp.route("/api/email/<gmail_id>", methods=["GET"])
def get_email_details(gmail_id):
    """Retrieves full analytical insights for a specific email and marks it as read."""
    user_email = session.get("user_email")
    if not user_email:
        return jsonify({"error": "Unauthorized session"}), 401
        
    db = get_db()
    email_doc = db.emails.find_one({"gmail_id": gmail_id, "user_email": user_email})
    
    if not email_doc:
        return jsonify({"error": "Email analysis not found"}), 404
        
    # Mark as read if currently unread
    if email_doc.get("status") == "unread":
        try:
            db.emails.update_one(
                {"gmail_id": gmail_id, "user_email": user_email},
                {"$set": {"status": "read"}}
            )
            email_doc["status"] = "read"
        except Exception as e:
            logger.error(f"Failed to update email read status in DB: {e}")
            
    # Strip database ID object
    if "_id" in email_doc:
        email_doc["_id"] = str(email_doc["_id"])
        
    return jsonify({"success": True, "email": email_doc})

@gmail_bp.route("/api/search", methods=["GET"])
def search_emails():
    """Searches user's processed emails matching a specific keyword."""
    user_email = session.get("user_email")
    if not user_email:
        return jsonify({"error": "Unauthorized session"}), 401
        
    query_term = request.args.get("q", "").strip()
    if not query_term:
        return jsonify({"success": True, "emails": []})
        
    db = get_db()
    
    # Simple regex search across Subject, Sender, and Body
    search_filter = {
        "user_email": user_email,
        "$or": [
            {"subject": {"$regex": query_term, "$options": "i"}},
            {"sender": {"$regex": query_term, "$options": "i"}},
            {"body": {"$regex": query_term, "$options": "i"}}
        ]
    }
    
    try:
        cursor = db.emails.find(search_filter).sort("created_at", -1)
        emails = list(cursor)
        
        for em in emails:
            if "_id" in em:
                em["_id"] = str(em["_id"])
                
        return jsonify({"success": True, "emails": emails})
        
    except Exception as e:
        logger.error(f"Error running search query: {e}")
        return jsonify({"error": "Search failed", "details": str(e)}), 500
