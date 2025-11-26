"""
Pytest configuration and fixtures for validator testing.

This module provides Flask application fixtures and utilities for testing
WTForms validators, particularly the SenhaComplexa validator.
"""

import pytest
from flask import Flask
from app import create_app


@pytest.fixture
def app():
    """Create Flask app instance for testing.
    
    Creates a minimal Flask application with test configuration
    that can be used for validator testing without requiring
    a full database setup.
    
    Returns:
        Flask: Configured Flask application instance for testing.
    """
    # Create a minimal test app without loading config files
    test_app = Flask(__name__, instance_relative_config=True)
    
    # Set basic test configuration
    test_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key-for-validators',
        'WTF_CSRF_ENABLED': False,  # Disable CSRF for testing
        # Default password policy settings for testing
        'PASSWORD_MIN': 8,
        'PASSWORD_MAIUSCULA': True,
        'PASSWORD_MINUSCULA': True,
        'PASSWORD_NUMERO': True,
        'PASSWORD_SIMBOLO': True,
    })
    
    return test_app


@pytest.fixture
def app_context(app):
    """Provide Flask application context for validator testing.
    
    Creates and manages the Flask application context needed
    for validators that access current_app.config.
    
    Args:
        app (Flask): Flask application fixture.
        
    Yields:
        Flask application context: Active application context.
    """
    with app.app_context():
        yield app


@pytest.fixture
def password_config():
    """Provide configurable password policy settings for testing.
    
    Returns a dictionary with default password policy configuration
    that can be modified in individual tests to test different
    password validation scenarios.
    
    Returns:
        dict: Default password policy configuration.
    """
    return {
        'default': {
            'PASSWORD_MIN': 8,
            'PASSWORD_MAIUSCULA': True,
            'PASSWORD_MINUSCULA': True,
            'PASSWORD_NUMERO': True,
            'PASSWORD_SIMBOLO': True,
        },
        'minimal': {
            'PASSWORD_MIN': 0,
            'PASSWORD_MAIUSCULA': False,
            'PASSWORD_MINUSCULA': False,
            'PASSWORD_NUMERO': False,
            'PASSWORD_SIMBOLO': False,
        }
    }


@pytest.fixture
def mock_config(app_context, password_config):
    """Fixture for mocking Flask app configuration during tests.
    
    Provides a context manager that temporarily updates the Flask
    app configuration with test-specific password policy settings.
    
    Args:
        app_context: Flask application context fixture.
        password_config (dict): Default password configuration.
        
    Returns:
        function: Context manager for updating app configuration.
    """
    from flask import current_app
    
    def _mock_config(config_updates=None):
        """Context manager for temporarily updating app config.
        
        Args:
            config_updates (dict, optional): Configuration updates to apply.
            
        Returns:
            context manager: Manages temporary config changes.
        """
        class ConfigMocker:
            def __init__(self, updates):
                self.updates = updates or {}
                self.original_values = {}
                
            def __enter__(self):
                # Store original values and apply updates
                for key, value in self.updates.items():
                    if key in current_app.config:
                        self.original_values[key] = current_app.config[key]
                    current_app.config[key] = value
                return current_app.config
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                # Restore original values
                for key, value in self.updates.items():
                    if key in self.original_values:
                        current_app.config[key] = self.original_values[key]
                    else:
                        current_app.config.pop(key, None)
        
        return ConfigMocker(config_updates)
    
    return _mock_config