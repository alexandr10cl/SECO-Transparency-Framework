import logging
import os
from datetime import timedelta

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix


# Load environment variables from .env file
load_dotenv()

# Initialize the Flask app
app = Flask(__name__)

# The platform terminates TLS at the edge and forwards over plain HTTP. Without this
# the scheme and host come from that internal hop, and url_for(_external=True) builds
# the e-mail verification link in views/auth.py as http:// with the wrong host.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Defaults to production so a missing variable errs on the strict side: it used to
# silently turn SESSION_COOKIE_SECURE off.
FLASK_ENV = os.environ.get("FLASK_ENV", "production")
IS_PRODUCTION = FLASK_ENV == "production"

# from_pyfile first: it feeds app.config from database.py, and running it after the
# SECRET_KEY assignment is what used to overwrite the key.
app.config.from_pyfile('database.py')

# Security configurations
# The "dev-secret" fallback is public in this repository and the session cookie carries
# the UX-Tracking JWT (services/uxt_service.py), so production has to fail loudly.
_secret_key = os.environ.get("SECRET_KEY")
if not _secret_key:
    if IS_PRODUCTION:
        raise RuntimeError(
            "SECRET_KEY is required when FLASK_ENV=production. "
            'Generate one with: python -c "import secrets;print(secrets.token_urlsafe(64))"'
        )
    _secret_key = "dev-secret"
app.config["SECRET_KEY"] = _secret_key

# Fix #1: Add session timeout (24 hours)
# Sessions will expire after 24 hours of inactivity for security
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)
app.config["SESSION_COOKIE_SECURE"] = IS_PRODUCTION  # HTTPS only in production
app.config["SESSION_COOKIE_HTTPONLY"] = True  # Prevent JavaScript access to session cookie
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # CSRF protection

# Under gunicorn, app.logger has no handler of its own and inherits the root level
# (WARNING), which hides every app.logger.info - the heatmap prefetch among them.
_gunicorn_logger = logging.getLogger("gunicorn.error")
if _gunicorn_logger.handlers:
    app.logger.handlers = _gunicorn_logger.handlers
app.logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())

# Initialize the database
db = SQLAlchemy(app)

# Initialize the migration
migrate = Migrate(app, db)

# Feature flags (see config_flags.py and .env.example)
from config_flags import DEV_MODE, UXT_INTEGRATION, AI_ANALYSIS, AI_ALLOW_REGENERATE
app.logger.warning(
    "Startup flags: DEV_MODE=%s | UXT_INTEGRATION=%s | AI_ANALYSIS=%s (regenerate=%s)",
    DEV_MODE, UXT_INTEGRATION, AI_ANALYSIS, AI_ALLOW_REGENERATE
)

# Importing views
from views.index import *
from views.pages import *
from views.auth import *
from views.admin import *
from views.api import *
from views.ai_analysis import *
from external.tasks import *
from views import pages, auth  # We gebruiken pages.py voor de API endpoints

# Importing models
from models import *

# Importing func to init db
from models.database import init_db
init_db()

# Register CLI commands (e.g. flask seed)
from commands import register_commands
register_commands(app)

# Context processor to make video URLs available to all templates
@app.context_processor
def inject_video_urls():
    # YouTube embed URLs
    return {
        'extension_video_url': 'https://www.youtube.com/embed/-jC_3eWaUf8',
        'tool_video_url': 'https://www.youtube.com/embed/LC0DVUUFau4'
    }

# Fix #4: Global error handlers for database connection issues
# Handle database connection errors gracefully instead of crashing
from sqlalchemy.exc import OperationalError, DisconnectionError, DatabaseError
from flask import jsonify, render_template

@app.errorhandler(OperationalError)
def handle_db_operational_error(e):
    """Handle database connection/operational errors"""
    db.session.rollback()  # Rollback any pending transactions
    print(f"Database operational error: {str(e)}")
    return render_template('error.html', 
                         error_code=503,
                         error_message="Database service is temporarily unavailable. Please try again later."), 503

@app.errorhandler(DisconnectionError)
def handle_db_disconnection_error(e):
    """Handle database disconnection errors"""
    db.session.rollback()
    print(f"Database disconnection error: {str(e)}")
    return render_template('error.html',
                         error_code=503,
                         error_message="Lost connection to database. Please refresh and try again."), 503

@app.errorhandler(DatabaseError)
def handle_db_error(e):
    """Handle general database errors"""
    db.session.rollback()
    print(f"Database error: {str(e)}")
    return render_template('error.html',
                         error_code=500,
                         error_message="A database error occurred. Please try again or contact support."), 500

@app.errorhandler(500)
def handle_internal_error(e):
    """Handle internal server errors"""
    db.session.rollback()  # Always rollback on 500 errors
    print(f"Internal server error: {str(e)}")
    return render_template('error.html',
                         error_code=500,
                         error_message="An internal error occurred. Please try again later."), 500

@app.errorhandler(404)
def handle_not_found(e):
    """Handle 404 errors with custom page"""
    return render_template('error.html',
                         error_code=404,
                         error_message="The page you're looking for doesn't exist."), 404

# Run the app
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
