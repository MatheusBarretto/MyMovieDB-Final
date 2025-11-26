---
inclusion: always
---

# MyMovieDB Coding Conventions

## Flask Application Architecture

### Service Layer Pattern

- Business logic belongs in service classes (`app/services/`)
- Services handle complex operations, external API calls, and data processing
- Keep route handlers thin - delegate to services for business logic
- Models should focus on data representation and basic queries

### Blueprint Organization

- Group related routes into feature-based blueprints
- Register blueprints in `app/__init__.py` with appropriate URL prefixes
- Use consistent naming: `auth_bp`, `movie_bp`, etc.

### Configuration Management

- Use JSON configuration files in `instance/` directory
- Support environment variable overrides
- Never commit sensitive configuration to version control
- Use encrypted storage for secrets (`.env.crypto`)

## Code Style & Formatting

### Python Standards

- Follow **PEP 8** style guide strictly
- Use 4 spaces for indentation (no tabs)
- Line length limit: 79 characters
- Use type hints for all function parameters and return values
- Import order: standard library, third-party, local imports
- SHOULD use pathlib methods instead of os ones

### Naming Conventions

- **Modules/Functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: `_leading_underscore`
- **Database tables**: `snake_case` (plural nouns)

### Database access

- Anything greater than a simple select should be performed by a service in the service layer
- Basic access SHOULD be performed by methods in the BasicRepositoryMixin class
- Methods in the BasicRepositoryMixin SHOULD be used with the raise_if_not_found argument as True (use try/except for record not found)


## Flask-Specific Patterns

### Route Handlers

```python
@bp.route('/movies/<int:movie_id>')
@login_required
def movie_detail(movie_id: int) -> str:
    """Display movie details page."""
    movie = movie_service.get_movie_by_id(movie_id)
    if not movie:
        abort(404)
    return render_template('movies/detail.jinja2', movie=movie)
```

### Form Handling

- Use Flask-WTF for all forms
- Validate forms in route handlers before processing
- Handle CSRF protection automatically via Flask-WTF
- Place form classes in `app/forms/`

### Database Models

- Use SQLAlchemy declarative base
- Include `__repr__` methods for debugging
- Use mixins for common functionality (timestamps, etc.)
- Define relationships with proper lazy loading

## Security Best Practices

### Authentication & Authorization

- Always use `@login_required` decorator for protected routes
- Validate user permissions before sensitive operations
- Use JWT tokens for API authentication
- Implement proper session management

### Data Validation

- Validate all user input at multiple layers (form, service, model)
- Sanitize data before database operations
- Use parameterized queries (SQLAlchemy handles this)
- Validate file uploads (type, size, content)

### Sensitive Data

- Never log sensitive information (passwords, tokens, etc.)
- Use Fernet encryption for sensitive stored data
- Hash passwords with Werkzeug's security utilities
- Implement proper 2FA/TOTP handling

## Database Patterns

### Model Design

```python
class Movie(db.Model, TimestampMixin):
    """Movie model with TMDB integration."""

    __tablename__ = 'movies'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tmdb_id = db.Column(db.Integer, unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)

    def __repr__(self) -> str:
        return f'<Movie {self.title}>'
```

### Migration Guidelines

- Always create migrations for schema changes
- Use descriptive migration messages
- Test migrations on development data before production
- Never edit existing migrations - create new ones

## Testing Standards

### Test Organization

- Place tests in `tests/` directory
- Use `test_*.py` naming convention
- Group tests by feature area
- Use pytest fixtures for common setup

### Test Coverage

- Aim for high test coverage on business logic
- Test edge cases and error conditions
- Mock external API calls (TMDB, email services)
- Test authentication and authorization flows

### Test Structure

```python
def test_movie_service_get_by_id(app, db_session):
    """Test movie retrieval by ID."""
    # Arrange
    movie = create_test_movie()
    db_session.add(movie)
    db_session.commit()

    # Act
    result = movie_service.get_movie_by_id(movie.id)

    # Assert
    assert result is not None
    assert result.title == movie.title
```

## Error Handling

### Exception Management

- Use specific exception types, not generic `Exception`
- Log errors with appropriate context
- Return user-friendly error messages
- Handle external API failures gracefully

### Logging

- Use Flask's app logger for application events
- Log at appropriate levels (DEBUG, INFO, WARNING, ERROR)
- Include request context in error logs
- Never log sensitive information

## External API Integration

### TMDB API

- Use service layer for all TMDB interactions
- Implement proper rate limiting and retry logic
- Cache frequently accessed data
- Handle API errors gracefully

### Email Services

- Abstract email providers behind service interface
- Support multiple providers (Postmark, SMTP, Mock)
- Queue email sending for better performance
- Handle delivery failures appropriately

## Performance Considerations

### Database Optimization

- Use appropriate indexes on frequently queried columns
- Implement pagination for large result sets
- Use eager loading for related data when needed
- Monitor query performance and optimize N+1 problems

### Caching Strategy

- Cache expensive operations (external API calls)
- Use appropriate cache invalidation strategies
- Consider Redis for production caching needs

## Documentation Standards

- All comments and docstring MUST be in pt-BR

### Docstrings

- Use Google-style docstrings for consistency
- Document all public methods and classes
- Include parameter types and return types
- Provide usage examples for complex functions

### Code Comments

- Explain "why" not "what" in comments
- Document business logic decisions
- Mark TODO items with clear descriptions
- Keep comments up-to-date with code changes
