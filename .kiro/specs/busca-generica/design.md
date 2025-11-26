# Design Document - Busca Genérica

## Overview

Este documento descreve o design técnico para implementar a funcionalidade de busca genérica no MyMovieDB. A solução conectará o campo de busca existente na navbar a um sistema backend que pesquisa simultaneamente em filmes e pessoas, retornando resultados organizados em uma página dedicada.

## Architecture

### High-Level Architecture

```
[Navbar Search Form] → [Search Route] → [Search Service] → [Database Queries] → [Results Template]
```

### Component Interaction Flow

1. **User Input**: Usuário digita termo na navbar e submete o formulário
2. **Route Handler**: Rota `/buscar` recebe o parâmetro `q` e valida entrada
3. **Service Layer**: `SearchService` executa consultas paralelas em filmes e pessoas
4. **Data Processing**: Resultados são formatados e limitados
5. **Template Rendering**: Página de resultados é renderizada com dados organizados

## Components and Interfaces

### 1. Route Handler (`app/routes/root/__init__.py`)

**Nova rota**: `/buscar`
- **Método**: GET
- **Parâmetros**: `q` (query string)
- **Validação**: Termo mínimo de 2 caracteres
- **Response**: Template com resultados ou mensagem de erro

```python
@root_bp.route("/buscar")
def buscar():
    """Executa busca genérica em filmes e pessoas."""
    # Validação e chamada ao service
    # Renderização do template de resultados
```

### 2. Search Service (`app/services/search_service.py`)

**Classe principal**: `SearchService`
- **Método**: `buscar_geral(termo: str) -> SearchResult`
- **Responsabilidades**:
  - Executar consultas SQL otimizadas
  - Aplicar filtros case-insensitive
  - Limitar resultados (20 por categoria)
  - Formatar dados para apresentação

**Estruturas de dados**:
```python
@dataclass
class SearchResult:
    filmes: list[FilmeSearchResult]
    pessoas: list[PessoaSearchResult]
    termo_busca: str
    total_filmes: int
    total_pessoas: int

@dataclass
class FilmeSearchResult:
    id: uuid.UUID
    titulo_original: str
    titulo_portugues: Optional[str]
    ano_lancamento: Optional[int]
    com_poster: bool

@dataclass
class PessoaSearchResult:
    id: uuid.UUID
    nome: str
    nome_artistico: Optional[str]
    com_foto: bool
    eh_ator: bool
```

### 3. Database Queries

**Consulta de Filmes**:
```sql
SELECT f.id, f.titulo_original, f.titulo_portugues, f.ano_lancamento, f.com_poster
FROM filmes f
WHERE (
    LOWER(f.titulo_original) LIKE LOWER('%termo%') OR
    LOWER(f.titulo_portugues) LIKE LOWER('%termo%') OR
    LOWER(f.sinopse) LIKE LOWER('%termo%')
)
ORDER BY f.titulo_original
LIMIT 20
```

**Consulta de Pessoas**:
```sql
SELECT p.id, p.nome, a.nome_artistico, p.com_foto, 
       CASE WHEN a.id IS NOT NULL THEN true ELSE false END as eh_ator
FROM pessoas p
LEFT JOIN atores a ON p.id = a.pessoa_id
WHERE (
    LOWER(p.nome) LIKE LOWER('%termo%') OR
    LOWER(a.nome_artistico) LIKE LOWER('%termo%') OR
    LOWER(p.biografia) LIKE LOWER('%termo%')
)
ORDER BY p.nome
LIMIT 20
```

### 4. Template Updates

**Navbar Update** (`app/templates/navbar.jinja2`):
- Alterar `action="#"` para `action="{{ url_for('root.buscar') }}"`
- Manter estrutura existente (desktop e mobile)

**New Template** (`app/routes/root/templates/root/buscar.jinja2`):
- Layout responsivo com seções separadas
- Cards para filmes (com poster thumbnail)
- Cards para pessoas (com foto thumbnail)
- Mensagens de "nenhum resultado encontrado"
- Preservação do termo de busca no campo

## Data Models

### Existing Models Integration

