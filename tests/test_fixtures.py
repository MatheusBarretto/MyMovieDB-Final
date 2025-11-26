"""
Test to verify fixtures and test helpers are working correctly.
"""
import pytest
from tests.utils.test_helpers import MockField, MockForm, create_password_field


def test_app_fixture(app):
    """Test that the app fixture provides a Flask app."""
    assert app is not None
    assert app.config['TESTING'] is True


def test_app_context_fixture(app_context):
    """Test that the app_context fixture provides Flask context."""
    from flask import current_app
    assert current_app is not None
    assert current_app.config['TESTING'] is True


def test_mock_field():
    """Test MockField helper class."""
    field = MockField("test_data")
    assert field.data == "test_data"
    assert field.name == "mock_field"
    assert field.errors == []


def test_mock_form():
    """Test MockForm helper class."""
    form = MockForm(password="test123")
    assert hasattr(form, 'password')
    assert form.password.data == "test123"


def test_create_password_field():
    """Test password field factory function."""
    field = create_password_field("mypassword")
    assert field.data == "mypassword"
    assert field.name == "password"


def test_password_config_fixture(password_config):
    """Test password configuration fixture."""
    assert 'default' in password_config
    assert 'minimal' in password_config
    assert password_config['default']['PASSWORD_MIN'] == 8


def test_mock_config_fixture(mock_config, app_context):
    """Test configuration mocking fixture."""
    from flask import current_app
    
    original_value = current_app.config.get('PASSWORD_MIN')
    
    with mock_config({'PASSWORD_MIN': 999}):
        assert current_app.config['PASSWORD_MIN'] == 999
    
    # Should be restored
    assert current_app.config.get('PASSWORD_MIN') == original_value