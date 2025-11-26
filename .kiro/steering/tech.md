# Technology Stack & Build System

## Backend Framework
- **Flask 3.1.2**: Main web framework
- **SQLAlchemy**: ORM with Flask-SQLAlchemy integration
- **Flask-Migrate**: Database migrations using Alembic
- **Flask-Login**: User session management
- **Flask-WTF**: Form handling and CSRF protection

## Security & Authentication
- **PyJWT**: JWT token generation and validation
- **PyOTP**: TOTP/2FA implementation
- **Cryptography (Fernet)**: Sensitive data encryption
- **Werkzeug**: Password hashing
- **QRCode**: 2FA QR code generation

## Frontend & UI
- **Bootstrap 5**: UI framework via Bootstrap-Flask
- **Cropper.js**: Image cropping (via CDN)
- **Jinja2**: Template engine

## Database
- **SQLite**: Development database
- **PostgreSQL**: Production database (configurable)

## Email Services
- **Postmark API**: Production email service
- **SMTP**: Generic email support (Gmail, etc.)
- **Mock provider**: Development/testing

## Image Processing
- **Pillow (PIL)**: Image manipulation and processing
- **Pydenticon**: Automatic identicon generation

## External APIs
- **TMDB API**: Movie database integration
- **OpenAI API**: AI-generated descriptions (optional)
- **Perplexity AI**: Biography generation (optional)

## Development Tools
- **pip-tools**: Dependency management
- **pytest**: Testing framework with coverage
- **python-dotenv**: Environment variable management

## Common Commands

### Environment Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\activate.ps1

# Activate (Linux/macOS)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Database Management
```bash
# Set Flask app
set FLASK_APP=flask_app.py  # Windows
export FLASK_APP=flask_app.py  # Linux/macOS

# Initialize migrations (first time only)
flask db init

# Create migration
flask db migrate -m "Description"

# Apply migrations
flask db upgrade
```

### Running the Application
```bash
# Development server
flask run

# With custom config
python flask_app.py --config config.prod.json

# Generate encryption keys
flask secrets generate
```

### Testing
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

### Data Seeding
```bash
# Complete seeding process
cd seeder
python fetch_data.py --fetch-persons --language pt-BR
python process_data.py
cd ..
python -m seeder.seed_data_into_app

# Generate AI descriptions (optional)
cd seeder
python seed_all_descriptions.py
python seed_biografias.py
```

## Configuration
- JSON-based configuration in `instance/config.dev.json`
- Environment variable overrides supported
- Encrypted secrets via `.env.crypto` file
- See CONFIG.md for complete configuration reference