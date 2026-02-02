"""
Custom error classes and error handling utilities for HB-Staffing API
"""

from flask import jsonify, current_app
import logging

# Set up logger
logger = logging.getLogger(__name__)


class HBStaffingError(Exception):
    """Base exception class for HB-Staffing application"""

    def __init__(self, message, status_code=400, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload


class ValidationError(HBStaffingError):
    """Raised when input validation fails"""

    def __init__(self, message, field=None):
        super().__init__(message, 400, {'field': field} if field else None)


class NotFoundError(HBStaffingError):
    """Raised when a requested resource is not found"""

    def __init__(self, resource_type, resource_id=None):
        message = f"{resource_type} not found"
        if resource_id:
            message += f" with id {resource_id}"
        super().__init__(message, 404)


class ConflictError(HBStaffingError):
    """Raised when an operation would result in a conflict"""

    def __init__(self, message):
        super().__init__(message, 409)


class UnauthorizedError(HBStaffingError):
    """Raised when authentication/authorization fails"""

    def __init__(self, message="Unauthorized access"):
        super().__init__(message, 401)


class ForbiddenError(HBStaffingError):
    """Raised when access to a resource is forbidden"""

    def __init__(self, message="Access forbidden"):
        super().__init__(message, 403)


class BusinessLogicError(HBStaffingError):
    """Raised when business logic constraints are violated"""

    def __init__(self, message):
        super().__init__(message, 422)  # Unprocessable Entity


def register_error_handlers(app):
    """Register error handlers with the Flask app"""

    @app.errorhandler(HBStaffingError)
    def handle_hb_staffing_error(error):
        """Handle custom HB-Staffing errors"""
        logger.warning(f"HB-Staffing Error: {error.message}", extra={
            'status_code': error.status_code,
            'payload': error.payload
        })

        response = {
            'error': {
                'type': error.__class__.__name__,
                'message': error.message
            }
        }

        if error.payload:
            response['error']['details'] = error.payload

        return jsonify(response), error.status_code

    @app.errorhandler(400)
    def handle_bad_request(error):
        """Handle 400 Bad Request errors"""
        logger.warning(f"Bad Request: {error.description}")
        return jsonify({
            'error': {
                'type': 'BadRequest',
                'message': error.description or 'Bad request'
            }
        }), 400

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 Not Found errors"""
        logger.info(f"Not Found: {error.description}")
        return jsonify({
            'error': {
                'type': 'NotFound',
                'message': error.description or 'Resource not found'
            }
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle 405 Method Not Allowed errors"""
        logger.warning(f"Method Not Allowed: {error.description}")
        return jsonify({
            'error': {
                'type': 'MethodNotAllowed',
                'message': 'Method not allowed for this endpoint'
            }
        }), 405

    @app.errorhandler(422)
    def handle_unprocessable_entity(error):
        """Handle 422 Unprocessable Entity errors"""
        logger.warning(f"Unprocessable Entity: {error.description}")
        return jsonify({
            'error': {
                'type': 'UnprocessableEntity',
                'message': error.description or 'Unprocessable entity'
            }
        }), 422

    @app.errorhandler(500)
    def handle_internal_server_error(error):
        """Handle 500 Internal Server Error"""
        logger.error(f"Internal Server Error: {error.description}", exc_info=True)
        return jsonify({
            'error': {
                'type': 'InternalServerError',
                'message': 'An unexpected error occurred. Please try again later.'
            }
        }), 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle unexpected errors"""
        logger.error(f"Unexpected Error: {str(error)}", exc_info=True)
        return jsonify({
            'error': {
                'type': 'UnexpectedError',
                'message': 'An unexpected error occurred. Please contact support if this persists.'
            }
        }), 500


def validate_required(data, fields):
    """Validate that required fields are present in data"""
    missing = []
    for field in fields:
        if field not in data or data[field] is None or (isinstance(data[field], str) and data[field].strip() == ''):
            missing.append(field)

    if missing:
        raise ValidationError(f"Missing required fields: {', '.join(missing)}")


def validate_date_range(start_date, end_date, start_field="start_date", end_field="end_date"):
    """Validate date range logic"""
    if start_date and end_date:
        if start_date >= end_date:
            raise ValidationError(f"{end_field} must be after {start_field}")


def validate_positive_number(value, field_name):
    """Validate that a value is a positive number"""
    try:
        num = float(value)
        if num <= 0:
            raise ValidationError(f"{field_name} must be a positive number")
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} must be a valid number")


def validate_enum(value, allowed_values, field_name):
    """Validate that a value is in an allowed set"""
    if value not in allowed_values:
        raise ValidationError(f"{field_name} must be one of: {', '.join(allowed_values)}")


def safe_db_operation(operation_func, error_message="Database operation failed"):
    """Safely execute database operations with error handling"""
    try:
        return operation_func()
    except Exception as e:
        logger.error(f"Database operation failed: {str(e)}")
        raise HBStaffingError(error_message) from e


def log_api_request(endpoint, method, user_id=None, **kwargs):
    """Log API requests for auditing"""
    logger.info(f"API Request: {method} {endpoint}", extra={
        'user_id': user_id,
        'method': method,
        'endpoint': endpoint,
        **kwargs
    })


def log_api_response(endpoint, method, status_code, response_time=None, **kwargs):
    """Log API responses for monitoring"""
    level = logging.INFO if status_code < 400 else logging.WARNING
    logger.log(level, f"API Response: {method} {endpoint} - {status_code}", extra={
        'status_code': status_code,
        'response_time': response_time,
        'method': method,
        'endpoint': endpoint,
        **kwargs
    })
