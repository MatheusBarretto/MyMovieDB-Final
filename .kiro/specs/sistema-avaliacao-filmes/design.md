# Documento de Design - Sistema de Avaliação de Filmes

## Visão Geral

O sistema de avaliação de filmes será implementado seguindo a arquitetura MVC existente da aplicação Flask. O design utiliza os padrões já estabelecidos: modelos SQLAlchemy, serviços para lógica de negócio, formulários WTForms, rotas Blueprint e templates Jinja2. O sistema permitirá que usuários autenticados avaliem filmes e visualizem estatísticas agregadas.

## Arquitetura

### Camada de Dados (Models)
- **Modelo Avaliacao**: Já existe em `app/models/juncoes.py` com campos: nota, comentario, recomendaria
- **Relacionamentos**: Filme 1:N Avaliacao, User 1:N Avaliacao
- **Constraint**: Unique constraint (filme_id, usuario_id) para evitar avaliações duplicadas

### Camada de Serviço (Services)
- **FilmeService**: Já possui métodos para estatísticas (`obter_estatisticas_avaliacoes`)
- **AvaliacaoService**: Novo serviço para operações CRUD de avaliações
- **PaginationService**: Já existe para paginação de listas

### Camada de Apresentação (Views/Routes)
- **Blueprint filme**: Extensão das rotas existentes em `app/routes/filme/__init__.py`
- **Formulários**: Novos formulários para criação/edição de avaliações
- **Templates**: Novos templates para exibição e formulários de avaliação

### Camada de Controle (Routes)
- Rotas RESTful para operações CRUD de avaliações
- Integração com sistema de autenticação existente (Flask-Login)
- Validação de permissões (usuário só pode editar suas próprias avaliações)

## Componentes e Interfaces

### 1. Serviço de Avaliações (AvaliacaoService)

```python
class AvaliacaoService:
    @classmethod
    def criar_ou_atualizar_avaliacao(cls, filme_id, usuario_id, nota, comentario, recomendaria, session=None) -> Avaliacao
    
    @classmethod
    def obter_avaliacao_usuario(cls, filme_id, usuario_id, session=None) -> Optional[Avaliacao]
    
    @classmethod
    def listar_avaliacoes_filme(cls, filme_id, page=1, per_page=10, session=None) -> Pagination
    
    @classmethod
    def excluir_avaliacao(cls, avaliacao_id, usuario_id, session=None) -> bool
    
    @classmethod
    def validar_permissao_edicao(cls, avaliacao_id, usuario_id, session=None) -> bool
```

### 1.1. Extensão do FilmeService para Estatísticas Detalhadas

```python
@dataclass
class FilmeReviewStats:
    nota_media: float
    total_avaliacoes: int
    total_recomendacoes: int
    percentual_recomendacoes: float
    distribuicao_notas: dict[int, float]  # {nota: percentual}

class FilmeService:
    @classmethod
    def obter_estatisticas_avaliacoes(cls, filme: Filme, session=None) -> FilmeReviewStats:
        # Calcula estatísticas básicas + distribuição de notas por nota inteira (0-5)
        pass
```

### 2. Formulários (app/forms/filme/)

```python
class AvaliacaoForm(FlaskForm):
    nota = SelectField('Nota', choices=[(i, str(i)) for i in range(0, 6)], coerce=int)
    comentario = TextAreaField('Comentário', validators=[Length(max=1000)])
    recomendaria = BooleanField('Recomendaria este filme')
    submit = SubmitField('Salvar Avaliação')
```

### 3. Rotas (app/routes/filme/)

```python
# Rotas principais
@filme_bp.route('/<uuid:filme_id>')
def detalhes_filme(filme_id)  # Exibe filme com avaliações e formulário

@filme_bp.route('/<uuid:filme_id>/avaliar', methods=['POST'])
@login_required
def avaliar_filme(filme_id)  # Cria/atualiza avaliação

@filme_bp.route('/avaliacao/<uuid:avaliacao_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_avaliacao(avaliacao_id)  # Edita avaliação existente

@filme_bp.route('/avaliacao/<uuid:avaliacao_id>/excluir', methods=['POST'])
@login_required
def excluir_avaliacao(avaliacao_id)  # Exclui avaliação

@filme_bp.route('/random')
def random_filme()  # Filme aleatório

@filme_bp.route('/')
def list_filmes()  # Lista com filtros e ordenação
```

### 4. Templates

