from flask import Flask, jsonify
from config import Config
from database.mongodb import init_db
from routes.auth import auth_bp
from routes.gmail import gmail_bp
from routes.dashboard import dashboard_bp
from utils.helpers import logger

def create_app():
    """Application factory to configure and initialize the Flask application."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize Database connection
    init_db()

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(gmail_bp)
    app.register_blueprint(dashboard_bp)

    # Register global error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

    logger.info("MailSort Flask application initialized successfully.")
    return app

app = create_app()

if __name__ == "__main__":
    # In development mode, we run on localhost port 5000
    app.run(host="0.0.0.0", port=5000, debug=Config.DEBUG)
