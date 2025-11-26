# Design Document

## Overview

This design implements complete CRUD operations for the Pessoa class following the established MyMovieDB architecture patterns. The solution leverages existing infrastructure including the service layer pattern, Flask-WTF forms, Bootstrap 5 UI components, and the current authentication system. The design maintains consistency with existing features while providing comprehensive person management functionality.

## Architecture

### Component Structure

```
app/
├── routes/pessoas/
│   ├── __init__.py (existing - extend with CRUD routes)
│   └── templates/pessoa/web/
│       ├── details.jinja2 (existing)
│       ├── list.jinja2 (new)
│       ├── create.jinja2 (new)
│       ├── edit.jinja2 (new)
│       └── _form.jinja2 (new - shared form template)
├── forms/pessoas/
│   └── __init__.py (new - PessoaForm)
├── services/
│   └── pessoa_service.py (existing - extend with CRUD methods)
└── models/
    └── pessoa.py (existing - no changes needed)
```

### Request Flow

1. **Public Access**: List and detail views accessible without authentication
2. **Authenticated Access**: Create, edit, delete operations require login
3. **Form Processing**: Flask-WTF handles validation and CSRF protection
4. **Service Layer**: Business logic centralized in PessoaService
5. **Database Operations**: Leverages existing BasicRepositoryMixin methods

## Components and Interfaces

### Route Handlers (app/routes/pessoas/__init__.py)

**New Routes to Add:**

```python
# Public routes
@pessoa_bp.route('/', methods=['GET'])
def pessoa_list()
    # Paginated listing with search functionality

# Authenticated routes  
@pessoa_bp.route('/create', methods=['GET', 'POST'])
@login_required
def pessoa_create()
    # Create new person form and processing

@pessoa_bp.route('/<uuid:pessoa_id>/edit', methods=['GET', 'POST'])
@login_required  
def pessoa_edit(pessoa_id)
    # Edit existing person form and processing

@pessoa_bp.route('/<uuid:pessoa_id>/delete', methods=['POST'])
@login_required
def pessoa_delete(pessoa_id)
    # Delete person with confirmation
```

### Form Definition (app/forms/pessoas/__init__.py)

```python
class PessoaForm(FlaskForm):
    """Form for creating and editing person records."""
    
    nome = StringField(
        label="Nome",
        validators=[InputRequired(), Length(max=100)]
    )
    
    data_nascimento = DateField(
        label="Data de Nascimento",
        validators=[Optional()]
    )
    
    data_falecimento = DateField(
        label="Data de Falecimento", 
        validators=[Optional()]
    )
    
    local_nascimento = StringField(
        label="Local de Nascimento",
        validators=[Optional(), Length(max=100)]
    )
    
    biografia = TextAreaField(
        label="Biografia",
        validators=[Optional()]
    )
    
    foto = FileField(
        label="Foto",
        validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png'])]
    )
    
    submit = SubmitField("Salvar")
```

### Service Layer Extensions (app/services/pessoa_service.py)

**New Methods to Add:**

```python
@classmethod
def listar_pessoas(cls, page=1, per_page=20, search=None, session=None):
    """List persons with pagination and search."""
    
@classmethod  
def criar_pessoa(cls, form_data, session=None):
    """Create new person from form data."""
    
@classmethod
def atualizar_pessoa(cls, pessoa, form_data, session=None):
    """Update existing person from form data."""
    
@classmethod
def deletar_pessoa(cls, pessoa, session=None):
    """Delete person and handle relationships."""
    
@classmethod
def validar_pessoa_unica(cls, nome, data_nascimento, pessoa_id=None, session=None):
    """Validate person uniqueness by name and birth date."""
```

## Data Models

### Existing Pessoa Model
The current Pessoa model already provides all necessary fields and functionality:

- **Primary Fields**: id, nome, data_nascimento, data_falecimento, local_nascimento, biografia
- **Photo Management**: foto_base64, foto_mime, com_foto with property-based access
- **Relationships**: ator (one-to-one), funcoes_tecnicas (one-to-many)
- **Mixins**: BasicRepositoryMixin (CRUD operations), AuditMixin (timestamps)