```
app/templates/filme/
├── detalhes.jinja2          # Página principal do filme
├── lista.jinja2             # Lista de filmes com avaliações
├── _avaliacao_form.jinja2   # Formulário de avaliação (partial)
├── _avaliacao_item.jinja2   # Item individual de avaliação (partial)
└── _estatisticas.jinja2     # Estatísticas do filme (partial)
```

## Modelos de Dados

### Modelo Avaliacao (Existente)

```python
class Avaliacao:
    id: UUID(PK)
    filme_id: UUID(FK -> filmes.id_pessoa)
    usuario_id: UUID(FK -> usuarios.id_pessoa)
    nota: int(0 - 5)
    comentario: str(opcional, max
    1000
    chars)
    recomendaria: bool
    created_at: datetime
    updated_at: datetime
```

### Extensões ao Modelo Filme
- Propriedade calculada para nota média
- Propriedade para total de avaliações
- Propriedade para percentual de recomendações

## Tratamento de Erros

### Validações de Negócio
- **Nota**: Deve estar entre 0 e 5
- **Comentário**: Máximo 1000 caracteres
- **Permissões**: Usuário só pode editar/excluir suas próprias avaliações
- **Autenticação**: Apenas usuários logados podem avaliar

### Tratamento de Exceções
- **Filme não encontrado**: HTTP 404
- **Avaliação não encontrada**: HTTP 404
- **Acesso negado**: HTTP 403 com redirecionamento
- **Dados inválidos**: Formulário com mensagens de erro
- **Erro de banco**: Rollback automático e mensagem genérica

### Mensagens de Feedback
- **Sucesso**: "Avaliação salva com sucesso"
- **Atualização**: "Avaliação atualizada com sucesso"
- **Exclusão**: "Avaliação removida com sucesso"
- **Erro**: "Erro ao processar avaliação. Tente novamente."

## Estratégia de Testes

### Testes Unitários
- **AvaliacaoService**: Testes para todos os métodos CRUD
- **FilmeService**: Testes para cálculo de estatísticas
- **Formulários**: Validação de campos e regras de negócio
- **Modelos**: Testes de relacionamentos e constraints

### Testes de Integração
- **Rotas**: Testes end-to-end para fluxos completos
- **Autenticação**: Verificação de permissões e redirecionamentos
- **Banco de dados**: Testes com transações e rollbacks
- **Templates**: Renderização correta de dados

### Cenários de Teste
1. **Criar primeira avaliação**: Usuário avalia filme pela primeira vez
2. **Atualizar avaliação**: Usuário modifica avaliação existente
3. **Visualizar avaliações**: Listagem paginada de avaliações
4. **Permissões**: Tentativa de editar avaliação de outro usuário
5. **Estatísticas**: Cálculo correto de médias e percentuais
6. **Filme aleatório**: Seleção e redirecionamento corretos
7. **Filtros e ordenação**: Lista de filmes com diferentes critérios

### Dados de Teste
- **Filmes**: Mínimo 10 filmes para testes de paginação
- **Usuários**: 3-5 usuários para testes de permissão
- **Avaliações**: Variadas (notas 1-10, com/sem comentários)
- **Edge cases**: Filmes sem avaliações, usuários sem avaliações

## Considerações de Performance

### Otimizações de Consulta
- **Eager loading**: Carregar avaliações com usuários em uma consulta
- **Índices**: Índices compostos em (filme_id, created_at) para ordenação
- **Agregações**: Cache de estatísticas para filmes com muitas avaliações

### Paginação
- **Limite padrão**: 10 avaliações por página
- **Limite máximo**: 50 avaliações por página
- **Offset otimizado**: Usar cursor-based pagination para listas grandes

### Caching (Futuro)
- **Estatísticas**: Cache Redis para estatísticas de filmes populares
- **Listas**: Cache de listas ordenadas por popularidade
- **Invalidação**: Invalidar cache ao criar/atualizar avaliações

## Segurança

### Autenticação e Autorização
- **Login obrigatório**: Apenas usuários autenticados podem avaliar
- **Propriedade**: Usuários só podem editar suas próprias avaliações
- **CSRF**: Proteção via Flask-WTF em todos os formulários

### Validação de Entrada
- **Sanitização**: Escape de HTML em comentários
- **Validação**: Validação server-side de todos os campos
- **Rate limiting**: Prevenção de spam de avaliações (futuro)

### Auditoria
- **Logs**: Log de todas as operações de avaliação
- **Timestamps**: Rastreamento de criação e modificação
- **Soft delete**: Manter histórico de avaliações excluídas (futuro)
