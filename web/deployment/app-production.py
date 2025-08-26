#!/usr/bin/env python3
"""
Production configuration wrapper for the Flask application.
This file ensures the app runs in production mode with appropriate settings.
"""

import os
import sys

# Add parent directory to path to import the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

if __name__ == '__main__':
    # Production configuration
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
    
    # Run the application
    # In production, you might want to use a proper WSGI server like Gunicorn
    # For now, we'll use Flask's built-in server with production settings
    app.run(
        host='0.0.0.0',  # Listen on all interfaces
        port=5000,        # Port 5000
        debug=False,      # No debug mode in production
        use_reloader=False  # Disable reloader in production
    )