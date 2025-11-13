from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# Initialize the Flask app
app = Flask(__name__)

import os
from datetime import timedelta

# Security configurations
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")
app.config.from_pyfile('database.py')

# Fix #1: Add session timeout (24 hours)
# Sessions will expire after 24 hours of inactivity for security
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") == "production"  # HTTPS only in production
app.config["SESSION_COOKIE_HTTPONLY"] = True  # Prevent JavaScript access to session cookie
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # CSRF protection

# Initialize the database
db = SQLAlchemy(app)

# Initialize the migration
migrate = Migrate(app, db) 

# Importing views
from views.index import *
from views.pages import *
from views.auth import *
from views.admin import *
from views.api import *
from external.tasks import *
from views import pages, auth  # We gebruiken pages.py voor de API endpoints

# Importing models
from models import *

# Importing func to init db
from models.database import init_db
init_db()

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
