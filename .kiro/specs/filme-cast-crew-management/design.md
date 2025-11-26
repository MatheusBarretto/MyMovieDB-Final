# Design Document

## Overview

The cast and crew management feature extends the existing movie detail view with interactive management capabilities for authenticated users. The design leverages existing infrastructure including the person autocomplete API, modal components, and service layer patterns while maintaining the current user experience for public users.

## Architecture

### Component Integration
- **Frontend**: Bootstrap 5 modals with JavaScript for dynamic interactions and apropriated fallback for non-JavaScript users
- **Backend**: New Flask routes integrated into the existing filme blueprint
- **API**: Utilizes existing `/api/pessoas/search` endpoint for person autocomplete
- **Database**: Leverages existing Atuacao and EquipeTecnica junction tables
- **Services**: New ElencoEquipeService following established service layer patterns

### User Experience Flow
1. **Public View**: Standard movie detail display without management controls
2. **Authenticated View**: Enhanced with "Adicionar" buttons and management controls
3. **Modal Interactions**: Add/edit operations through responsive modal dialogs
4. **Real-time Updates**: Page refresh after successful operations to show changes

## Components and Interfaces

### Backend Routes (app/routes/filmes/)

#### New Route Endpoints
```python
# Cast Management
POST /filme/<uuid:filme_id>/elenco/adicionar
POST /filme/<uuid:filme_id>/elenco/<uuid:atuacao_id>/editar  
POST /filme/<uuid:filme_id>/elenco/<uuid:atuacao_id>/remover

# Crew Management  
POST /filme/<uuid:filme_id>/equipe-tecnica/adicionar
POST /filme/<uuid:filme_id>/equipe-tecnica/<uuid:equipe_id>/editar
POST /filme/<uuid:filme_id>/equipe-tecnica/<uuid:equipe_id>/remover
```

#### Route Handler Pattern
- Validate user authentication via `@login_required`
- Validate movie existence and return 404 if not found
- Process form data and delegate business logic to CastCrewService
- Handle success/error responses with appropriate flash messages
- Redirect back to movie detail view

### Service Layer (app/services/elencoequipe_service.py)

#### ElencoEquipeService Class
Following the established service pattern with session management and error handling:

```python
class ElencoEquipeService:
    """Service for managing movie cast and crew relationships."""
    
    @classmethod
    def adicionar_elenco(cls, filme_id, pessoa_id, personagem, session=None, auto_commit=True)
    
    @classmethod  
    def editar_elenco(cls, atuacao_id, pessoa_id, personagem, session=None, auto_commit=True)
    
    @classmethod
    def remover_elenco(cls, atuacao_id, session=None, auto_commit=True)
    
    @classmethod
    def adicionar_equipe_tecnica(cls, filme_id, pessoa_id, funcao_tecnica_id, session=None, auto_commit=True)
    
    @classmethod
    def editar_equipe_tecnica(cls, equipe_id, pessoa_id, funcao_tecnica_id, session=None, auto_commit=True)
    
    @classmethod
    def remover_equipe_tecnica(cls, equipe_id, session=None, auto_commit=True)
```

#### Service Responsibilities
- Validate business rules (uniqueness constraints, required fields)
- Handle database operations with proper transaction management
- Return structured operation results with success/error status
- Provide detailed error messages for validation failures

### Frontend Components

#### Template Modifications (details.jinja2)
- **Conditional Rendering**: Show management buttons only for authenticated users
- **Modal Integration**: Include modal templates for add/edit operations
- **JavaScript Enhancement**: Handle form submissions and autocomplete interactions

#### Modal Templates
- **Add Cast Modal**: Person autocomplete + character name input
- **Edit Cast Modal**: Pre-populated person autocomplete + character name input  
- **Add Crew Modal**: Person autocomplete + technical role dropdown
- **Edit Crew Modal**: Pre-populated person autocomplete + technical role dropdown
- **Confirmation Modals**: Simple confirmation dialogs for removal operations

#### JavaScript Functionality
- **Autocomplete Integration**: Connect to existing `/api/pessoas/search` endpoint
- **Form Validation**: Client-side validation before submission
- **Modal Management**: Show/hide modals and handle form state
- **Dynamic Updates**: Update UI elements based on user interactions

