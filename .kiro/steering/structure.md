# Project Structure & Organization

## Root Directory Structure

```
├── app/                    # Main Flask application package
├── instance/              # Instance-specific configuration and data
├── migrations/            # Database migration files (Alembic)
├── seeder/               # Data seeding scripts and utilities
├── tests/                # Test suite
├── flask_app.py          # Application entry point
├── requirements.txt      # Python dependencies
└── requirements.in       # Dependency source file
```

## Application Package (`app/`)

```
app/
├── __init__.py           # Application factory and configuration
├── cli/                  # Custom Flask CLI commands
├── forms/                # WTForms form definitions
├── infra/                # Infrastructure modules (db, login, etc.)
├── models/               # SQLAlchemy model definitions
├── routes/               # Blueprint route handlers
├── services/             # Business logic and service layer
├── static/               # Static assets (CSS, JS, images)
└── templates/            # Jinja2 templates
```

## Key Architectural Patterns

### Blueprint Organization
- Routes are organized by feature area in separate blueprints
- Each blueprint handles related functionality (auth, movies, etc.)
- Blueprint registration happens in `app/__init__.py`

### Service Layer Pattern
- Business logic separated into service classes
- Services handle complex operations and external API calls
- Models focus on data representation and basic queries

### Configuration Management
- JSON-based configuration files in `instance/` directory
- Environment variable overrides supported
- Sensitive data encrypted and stored separately

### Database Models
- Located in `app/models/` with logical grouping
- Mixins for common functionality
- Custom types for specialized data handling

## Instance Directory (`instance/`)
- `config.dev.json`: Development configuration
- `.env.crypto`: Encrypted environment variables
- `*.db`: SQLite database files
- Configuration files are instance-specific and not committed

## Seeder System (`seeder/`)
- Complete data import system for TMDB integration
- Modular scripts for fetching, processing, and importing data
- Support for AI-generated content (descriptions, biographies)
- Organized output structure for processed data

## Testing Structure (`tests/`)
- `conftest.py`: Pytest configuration and fixtures
- Test files follow `test_*.py` naming convention
- Separate test requirements in `requirements-test.txt`
- Coverage reporting configured

## File Naming Conventions

### Python Files
- Snake_case for modules and functions
- PascalCase for classes
- Descriptive names reflecting functionality

### Templates
- `.jinja2` extension for Jinja templates
- Organized by feature area
- Base templates for common layouts

### Static Assets
- Organized by type (css/, js/, images/)
- Versioning handled by Flask's static file serving

## Import Patterns
- Relative imports within the app package
- Absolute imports for external dependencies
- Circular import prevention through careful module organization

## Security Considerations
- Sensitive configuration never committed to version control
- Encryption keys managed through dedicated CLI commands
- User uploads handled with proper validation and storage