# Design Document

## Overview

The person details feature will create a comprehensive view for individual persons in the movie database, showing their biographical information and complete filmography. This feature extends the existing movie-centric architecture to provide person-centric navigation and information display.

The implementation will follow the existing Flask application patterns, using the Blueprint architecture, service layer pattern, and Jinja2 templating system already established in the codebase.

## Architecture

### URL Structure
- `/pessoa/<uuid:pessoa_id>` - Main person details page
- Integration with existing movie detail pages through hyperlinked person names

### Component Integration
The feature integrates with existing components:
- **Models**: Leverages existing `Pessoa`, `Ator`, `Atuacao`, and `EquipeTecnica` models
- **Services**: Creates new `PessoaService` following the pattern of `FilmeService`
- **Routes**: Adds new `pessoa_bp` Blueprint following the pattern of `filme_bp`
- **Templates**: Creates new person detail template with consistent styling

## Components and Interfaces

### 1. Route Layer (`app/routes/pessoa/__init__.py`)
```python
pessoa_bp = Blueprint('pessoa', __name__, url_prefix='/pessoa')

@pessoa_bp.route('/<uuid:pessoa_id>')
def detalhes_pessoa(pessoa_id):
    # Main person details route
    pass
```

**Responsibilities:**
- Handle HTTP requests for person details
- Validate pessoa_id parameter
- Coordinate with service layer to fetch data
- Render template with person data
- Handle 404 errors for invalid person IDs

### 2. Service Layer (`app/services/pessoa_service.py`)
```python
class PessoaService:
    @classmethod
    def obter_filmografia_completa(cls, pessoa: Pessoa, session=None) -> dict:
        # Returns acting and crew credits organized by type
        pass
    
    @classmethod
    def obter_creditos_atuacao(cls, pessoa: Pessoa, session=None) -> list:
        # Returns acting credits ordered by date
        pass
    
    @classmethod
    def obter_creditos_equipe_tecnica(cls, pessoa: Pessoa, session=None) -> list:
        # Returns crew credits ordered by date
        pass
```

**Responsibilities:**
- Encapsulate business logic for person data retrieval
- Query database for person's acting and crew credits
- Order filmography by release date (descending)
- Handle data aggregation and formatting
- Follow the same session management pattern as `FilmeService`

### 3. Template Layer (`app/templates/pessoa/detalhes.jinja2`)
**Structure:**
- Person header with photo, name, and biographical information
- Acting credits section (if applicable)
- Crew credits section (if applicable)
- Consistent styling with existing movie detail pages

### 4. Template Updates (`app/templates/filme/detalhes.jinja2`)
**Modifications:**
- Convert actor names to hyperlinks: `<a href="{{ url_for('pessoa.detalhes_pessoa', pessoa_id=ator_id) }}">{{ nome_ator }}</a>`
- Convert crew member names to hyperlinks: `<a href="{{ url_for('pessoa.detalhes_pessoa', pessoa_id=pessoa_id) }}">{{ nome_pessoa }}</a>`

## Data Models

### Existing Models Usage
The feature leverages existing database models without modifications:

**Pessoa Model:**
- `id`, `nome`, `data_nascimento`, `nacionalidade`, `biografia`, `foto_base64`

**Ator Model:**
- Links to `Pessoa` via `pessoa_id`
- Provides `nome_artistico` if different from real name

**Atuacao Model:**
- Links actors to films with character information
- Provides `personagem`, `creditado`, `protagonista`

**EquipeTecnica Model:**
- Links persons to films with technical roles
- Provides `creditado` status and links to `FuncaoTecnica`

### Data Flow
1. **Person ID** → `Pessoa.get_by_id(pessoa_id)`
2. **Acting Credits** → Query `Atuacao` joined with `Filme` where `ator.pessoa_id = pessoa.id`
3. **Crew Credits** → Query `EquipeTecnica` joined with `Filme` and `FuncaoTecnica` where `pessoa_id = pessoa.id`
4. **Ordering** → All credits ordered by `Filme.ano_lancamento DESC`

## Error Handling

### 404 Handling
- Invalid `pessoa_id` returns 404 with user-friendly error page
- Uses existing error template pattern from the application

### Data Validation
- UUID validation handled by Flask route parameter conversion
- Database query errors caught and logged appropriately

### Graceful Degradation
- Missing biographical information displays gracefully
- Empty filmography sections are hidden rather than showing empty lists
- Missing photos show placeholder icons

## Testing Strategy

### Unit Tests
- `PessoaService` methods with mock data
- Edge cases: person with no credits, person with only acting credits, person with only crew credits
- Data ordering verification

### Integration Tests
- Route handling with valid and invalid person IDs
- Template rendering with various data scenarios
- Hyperlink generation from movie detail pages

### Manual Testing Scenarios
1. Navigate from movie detail page to person page via actor link
2. Navigate from movie detail page to person page via crew member link
3. Verify person page displays correct biographical information
4. Verify filmography is ordered chronologically (newest first)
5. Verify movie titles link back to movie detail pages
6. Test with persons who have both acting and crew credits
7. Test with persons who have only one type of credit
8. Test error handling with invalid person IDs

## Implementation Notes

### Blueprint Registration
The new `pessoa_bp` blueprint must be registered in `app/__init__.py`:
```python
from .routes.pessoa import pessoa_bp
app.register_blueprint(pessoa_bp)
```

### URL Generation
Template updates will use Flask's `url_for()` function to generate person detail URLs:
```jinja2
<a href="{{ url_for('pessoa.detalhes_pessoa', pessoa_id=pessoa.id) }}">{{ pessoa.nome }}</a>
```

### Performance Considerations
- Service methods use efficient joins to minimize database queries
- Filmography queries are optimized with proper indexing on foreign keys
- Template rendering uses lazy loading for large filmographies

### Consistency with Existing Patterns
- Follows the same service layer pattern as `FilmeService`
- Uses the same template structure and styling as movie detail pages
- Maintains consistent error handling and user experience patterns