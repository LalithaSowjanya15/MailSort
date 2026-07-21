from datetime import datetime, timedelta
from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from database.mongodb import get_db
from utils.helpers import logger

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
def index():
    """Serves the Landing page. If the user is logged in, redirects to the Dashboard."""
    if "user_email" in session:
        return redirect(url_for("dashboard.dashboard_page"))
    return render_template("login.html")

@dashboard_bp.route("/dashboard")
def dashboard_page():
    """Serves the main dashboard workspace. Enforces authentication."""
    if "user_email" not in session:
        return redirect(url_for("dashboard.index"))
    return render_template("dashboard.html")

@dashboard_bp.route("/api/dashboard", methods=["GET"])
def get_dashboard_data():
    """Returns dashboard overview metrics and recent email summary list."""
    user_email = session.get("user_email")
    if not user_email:
        return jsonify({"error": "Unauthorized"}), 401
        
    db = get_db()
    
    try:
        # Fetch all user emails to calculate metrics
        cursor = db.emails.find({"user_email": user_email}).sort("created_at", -1)
        emails = list(cursor)
        
        # Calculate overview counts
        total_emails = len(emails)
        urgent_count = sum(1 for e in emails if e.get("priority") == "Urgent")
        reply_now_count = sum(1 for e in emails if e.get("priority") == "Reply Now")
        read_later_count = sum(1 for e in emails if e.get("priority") == "Read Later")
        ignore_count = sum(1 for e in emails if e.get("priority") == "Ignore")
        
        # Get recent 10 emails
        recent_emails = emails[:10]
        
        for em in recent_emails:
            if "_id" in em:
                em["_id"] = str(em["_id"])
                
        return jsonify({
            "success": True,
            "metrics": {
                "total": total_emails,
                "urgent": urgent_count,
                "reply_now": reply_now_count,
                "read_later": read_later_count,
                "ignore": ignore_count
            },
            "recent_emails": recent_emails
        })
        
    except Exception as e:
        logger.error(f"Error compiling dashboard metrics: {e}")
        return jsonify({"error": "Failed to load dashboard metrics", "details": str(e)}), 500

@dashboard_bp.route("/api/analytics", methods=["GET"])
def get_analytics_data():
    """Aggregates and returns category distribution, priority distribution, and trends for charts."""
    user_email = session.get("user_email")
    if not user_email:
        return jsonify({"error": "Unauthorized"}), 401
        
    db = get_db()
    
    try:
        cursor = db.emails.find({"user_email": user_email})
        emails = list(cursor)
        
        # 1. Priority Distribution
        priorities = {"Urgent": 0, "Reply Now": 0, "Read Later": 0, "Ignore": 0}
        
        # 2. Category Distribution
        active_categories = ["Client", "Manager", "HR", "Meeting", "Personal", "Promotion", "Security"]
        categories = {cat: 0 for cat in active_categories}
        
        # 3. Daily trends (past 7 days)
        today = datetime.now().date()
        past_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        daily_trends = {day.strftime("%a %d"): 0 for day in past_7_days}
        
        for em in emails:
            # Aggregate priorities
            priority_val = em.get("priority")
            if priority_val in priorities:
                priorities[priority_val] += 1
                
            # Aggregate categories
            cat_val = em.get("category")
            if cat_val in categories:
                categories[cat_val] += 1
            elif cat_val:
                categories[cat_val] = categories.get(cat_val, 0) + 1
                
            # Aggregate daily trends
            created_time = em.get("created_at", 0)
            if created_time:
                em_date = datetime.fromtimestamp(created_time).date()
                date_str = em_date.strftime("%a %d")
                if date_str in daily_trends:
                    daily_trends[date_str] += 1
                    
        # Structure data for Chart.js
        return jsonify({
            "success": True,
            "priority_distribution": {
                "labels": list(priorities.keys()),
                "data": list(priorities.values())
            },
            "category_distribution": {
                "labels": list(categories.keys()),
                "data": list(categories.values())
            },
            "daily_trends": {
                "labels": list(daily_trends.keys()),
                "data": list(daily_trends.values())
            }
        })
        
    except Exception as e:
        logger.error(f"Error compiling analytics metrics: {e}")
        return jsonify({"error": "Failed to compile analytics", "details": str(e)}), 500
