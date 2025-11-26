"""
Test helper utilities for WTForms validator testing.

This module provides mock objects and utility functions for testing
WTForms validators without requiring actual form instances.
"""

from typing import Any, Optional


class MockField:
    """Mock WTForms field with configurable data property.
    
    Simulates a WTForms field object for testing validators
    without requiring actual form setup.
    
    Attributes:
        data: The field's data value that validators will check.
        name: Optional field name for error reporting.
    """
    
    def __init__(self, data: Any, name: Optional[str] = None):
        """Initialize mock field with data.
        
        Args:
            data: The data value for the field.
            name: Optional field name for identification.
        """
        self.data = data
        self.name = name or 'mock_field'
        self.errors = []
        
    def __repr__(self):
        """String representation of the mock field."""
        return f"MockField(data={self.data!r}, name={self.name!r})"
    
    def __str__(self):
        """String representation of field data."""
        return str(self.data) if self.data is not None else ''


class MockForm:
    """Mock WTForms form for simulating form objects.
    
    Provides a minimal form-like object that can be used
    with validators that expect a form parameter.
    
    Attributes:
        reference_obj: Optional reference object for validators like CampoImutavel.
        fields: Dictionary of field names to MockField instances.
    """
    
    def __init__(self, reference_obj: Optional[Any] = None, **fields):
        """Initialize mock form.
        
        Args:
            reference_obj: Optional reference object for validation.
            **fields: Field data as keyword arguments.
        """
        self.reference_obj = reference_obj
        self.fields = {}
        self.errors = {}
        
        # Create MockField instances for provided field data
        for field_name, field_data in fields.items():
            if isinstance(field_data, MockField):
                self.fields[field_name] = field_data
            else:
                self.fields[field_name] = MockField(field_data, field_name)
    
    def __getattr__(self, name):
        """Allow access to fields as attributes."""
        if name in self.fields:
            return self.fields[name]
        raise AttributeError(f"MockForm has no field '{name}'")
    
    def add_field(self, name: str, data: Any = None) -> MockField:
        """Add a field to the mock form.
        
        Args:
            name: Name of the field.
            data: Data value for the field.
            
        Returns:
            The created MockField instance.
        """
        field = MockField(data, name)
        self.fields[name] = field
        setattr(self, name, field)
        return field
    
    def __repr__(self):
        """String representation of the mock form."""
        field_names = list(self.fields.keys())
        return f"MockForm(fields={field_names}, reference_obj={self.reference_obj})"


def create_password_field(password_data: str, field_name: str = 'password') -> MockField:
    """Factory function for creating password field mocks.
    
    Creates a MockField instance specifically configured for
    password validation testing.
    
    Args:
        password_data: The password string to test.
        field_name: Name of the password field (default: 'password').
        
    Returns:
        MockField: Configured mock field for password testing.
    """
    return MockField(data=password_data, name=field_name)


def create_email_field(email_data: str, field_name: str = 'email') -> MockField:
    """Factory function for creating email field mocks.
    
    Creates a MockField instance specifically configured for
    email validation testing.
    
    Args:
        email_data: The email string to test.
        field_name: Name of the email field (default: 'email').
        
    Returns:
        MockField: Configured mock field for email testing.
    """
    return MockField(data=email_data, name=field_name)


def create_form_with_password(password: str, reference_obj: Optional[Any] = None) -> MockForm:
    """Create a mock form with a password field.
    
    Convenience function for creating forms with password fields
    for validator testing.
    
    Args:
        password: Password data for the field.
        reference_obj: Optional reference object for the form.
        
    Returns:
        MockForm: Form with password field configured.
    """
    return MockForm(
        reference_obj=reference_obj,
        password=create_password_field(password)
    )


def create_form_with_email(email: str, reference_obj: Optional[Any] = None) -> MockForm:
    """Create a mock form with an email field.
    
    Convenience function for creating forms with email fields
    for validator testing.
    
    Args:
        email: Email data for the field.
        reference_obj: Optional reference object for the form.
        
    Returns:
        MockForm: Form with email field configured.
    """
    return MockForm(
        reference_obj=reference_obj,
        email=create_email_field(email)
    )


