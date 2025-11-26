# Design Document

## Overview

Esta funcionalidade implementa uma página de detalhes para pessoas no sistema de filmes, seguindo o padrão arquitetural existente. A solução utiliza o blueprint `pessoa_bp` já registrado, criando uma nova rota para detalhes e templates correspondentes. A implementação reutiliza os serviços existentes (`PessoaService`, `AtorService`, `FilmeService`) e segue o padrão visual estabelecido pelos detalhes de filmes.

## Architecture

### Route Structure
```
/pessoa/<uuid:pessoa_id>/detalhes - GET
```

A rota será implementada no blueprint `pessoa_bp` existente em `app/routes/pessoas/__init__.py`, seguindo o padrão das rotas de filme.

### Template Structure
```
app/routes/pessoas/templates/
├── pessoa/
│   └── web/
│       ├── details.jinja2          # Template principal de detalhes
│       └── _header_pessoa.jinja2   # Header reutilizável (similar ao filme)
```

### Service Layer Integration
- **PessoaService**: Utilizado para obter funções técnicas via `obter_funcoes()`
- **AtorService**: Utilizado para obter papéis de atuação via `obter_papeis()`
- **FilmeService**: Utilizado quando necessário para operações relacionadas a filmes

## Components and Interfaces

### Route Handler
```python
@pessoa_bp.route('/<uuid:pessoa_id>/detalhes', methods=['GET'])
def pessoa_detalhes(pessoa_id):
    """Apresenta os detalhes completos de uma pessoa.
    
    Args:
        pessoa_id (uuid.UUID): ID da pessoa
        
    Returns:
        Template renderizado com detalhes da pessoa
        
    Raises:
        404: Se a pessoa não for encontrada
    """
```

### Template Context Data
```python
{
    'pessoa': Pessoa,                    # Objeto pessoa com dados básicos
    'papeis': List[Dict],               # Lista de filmes e personagens (AtorService)
    'funcoes_tecnicas': List[Dict],     # Lista de filmes e funções (PessoaService)
    'title': str                        # Título da página
}
```

### Service Method Extensions

#### PessoaService Enhancement
Método existente `obter_funcoes()` já atende aos requisitos. Retorna estrutura:
```python
[
    {
        'filme': Filme,
        'funcoes': [('Diretor', True), ('Montador', False)]
    }
]
```

#### AtorService Enhancement  
Método existente `obter_papeis()` já atende aos requisitos. Retorna estrutura:
```python
[
    {
        'filme': Filme,
        'personagens': [('Batman', True), ('Bruce Wayne', True)]
    }
]
```

## Data Models

### Existing Models Used
- **Pessoa**: Modelo principal com foto, nome, biografia
- **Ator**: Relacionamento com Pessoa para dados de atuação
- **Filme**: Modelo de filme para links e informações
- **Atuacao**: Junção entre Ator e Filme
- **EquipeTecnica**: Junção entre Pessoa e Filme para funções técnicas

### Template Data Flow
```
Route Handler → Services → Models → Template Context → Jinja2 Rendering
```

## Error Handling

### 404 Handling
- Pessoa não encontrada: `abort(404)` seguindo padrão do `detail_filme`
- Tratamento automático pelo error handler global da aplicação

### Data Validation
- UUID validation automática pelo Flask routing
- Verificação de existência da pessoa no banco de dados
- Tratamento de listas vazias nos templates (mensagens informativas)

### Service Error Handling
- Utilização dos serviços existentes que já possuem tratamento de erro
- Sessão de banco de dados gerenciada automaticamente pelo Flask-SQLAlchemy

## Testing Strategy

### Unit Tests
- Teste da rota `pessoa_detalhes` com pessoa existente
- Teste da rota `pessoa_detalhes` com pessoa inexistente (404)
- Teste de renderização do template com dados completos
- Teste de renderização do template com listas vazias

### Integration Tests
- Teste de navegação bidirecional (filme → pessoa → filme)
- Teste de links funcionais entre páginas
- Teste de exibição correta de dados dos serviços

### Template Tests
- Verificação de estrutura HTML responsiva
- Teste de exibição de placeholder quando não há foto
- Teste de links para detalhes de filmes
- Teste de mensagens informativas para listas vazias

## Implementation Details

### Template Layout Structure
```html
<div class="card">
    <div class="card-header">
        <div class="row">
            <div class="col-md-4">
                <!-- Foto da pessoa -->
            </div>
            <div class="col-md-8">
                <!-- Header com nome, biografia -->
            </div>
        </div>
    </div>
    <div class="card-body">
        <div class="row">
            <div class="col-md-6">
                <!-- Filmografia como ator -->
            </div>
            <div class="col-md-6">
                <!-- Participação em equipe técnica -->
            </div>
        </div>
    </div>
</div>
```

### Navigation Links Update
Modificação no template `filme/web/details.jinja2`:
```html
<!-- Elenco -->
<a href="{{ url_for('pessoa.pessoa_detalhes', pessoa_id=id_ator) }}" class="text-decoration-none">
    <strong>{{ nome }}</strong>
</a>

<!-- Equipe Técnica -->
<a href="{{ url_for('pessoa.pessoa_detalhes', pessoa_id=id_pessoa) }}" class="text-decoration-none">
    <strong>{{ nome }}</strong>
</a>
```

### Responsive Design
- Utilização do sistema de grid Bootstrap existente
- Layout adaptável para dispositivos móveis
- Imagens responsivas com `object-fit: cover`
- Estrutura de colunas que se empilham em telas pequenas

### Performance Considerations
- Reutilização de serviços existentes otimizados
- Queries eficientes através dos métodos dos serviços
- Lazy loading de relacionamentos quando apropriado
- Cache de imagens através do sistema existente de fotos