### Form Classes (app/forms/)

#### New Form Classes
```python
class AdicionarElencoForm(FlaskForm):
    pessoa_id = HiddenField(validators=[DataRequired(), UUID()])
    personagem = StringField(validators=[DataRequired(), Length(max=100)])
    
class EditarElencoForm(FlaskForm):
    pessoa_id = HiddenField(validators=[DataRequired(), UUID()])
    personagem = StringField(validators=[DataRequired(), Length(max=100)])
    
class AdicionarEquipeTecnicaForm(FlaskForm):
    pessoa_id = HiddenField(validators=[DataRequired(), UUID()])
    funcao_tecnica_id = SelectField(validators=[DataRequired()], coerce=str)
    
class EditarEquipeTecnicaForm(FlaskForm):
    pessoa_id = HiddenField(validators=[DataRequired(), UUID()])
    funcao_tecnica_id = SelectField(validators=[DataRequired()], coerce=str)
```

## Data Models

### Existing Model Utilization
The design leverages existing database models without modifications:

- **Atuacao**: Junction table linking Filme, Ator, and character information
- **EquipeTecnica**: Junction table linking Filme, Pessoa, and FuncaoTecnica
- **Pessoa/Ator**: Person entities with autocomplete search capability
- **FuncaoTecnica**: Technical roles for crew member assignments

### Data Validation Rules
- **Uniqueness**: Prevent duplicate (filme_id, ator_id, personagem) for cast
- **Uniqueness**: Prevent duplicate (filme_id, pessoa_id, funcao_tecnica_id) for crew
- **Character Length**: Limit character names to 100 characters
- **Required Fields**: Ensure all relationship fields are populated

## Error Handling

### Validation Errors
- **Duplicate Relationships**: Clear messages about existing combinations
- **Missing Data**: Specific field-level error messages
- **Invalid References**: Handle non-existent person or role selections

### Database Errors
- **Transaction Rollback**: Automatic rollback on any database operation failure
- **Connection Issues**: Graceful handling of database connectivity problems
- **Constraint Violations**: User-friendly messages for database constraint errors

### User Experience
- **Flash Messages**: Success and error messages using Flask's flash system
- **Form Persistence**: Retain form data on validation errors
- **Modal State**: Proper modal handling during error conditions

## Testing Strategy

### Unit Tests
- **Service Layer**: Test all CastCrewService methods with various scenarios
- **Form Validation**: Test form classes with valid and invalid data
- **Model Operations**: Test database operations and constraint handling

### Integration Tests
- **Route Handlers**: Test complete request/response cycles
- **Authentication**: Verify access control for all endpoints
- **Database Transactions**: Test rollback behavior on errors

### User Interface Tests
- **Modal Functionality**: Test modal show/hide and form interactions
- **Autocomplete**: Test person search and selection functionality
- **Responsive Design**: Verify functionality across different screen sizes

### Test Data Management
- **Fixtures**: Create test movies, people, and relationships
- **Cleanup**: Ensure proper test data cleanup between tests
- **Edge Cases**: Test boundary conditions and error scenarios

## Security Considerations

### Authentication Requirements
- All management operations require user authentication
- Public users can only view cast and crew information
- No sensitive data exposure in error messages

### Input Validation
- Server-side validation for all form inputs
- CSRF protection via Flask-WTF (form.csrf_token())
- UUID validation for all entity references (rememeber to cast from str to Uuid and vice-versa when required)

### Data Integrity
- Database constraints prevent invalid relationships
- Transaction management ensures data consistency
- Proper error handling prevents data corruption

## Performance Considerations

### Database Optimization
- Utilize existing indexes on junction table foreign keys
- Efficient queries for cast and crew retrieval
- Minimal database round trips for operations

### Frontend Optimization
- Lazy loading of modal content
- Efficient autocomplete with debouncing
- Minimal JavaScript for enhanced functionality

### Caching Strategy
- Leverage existing person photo caching
- Cache technical role dropdown data
- Utilize browser caching for static assets