def create_mock_user(user_id: str = "test-id", email: str = "test@example.com") -> object:
    """Create a mock user object for testing immutable field validators.
    
    Args:
        user_id: ID for the mock user.
        email: Email for the mock user.
        
    Returns:
        Mock user object with id and email attributes.
    """
    class MockUser:
        def __init__(self, user_id: str, email: str):
            self.id = user_id
            self.email = email
            
    return MockUser(user_id, email)


class ValidationTestHelper:
    """Helper class for common validation testing patterns.
    
    Provides utility methods for testing validator behavior
    and assertion patterns.
    """
    
    @staticmethod
    def assert_validation_passes(validator, form, field):
        """Assert that validation passes without raising ValidationError.
        
        Args:
            validator: The validator instance to test.
            form: Mock form object.
            field: Mock field object.
            
        Raises:
            AssertionError: If validation raises ValidationError unexpectedly.
        """
        try:
            validator(form, field)
        except Exception as e:
            raise AssertionError(f"Expected validation to pass, but got: {e}")
    
    @staticmethod
    def assert_validation_fails(validator, form, field, expected_message=None):
        """Assert that validation fails with ValidationError.
        
        Args:
            validator: The validator instance to test.
            form: Mock form object.
            field: Mock field object.
            expected_message: Optional expected error message substring.
            
        Returns:
            str: The actual validation error message.
            
        Raises:
            AssertionError: If validation doesn't raise ValidationError or
                          message doesn't match expected.
        """
        from wtforms import ValidationError
        
        try:
            validator(form, field)
            raise AssertionError("Expected ValidationError to be raised, but validation passed")
        except ValidationError as e:
            error_message = str(e)
            if expected_message and expected_message not in error_message:
                raise AssertionError(
                    f"Expected error message to contain '{expected_message}', "
                    f"but got: '{error_message}'"
                )
            return error_message
        except Exception as e:
            raise AssertionError(f"Expected ValidationError, but got {type(e).__name__}: {e}")


class ValidationTestCase:
    """Helper class for organizing validation test cases."""
    
    def __init__(self, 
                 password: str, 
                 config: dict, 
                 should_pass: bool, 
                 expected_message: Optional[str] = None,
                 description: str = ""):
        """Initialize a validation test case.
        
        Args:
            password: Password to test.
            config: Configuration dictionary for the test.
            should_pass: Whether validation should pass.
            expected_message: Expected error message if validation fails.
            description: Description of the test case.
        """
        self.password = password
        self.config = config
        self.should_pass = should_pass
        self.expected_message = expected_message
        self.description = description
        
    def __repr__(self):
        return f"ValidationTestCase(password='{self.password}', should_pass={self.should_pass}, desc='{self.description}')"