### Form Validation Rules

1. **Nome**: Required, max 100 characters
2. **Dates**: Optional, proper date format, logical validation (death after birth)
3. **Local**: Optional, max 100 characters  
4. **Biografia**: Optional, unlimited text
5. **Foto**: Optional, image files only (jpg, jpeg, png)
6. **Uniqueness**: Combination of nome + data_nascimento must be unique

## User Interface Design

### List Page (pessoa/web/list.jinja2)
- **Layout**: Bootstrap card-based grid layout
- **Features**: Pagination, search bar, person thumbnails
- **Actions**: View details (public), Create/Edit/Delete buttons (authenticated)
- **Search**: Real-time filtering by person name

### Create/Edit Pages (pessoa/web/create.jinja2, edit.jinja2)
- **Layout**: Centered form with Bootstrap styling
- **Form**: Shared template (_form.jinja2) for consistency
- **Validation**: Client-side and server-side validation
- **Photo Upload**: Drag-and-drop with preview functionality

### Shared Form Template (_form.jinja2)
- **Fields**: All person attributes with proper Bootstrap styling
- **Validation**: Error message display for each field
- **Photo Handling**: Current photo display (edit mode) and upload interface

## Error Handling

### Validation Errors
- **Form Validation**: Flask-WTF provides field-level validation
- **Business Rules**: Service layer validates uniqueness and date logic
- **Image Processing**: ImageProcessingService handles photo validation

### Database Errors
- **Constraint Violations**: Handled gracefully with user-friendly messages
- **Relationship Conflicts**: Cascade deletion warnings for related data
- **Transaction Management**: Proper rollback on errors

### HTTP Error Responses
- **404**: Person not found (invalid UUID)
- **403**: Unauthorized access to protected operations
- **400**: Invalid form data or validation errors

## Security Considerations

### Authentication & Authorization
- **Public Access**: List and detail views available to all users
- **Protected Operations**: Create, edit, delete require @login_required
- **CSRF Protection**: Flask-WTF automatically handles CSRF tokens

### Data Validation
- **Input Sanitization**: WTForms validators prevent malicious input
- **File Upload Security**: FileAllowed validator restricts file types
- **Image Processing**: ImageProcessingService handles secure image processing

### Audit Trail
- **Change Tracking**: AuditMixin automatically tracks creation and modification

## Testing Strategy

### Unit Tests
- **Service Methods**: Test all CRUD operations in PessoaService
- **Form Validation**: Test all validation rules and edge cases
- **Model Properties**: Test foto property and age calculation

### Integration Tests  
- **Route Handlers**: Test complete request/response cycles
- **Authentication**: Test access control for protected routes
- **Database Operations**: Test cascade deletions and relationships

### UI Tests
- **Form Submission**: Test create and edit workflows
- **Search Functionality**: Test filtering and pagination
- **Error Handling**: Test validation error display

## Performance Considerations

### Database Optimization
- **Pagination**: Limit query results for large datasets
- **Indexing**: Ensure proper indexes on nome and data_nascimento
- **Eager Loading**: Load relationships efficiently when needed

### Image Handling
- **Photo Storage**: Base64 encoding for simplicity (existing pattern)
- **Thumbnail Generation**: Consider caching for list views
- **Upload Limits**: Reasonable file size restrictions

### Caching Strategy
- **Static Data**: Cache person lists for anonymous users
- **Image Serving**: HTTP caching headers for photos
- **Search Results**: Consider caching frequent searches

## Implementation Notes

### Existing Code Integration
- **Extend Routes**: Add new routes to existing pessoa_bp blueprint
- **Service Extension**: Add methods to existing PessoaService class
- **Template Consistency**: Follow existing Bootstrap 5 patterns

### Migration Considerations
- **No Schema Changes**: Existing Pessoa model supports all requirements
- **Data Integrity**: Existing data remains unchanged
- **Backward Compatibility**: Existing routes and functionality preserved

### Development Approach
- **Incremental Implementation**: Build and test each CRUD operation separately
- **Template Reuse**: Maximize shared components between create/edit forms
- **Service-First**: Implement service methods before route handlers