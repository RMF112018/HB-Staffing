"""
Authentication and authorization module for HB-Staffing API
"""

from flask_jwt_extended import (
    JWTManager, jwt_required, get_jwt_identity,
    create_access_token, create_refresh_token,
    get_jwt, verify_jwt_in_request
)
from flask import current_app, request, jsonify, g
from functools import wraps
from datetime import datetime
from models import User
from errors import UnauthorizedError, ForbiddenError
import logging

logger = logging.getLogger(__name__)

# Initialize JWT manager
jwt = JWTManager()

def init_auth(app):
    """Initialize authentication for the Flask app"""
    # Ensure JWT secret key is set
    if not app.config.get('JWT_SECRET_KEY'):
        app.config['JWT_SECRET_KEY'] = 'dev-jwt-secret-key-change-in-production'

    jwt.init_app(app)

    # JWT callbacks
    @jwt.user_identity_loader
    def user_identity_lookup(user):
        return user.id

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return User.query.get(identity)

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'error': {
                'type': 'TokenExpired',
                'message': 'Token has expired'
            }
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'error': {
                'type': 'InvalidToken',
                'message': 'Invalid token'
            }
        }), 401

    @jwt.unauthorized_loader
    def unauthorized_callback(error):
        return jsonify({
            'error': {
                'type': 'Unauthorized',
                'message': 'Missing or invalid token'
            }
        }), 401


def login_user(username, password):
    """Authenticate user and return tokens"""
    user = User.get_by_username(username)

    if not user or not user.check_password(password):
        logger.warning(f"Failed login attempt for username: {username}")
        raise UnauthorizedError("Invalid username or password")

    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {username}")
        raise ForbiddenError("Account is deactivated")

    # Update last login
    user.last_login = datetime.utcnow()

    # Create tokens
    access_token = create_access_token(identity=user)
    refresh_token = create_refresh_token(identity=user)

    logger.info(f"Successful login for user: {username}")

    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    }


def refresh_access_token():
    """Refresh access token using refresh token"""
    current_user = get_jwt_identity()
    user = User.query.get(current_user)

    if not user or not user.is_active:
        raise ForbiddenError("User account is invalid or deactivated")

    access_token = create_access_token(identity=user)
    return {'access_token': access_token}


def register_user(username, email, password, role='preconstruction'):
    """Register a new user (admin only)"""
    from errors import ConflictError, ValidationError

    # Check if username or email already exists
    if User.get_by_username(username):
        raise ConflictError("Username already exists")

    if User.get_by_email(email):
        raise ConflictError("Email already exists")

    # Validate role
    valid_roles = ['preconstruction', 'leadership', 'admin']
    if role not in valid_roles:
        raise ValidationError(f"Invalid role. Must be one of: {', '.join(valid_roles)}")

    # Create user
    user = User(username=username, email=email, password=password, role=role)

    from db import db
    db.session.add(user)
    db.session.commit()

    logger.info(f"New user registered: {username} with role: {role}")

    return user.to_dict()


def require_role(required_role):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def wrapper(*args, **kwargs):
            current_user = get_jwt_identity()
            user = User.query.get(current_user)

            if not user:
                raise UnauthorizedError("User not found")

            if not user.is_active:
                raise ForbiddenError("Account is deactivated")

            if not user.has_role(required_role):
                raise ForbiddenError(f"Requires {required_role} role")

            g.current_user = user
            return f(*args, **kwargs)
        return wrapper
    return decorator


def require_permission(permission):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def wrapper(*args, **kwargs):
            current_user = get_jwt_identity()
            user = User.query.get(current_user)

            if not user:
                raise UnauthorizedError("User not found")

            if not user.is_active:
                raise ForbiddenError("Account is deactivated")

            if not user.has_permission(permission):
                raise ForbiddenError(f"Insufficient permissions: {permission}")

            g.current_user = user
            return f(*args, **kwargs)
        return wrapper
    return decorator


def optional_auth(f):
    """Decorator for optional authentication"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request(optional=True)
            current_user = get_jwt_identity()
            if current_user:
                user = User.query.get(current_user)
                if user and user.is_active:
                    g.current_user = user
        except Exception:
            # Authentication is optional, so ignore errors
            pass

        return f(*args, **kwargs)
    return wrapper


def get_current_user():
    """Get current authenticated user from global context"""
    return getattr(g, 'current_user', None)


def create_default_admin():
    """Create default admin user if none exists"""
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@hb-staffing.com',
            password='admin123!',  # Should be changed in production
            role='admin'
        )

        from db import db
        db.session.add(admin)
        db.session.commit()

        logger.info("Default admin user created")
        return admin

    return None
