"""
Authentication middleware for Flask web application.

Provides simple API key authentication for protecting API endpoints.
"""
from functools import wraps
from flask import request, jsonify
import sys
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import config


def require_api_key(f):
    """
    Decorator to require API key authentication for Flask routes.

    Usage:
        @app.route('/api/protected')
        @require_api_key
        def protected_endpoint():
            return jsonify({'message': 'Access granted'})

    The API key should be provided in one of two ways:
    1. Authorization header: Authorization: Bearer <api_key>
    2. Query parameter: ?api_key=<api_key>

    If REQUIRE_AUTH is False in config, authentication is bypassed.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip authentication if not required
        if not config.REQUIRE_AUTH:
            return f(*args, **kwargs)

        # No API key configured but auth is required
        if not config.API_KEY:
            return jsonify({
                'error': 'Authentication not configured',
                'message': 'Server configuration error: API_KEY not set'
            }), 500

        # Get API key from request
        api_key = None

        # Check Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header:
            # Support both "Bearer <key>" and just "<key>"
            if auth_header.startswith('Bearer '):
                api_key = auth_header[7:]
            else:
                api_key = auth_header

        # Check query parameter as fallback
        if not api_key:
            api_key = request.args.get('api_key')

        # Validate API key
        if not api_key:
            return jsonify({
                'error': 'Authentication required',
                'message': 'API key must be provided via Authorization header or api_key parameter'
            }), 401

        if api_key != config.API_KEY:
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is invalid'
            }), 403

        # Authentication successful
        return f(*args, **kwargs)

    return decorated_function


def optional_api_key(f):
    """
    Decorator for endpoints that support optional authentication.

    If authentication is provided and valid, sets request.authenticated = True.
    If authentication is invalid, returns 403 error.
    If no authentication provided, allows request through with request.authenticated = False.

    Usage:
        @app.route('/api/optional')
        @optional_api_key
        def optional_endpoint():
            if request.authenticated:
                return jsonify({'message': 'Authenticated access', 'premium': True})
            return jsonify({'message': 'Public access', 'premium': False})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Mark as not authenticated by default
        request.authenticated = False

        # Skip if auth not required
        if not config.REQUIRE_AUTH:
            request.authenticated = True
            return f(*args, **kwargs)

        # No API key configured
        if not config.API_KEY:
            return f(*args, **kwargs)

        # Get API key from request
        api_key = None

        auth_header = request.headers.get('Authorization')
        if auth_header:
            if auth_header.startswith('Bearer '):
                api_key = auth_header[7:]
            else:
                api_key = auth_header

        if not api_key:
            api_key = request.args.get('api_key')

        # If API key provided, validate it
        if api_key:
            if api_key != config.API_KEY:
                return jsonify({
                    'error': 'Invalid API key',
                    'message': 'The provided API key is invalid'
                }), 403
            request.authenticated = True

        return f(*args, **kwargs)

    return decorated_function
