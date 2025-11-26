---
inclusion: always
---

# Service Layer Pattern

## Database Service Template

All services that perform database operations MUST follow this standardized pattern:

```python
from sqlalchemy.exc import SQLAlchemyError
from app.infra.database import db

class <ServiceName>Error(Exception):
    """Custom exception for <ServiceName> operations."""
    pass

class <ServiceName>Service:
    """Service class for <entity> operations."""

    _default_session = db.session

    @classmethod
    def set_default_session(cls, session):
        """Set the default session to be used by the service.

        Args:
            session: SQLAlchemy session to be used as default
        """
        cls._default_session = session

    @classmethod
    def method_name(cls, session=None, auto_commit: bool = True):
        """Method description.

        Args:
            session: Optional SQLAlchemy session
            auto_commit: Whether to auto-commit the transaction

        Returns:
            Description of return value

        Raises:
            <ServiceName>Error: When operation fails
        """
        if session is None:
            session = cls._default_session

        try:
            # Perform database operations here
            result = None  # Replace with actual operations

            if auto_commit:
                session.commit()

            return result

        except SQLAlchemyError as e:
            session.rollback()
            raise <ServiceName>Error(f"Database error in {cls.__name__}.method_name: {str(e)}") from e
        except Exception as e:
            session.rollback()
            raise <ServiceName>Error(f"Unexpected error in {cls.__name__}.method_name: {str(e)}") from e
```

## Service Layer Rules

### Mandatory Patterns

- **Custom Exceptions**: Each service MUST define its own exception class
- **Session Management**: Use the session parameter pattern for testability
- **Error Handling**: Always wrap database operations in try/catch blocks
- **Transaction Control**: Support auto_commit parameter for transaction flexibility

### Naming Conventions

- Service classes: `<EntityName>Service` (e.g., `PessoaService`, `MovieService`)
- Exception classes: `<EntityName>Error` (e.g., `PessoaError`, `MovieError`)
- Method names: Use descriptive verbs (`create_`, `get_`, `update_`, `delete_`)

### Error Handling Requirements

- Always rollback on exceptions
- Provide meaningful error messages with context
- Chain exceptions using `from e` to preserve stack traces
- Distinguish between SQLAlchemy errors and general exceptions

### Testing Support

- Use `set_default_session()` in tests to inject test sessions
- Support dependency injection through session parameter
- Enable transaction control via `auto_commit` parameter