**Filme Model** - Campos utilizados:
- `id`: Identificação única
- `titulo_original`: Busca principal
- `titulo_portugues`: Busca secundária
- `sinopse`: Busca em conteúdo
- `ano_lancamento`: Exibição
- `com_poster`: Controle de thumbnail

**Pessoa Model** - Campos utilizados:
- `id`: Identificação única
- `nome`: Busca principal
- `biografia`: Busca em conteúdo
- `com_foto`: Controle de thumbnail

**Ator Model** - Campos utilizados:
- `nome_artistico`: Busca adicional para atores
- `pessoa_id`: Relacionamento

### Search Index Considerations

Para otimização futura, considerar:
- Índices compostos nos campos de busca
- Full-text search (PostgreSQL) para produção
- Cache de resultados frequentes

## Error Handling

### Input Validation
- **Termo muito curto**: Mensagem amigável solicitando mais caracteres
- **Termo vazio**: Redirecionamento para página inicial
- **Caracteres especiais**: Escape automático para prevenir SQL injection

### Database Errors
- **SQLAlchemyError**: Log do erro + mensagem genérica ao usuário
- **Timeout**: Mensagem de "busca demorou muito, tente novamente"
- **Connection Error**: Mensagem de "serviço temporariamente indisponível"

### Service Layer Error Handling
```python
class SearchServiceError(Exception):
    """Exceção customizada para operações de busca."""
    pass

try:
    resultado = SearchService.buscar_geral(termo)
except SearchServiceError as e:
    # Log error e retorna página com mensagem de erro
    current_app.logger.error(f"Erro na busca: {e}")
    return render_template("root/buscar.jinja2", erro="Erro interno na busca")
```

## Testing Strategy

### Unit Tests
- **SearchService**: Testes isolados com mock do database
- **Route Handler**: Testes de validação e response codes
- **Query Logic**: Testes com dados de fixture

### Integration Tests
- **End-to-End**: Submissão de formulário → resultados
- **Database Integration**: Consultas reais com dados de teste
- **Template Rendering**: Verificação de HTML gerado

### Test Cases
1. **Busca com resultados**: Termo que retorna filmes e pessoas
2. **Busca sem resultados**: Termo que não encontra nada
3. **Busca só filmes**: Termo que encontra apenas filmes
4. **Busca só pessoas**: Termo que encontra apenas pessoas
5. **Termo muito curto**: Validação de entrada
6. **Caracteres especiais**: Escape e sanitização
7. **Limite de resultados**: Verificar truncamento em 20 itens
8. **Case insensitive**: Busca funciona independente de maiúsculas/minúsculas

### Performance Tests
- **Response Time**: Busca deve completar em < 2 segundos
- **Concurrent Users**: Múltiplas buscas simultâneas
- **Large Dataset**: Performance com muitos registros

## Security Considerations

### Input Sanitization
- Escape de caracteres SQL especiais
- Validação de comprimento máximo (evitar DoS)
- Sanitização de HTML na exibição

### SQL Injection Prevention
- Uso exclusivo de parameterized queries
- Validação rigorosa de entrada
- Logging de tentativas suspeitas

### Rate Limiting (Future Enhancement)
- Limitar número de buscas por IP/usuário
- Implementar cooldown entre buscas
- Monitoramento de padrões abusivos

## Performance Optimization

### Database Optimization
- Índices nos campos de busca mais utilizados
- LIMIT nas queries para evitar resultados excessivos
- Consultas paralelas para filmes e pessoas

### Caching Strategy (Future)
- Cache de resultados por termo de busca
- TTL de 15 minutos para resultados
- Invalidação em updates de dados

### Frontend Optimization
- Lazy loading de imagens (posters/fotos)
- Paginação para muitos resultados (future enhancement)
- Debounce em busca automática (future enhancement)

## Deployment Considerations

### Database Migrations
- Não são necessárias alterações de schema
- Considerar criação de índices para otimização

### Configuration
- Nenhuma configuração adicional necessária
- Usar configurações existentes do Flask

### Monitoring
- Log de termos de busca mais frequentes
- Métricas de performance das consultas
- Monitoramento de erros de busca