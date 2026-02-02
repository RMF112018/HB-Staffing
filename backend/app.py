from flask import Flask, jsonify, current_app, request
from flask_cors import CORS
from config import config
from db import db
import logging
from errors import register_error_handlers


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

    # Create tables on startup
    with app.app_context():
        db.create_all()

    # Register blueprints
    from routes import api
    app.register_blueprint(api, url_prefix='/api')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5002, debug=True)