def get_password_test_cases():
    """Get comprehensive password validation test cases.
    
    Returns:
        List of ValidationTestCase instances covering various scenarios.
    """
    return [
        # Valid passwords
        ValidationTestCase(
            password="ValidPass123!",
            config={'PASSWORD_MIN': 8, 'PASSWORD_MAIUSCULA': True, 'PASSWORD_MINUSCULA': True, 'PASSWORD_NUMERO': True, 'PASSWORD_SIMBOLO': True},
            should_pass=True,
            description="Valid password meeting all requirements"
        ),
        ValidationTestCase(
            password="simple",
            config={'PASSWORD_MIN': 0, 'PASSWORD_MAIUSCULA': False, 'PASSWORD_MINUSCULA': False, 'PASSWORD_NUMERO': False, 'PASSWORD_SIMBOLO': False},
            should_pass=True,
            description="Simple password with no requirements"
        ),
        
        # Length failures
        ValidationTestCase(
            password="short",
            config={'PASSWORD_MIN': 8, 'PASSWORD_MAIUSCULA': False, 'PASSWORD_MINUSCULA': False, 'PASSWORD_NUMERO': False, 'PASSWORD_SIMBOLO': False},
            should_pass=False,
            expected_message="pelo menos 8 caracteres",
            description="Password too short"
        ),
        ValidationTestCase(
            password="exactly8",
            config={'PASSWORD_MIN': 8, 'PASSWORD_MAIUSCULA': False, 'PASSWORD_MINUSCULA': False, 'PASSWORD_NUMERO': False, 'PASSWORD_SIMBOLO': False},
            should_pass=True,
            description="Password exactly minimum length"
        ),
        
        # Character type failures
        ValidationTestCase(
            password="nouppercase123!",
            config={'PASSWORD_MIN': 0, 'PASSWORD_MAIUSCULA': True, 'PASSWORD_MINUSCULA': False, 'PASSWORD_NUMERO': False, 'PASSWORD_SIMBOLO': False},
            should_pass=False,
            expected_message="letras maiúsculas",
            description="Missing uppercase letters"
        ),
        ValidationTestCase(
            password="NOLOWERCASE123!",
            config={'PASSWORD_MIN': 0, 'PASSWORD_MAIUSCULA': False, 'PASSWORD_MINUSCULA': True, 'PASSWORD_NUMERO': False, 'PASSWORD_SIMBOLO': False},
            should_pass=False,
            expected_message="letras minúsculas",
            description="Missing lowercase letters"
        ),
        ValidationTestCase(
            password="NoNumbers!",
            config={'PASSWORD_MIN': 0, 'PASSWORD_MAIUSCULA': False, 'PASSWORD_MINUSCULA': False, 'PASSWORD_NUMERO': True, 'PASSWORD_SIMBOLO': False},
            should_pass=False,
            expected_message="números",
            description="Missing numbers"
        ),
        ValidationTestCase(
            password="NoSymbols123",
            config={'PASSWORD_MIN': 0, 'PASSWORD_MAIUSCULA': False, 'PASSWORD_MINUSCULA': False, 'PASSWORD_NUMERO': False, 'PASSWORD_SIMBOLO': True},
            should_pass=False,
            expected_message="símbolos especiais",
            description="Missing special symbols"
        ),
        
        # Multiple violations
        ValidationTestCase(
            password="bad",
            config={'PASSWORD_MIN': 8, 'PASSWORD_MAIUSCULA': True, 'PASSWORD_MINUSCULA': True, 'PASSWORD_NUMERO': True, 'PASSWORD_SIMBOLO': True},
            should_pass=False,
            expected_message="pelo menos 8 caracteres e letras maiúsculas, letras minúsculas, números e símbolos especiais",
            description="Multiple requirement violations"
        ),
    ]


def get_config_test_scenarios():
    """Get configuration test scenarios for different password policies.
    
    Returns:
        List of configuration dictionaries for testing different scenarios.
    """
    return [
        {'PASSWORD_MIN': 8, 'PASSWORD_MAIUSCULA': True, 'PASSWORD_MINUSCULA': False, 'PASSWORD_NUMERO': False, 'PASSWORD_SIMBOLO': False},
        {'PASSWORD_MIN': 0, 'PASSWORD_MAIUSCULA': False, 'PASSWORD_MINUSCULA': True, 'PASSWORD_NUMERO': True, 'PASSWORD_SIMBOLO': False},
        {'PASSWORD_MIN': 6, 'PASSWORD_MAIUSCULA': False, 'PASSWORD_MINUSCULA': False, 'PASSWORD_NUMERO': False, 'PASSWORD_SIMBOLO': True},
        {'PASSWORD_MIN': 10, 'PASSWORD_MAIUSCULA': True, 'PASSWORD_MINUSCULA': True, 'PASSWORD_NUMERO': True, 'PASSWORD_SIMBOLO': True},
        {'PASSWORD_MIN': 0, 'PASSWORD_MAIUSCULA': False, 'PASSWORD_MINUSCULA': False, 'PASSWORD_NUMERO': False, 'PASSWORD_SIMBOLO': False},
    ]