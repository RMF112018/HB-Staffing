"""
HB-Staffing API - Flask application for construction project staffing management

This is the main entry point for the HB-Staffing web application backend.
It provides RESTful API endpoints for managing staff, projects, assignments,
forecasting, and reporting.

Features:
- JWT-based authentication with role-based access control
- Complete CRUD operations for staff, projects, and assignments
- Advanced forecasting engine for staffing needs prediction
- Comprehensive reporting with CSV/PDF export
- Rate limiting and security headers
- Docker containerization support
- PostgreSQL database with migration support

Environment Variables:
- FLASK_ENV: development/production
- DATABASE_URL: Database connection string
- SECRET_KEY: Flask secret key
- JWT_SECRET_KEY: JWT signing key
- CORS_ORIGINS: Allowed CORS origins

Usage:
    python app.py

Or with Gunicorn (production):
    gunicorn app:create_app() --bind 0.0.0.0:8000
"""

from flask import Flask, jsonify, current_app, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import config
from db import db
import logging
from errors import register_error_handlers
from auth import init_auth, create_default_admin
from flask_migrate import Migrate


def configure_logging(app, config_name='development'):
    """Configure logging for the application"""
    # Clear existing handlers
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)

    # Set log level
    log_level = logging.INFO if app.config.get('DEBUG', False) else logging.WARNING
    app.logger.setLevel(log_level)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)

    # Add handler to logger
    app.logger.addHandler(console_handler)

    # Log application startup
    app.logger.info(f"HB-Staffing API starting in {config_name} mode")


def create_app(config_name='development'):
    """Application factory pattern"""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])

    # Configure logging
    configure_logging(app, config_name)

    # Initialize extensions
    db.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])

    # Initialize rate limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )

    # Initialize authentication
    init_auth(app)

    # Initialize Flask-Migrate
    migrate = Migrate(app, db)

    # Register error handlers
    register_error_handlers(app)

    # Request logging middleware
    @app.before_request
    def log_request_info():
        current_app.logger.info(f'{request.method} {request.url} - {request.remote_addr}')

    @app.after_request
    def log_response_info(response):
        current_app.logger.info(f'Response: {response.status_code}')
        return response

    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint to verify API is running"""
        return jsonify({
            'status': 'healthy',
            'message': 'HB-Staffing API is running'
        })

    # Initialize and seed database on startup
    with app.app_context():
        from database import init_db, seed_database
        init_db()
        seed_database()

    # Register blueprints
    from routes import api
    app.register_blueprint(api, url_prefix='/api')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5002, debug=True)
