"""Serviço de gerenciamento de pessoas.

Este módulo fornece a camada de serviço para operações relacionadas a pessoas,
incluindo consulta de funções técnicas em filmes e outras operações de negócio.

Classes principais:
    - PessoaService: Serviço principal com métodos para operações de pessoas
"""
from collections import defaultdict

from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.infra.modulos import db
from app.models.pessoa import Ator, Pessoa
from .utils import aplicar_filtro_creditado


class PessoaError(Exception):
    pass


class PessoaService:
    """Serviço para operações relacionadas a pessoas.

    Centraliza a lógica de negócio relacionada a pessoas, separando-a dos modelos.
    Utiliza uma sessão SQLAlchemy configurável para permitir uso em diferentes contextos,
    como testes ou transações customizadas.
    """

    # Sessão padrão a ser utilizada quando nenhuma sessão é fornecida
    _default_session = db.session

    @classmethod
    def set_default_session(cls, session):
        """Define a sessão padrão a ser utilizada pelo serviço.

        Args:
            session: Sessão SQLAlchemy a ser utilizada como padrão
        """
        cls._default_session = session

    @classmethod
    def obter_funcoes(cls,
                      pessoa: Pessoa,
                      creditado: bool = True,
                      nao_creditado: bool = True,
                      year_reverse: bool = True,
                      session=None) -> list:
        """Retorna lista de filmes e funções técnicas desempenhadas pela pessoa.

        Args:
            pessoa (Pessoa): Instância da pessoa
            creditado (bool): Se True, inclui funções creditadas. Default: True
            nao_creditado (bool): Se True, inclui funções não creditadas. Default: True
            year_reverse (bool): Se True, ordena do filme mais recente para o mais antigo.
            Default: True
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.

        Returns:
            list: Lista de dicionários com estrutura:
                [
                    {
                        'filme': Filme,
                        'funcoes': [
                            ('Diretor', True),   # (nome_funcao, creditado)
                            ('Montador', False)
                        ]
                    },
                    ...
                ]
                Retorna lista vazia se nenhum dos filtros estiver ativo.
                A lista é ordenada por ano de lançamento do filme.

        Raises:
            ValueError: Se ambos os filtros forem False

        Examples:
            >>> # Apenas funções creditadas
            >>> PessoaService.obter_funcoes(pessoa, nao_creditado=False)

            >>> # Apenas funções não creditadas
            >>> PessoaService.obter_funcoes(pessoa, creditado=False)

            >>> # Todas as funções
            >>> PessoaService.obter_funcoes(pessoa)
        """
        from app.models.juncoes import EquipeTecnica
        from app.models.filme import Filme
        from sqlalchemy import desc

        if session is None:
            session = cls._default_session

        # Constrói a query base com join no Filme para ordenação
        stmt = (
            select(EquipeTecnica)
            .join(Filme, EquipeTecnica.filme_id == Filme.id)
            .where(EquipeTecnica.pessoa_id == pessoa.id)
        )
        if year_reverse:
            stmt = stmt.order_by(desc(Filme.ano_lancamento))
        else:
            stmt = stmt.order_by(Filme.ano_lancamento)

        # Aplica filtros de creditado usando função utilitária
        stmt = aplicar_filtro_creditado(stmt, EquipeTecnica.creditado, creditado, nao_creditado)

        # Executa a query
        resultado = session.execute(stmt).scalars().all()

        # Agrupa funções por filme
        filmes_funcoes = defaultdict(list)
        filmes_obj = {}  # Guarda referência aos objetos Filme

        for equipe in resultado:
            filme_id = equipe.filme_id
            # Adiciona tupla (nome_funcao, creditado)
            filmes_funcoes[filme_id].append((equipe.funcao_tecnica.nome, equipe.creditado))
            if filme_id not in filmes_obj:
                filmes_obj[filme_id] = equipe.filme

        # Monta a lista de retorno mantendo a ordem do resultado
        funcoes = []
        filmes_adicionados = set()
        for equipe in resultado:
            if equipe.filme_id not in filmes_adicionados:
                funcoes.append({
                    'filme'  : equipe.filme,
                    'funcoes': filmes_funcoes[equipe.filme_id]
                })
                filmes_adicionados.add(equipe.filme_id)

        return funcoes

    @classmethod
    def listar_pessoas(cls,
                       page: int = 1,
                       per_page: int = 20,
                       search: str = None,
                       session=None):
        """Lista pessoas com paginação e busca por nome ou nome artístico.

        Args:
            page (int): Número da página (começa em 1). Default: 1
            per_page (int): Número de registros por página. Default: 20
            search (str): Termo de busca para filtrar por nome ou nome artístico. Default: None
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.

        Returns:
            Pagination: Objeto de paginação do Flask-SQLAlchemy contendo:
                - items: Lista de objetos Pessoa
                - page: Página atual
                - pages: Total de páginas
                - per_page: Registros por página
                - total: Total de registros
                - has_next: Se há próxima página
                - has_prev: Se há página anterior

        Examples:
            >>> # Listar primeira página
            >>> resultado = PessoaService.listar_pessoas()
            >>> pessoas = resultado.items

            >>> # Buscar por nome ou nome artístico
            >>> resultado = PessoaService.listar_pessoas(search="João")

            >>> # Página específica
            >>> resultado = PessoaService.listar_pessoas(page=2, per_page=10)
        """
        if session is None:
            session = cls._default_session

        # Constrói statement base com LEFT JOIN para incluir dados do ator
        stmt = (
            select(Pessoa)
            .outerjoin(Ator, Pessoa.id == Ator.pessoa_id)
            .order_by(Pessoa.nome)
        )

        # Aplica filtro de busca se fornecido
        # Busca tanto em Pessoa.nome quanto em Ator.nome_artistico
        if search and search.strip():
            search_term = f"%{search.strip()}%"
            stmt = stmt.where(
                    or_(
                            Pessoa.nome.ilike(search_term),
                            Ator.nome_artistico.ilike(search_term)
                    )
            )

        # Aplica paginação usando db.paginate com statement
        return db.paginate(
                stmt,
                page=page,
                per_page=per_page,
                error_out=False
        )

    @classmethod
    def listar_pessoas_por_funcao_tecnica(cls,
                                         funcao_tecnica,
                                         page: int = 1,
                                         per_page: int = 20,
                                         search: str = None,
                                         session=None):
        """Lista pessoas que executam uma função técnica específica com paginação.

        Args:
            funcao_tecnica (FuncaoTecnica): Instância da função técnica para filtrar pessoas
            page (int): Número da página (começa em 1). Default: 1
            per_page (int): Número de registros por página. Default: 20
            search (str): Termo de busca para filtrar por nome ou nome artístico. Default: None
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.

        Returns:
            Pagination: Objeto de paginação do Flask-SQLAlchemy contendo:
                - items: Lista de objetos Pessoa que executam a função técnica
                - page: Página atual
                - pages: Total de páginas
                - per_page: Registros por página
                - total: Total de registros
                - has_next: Se há próxima página
                - has_prev: Se há página anterior

        Examples:
            >>> # Listar diretores
            >>> funcao_diretor = FuncaoTecnica.get_by_id(funcao_id)
            >>> resultado = PessoaService.listar_pessoas_por_funcao_tecnica(funcao_diretor)
            >>> diretores = resultado.items

            >>> # Buscar roteiristas com "Silva" no nome
            >>> resultado = PessoaService.listar_pessoas_por_funcao_tecnica(funcao_roteirista, search="Silva")
        """
        from app.models.juncoes import EquipeTecnica

        if session is None:
            session = cls._default_session

        # Constrói statement com join na tabela de equipe técnica
        # Usa DISTINCT para evitar duplicatas (pessoa pode ter a mesma função em vários filmes)
        stmt = (
            select(Pessoa)
            .distinct()
            .join(EquipeTecnica, Pessoa.id == EquipeTecnica.pessoa_id)
            .outerjoin(Ator, Pessoa.id == Ator.pessoa_id)
            .where(EquipeTecnica.funcao_tecnica_id == funcao_tecnica.id)
            .order_by(Pessoa.nome)
        )

        # Aplica filtro de busca se fornecido
        if search and search.strip():
            search_term = f"%{search.strip()}%"
            stmt = stmt.where(
                    or_(
                            Pessoa.nome.ilike(search_term),
                            Ator.nome_artistico.ilike(search_term)
                    )
            )

        # Aplica paginação usando db.paginate com statement
        return db.paginate(
                stmt,
                page=page,
                per_page=per_page,
                error_out=False
        )

    @classmethod
    def criar_pessoa(cls,
                     form_data,
                     session=None,
                     auto_commit: bool = True):
        """Cria uma nova pessoa a partir dos dados do formulário.

        Args:
            form_data: Objeto de formulário Flask-WTF com dados validados
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            Pessoa: Nova instância de Pessoa criada e salva no banco

        Raises:
            ValueError: Se os dados do formulário são inválidos
            ImageProcessingError: Se houver erro ao processar a foto
            PessoaError: Se houver erro de banco de dados ou outros erros durante a criação

        Examples:
            >>> form = PessoaForm()
            >>> if form.validate_on_submit():
            ...     pessoa = PessoaService.criar_pessoa(form)
        """
        if session is None:
            session = cls._default_session

        try:
            # Cria nova instância de Pessoa
            pessoa = Pessoa(
                    nome=form_data.nome.data,
                    data_nascimento=form_data.data_nascimento.data,
                    data_falecimento=form_data.data_falecimento.data,
                    local_nascimento=form_data.local_nascimento.data,
                    biografia=form_data.biografia.data
            )

            # Processa foto se fornecida
            # Verifica se há um arquivo de foto sendo enviado
            if form_data.foto.data and hasattr(form_data.foto.data,
                                               'filename') and form_data.foto.data.filename:
                pessoa.foto = form_data.foto.data

            # Salva no banco
            session.add(pessoa)
            if auto_commit:
                session.commit()

        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            raise PessoaError(f"Erro de banco de dados ao criar pessoa: {str(e)}") from e
        except Exception as e:
            if auto_commit:
                session.rollback()
            raise PessoaError(f"Erro ao criar pessoa: {str(e)}") from e

        return pessoa

    @classmethod
    def atualizar_pessoa(cls,
                         pessoa,
                         form_data,
                         session=None,
                         auto_commit: bool = True):
        """Atualiza uma pessoa existente com dados do formulário.

        Args:
            pessoa (Pessoa): Instância existente da pessoa a ser atualizada
            form_data: Objeto de formulário Flask-WTF com dados validados
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            Pessoa: Instância atualizada da pessoa

        Raises:
            ValueError: Se os dados do formulário são inválidos
            ImageProcessingError: Se houver erro ao processar a foto
            PessoaError: Se houver erro de banco de dados ou outros erros durante a atualização

        Examples:
            >>> pessoa = Pessoa.query.get(pessoa_id)
            >>> form = PessoaForm(obj=pessoa)
            >>> if form.validate_on_submit():
            ...     pessoa_atualizada = PessoaService.atualizar_pessoa(pessoa, form)
        """
        from app.models.pessoa import Ator

        if session is None:
            session = cls._default_session

        try:
            # Atualiza campos básicos
            pessoa.nome = form_data.nome.data
            pessoa.data_nascimento = form_data.data_nascimento.data
            pessoa.data_falecimento = form_data.data_falecimento.data
            pessoa.local_nascimento = form_data.local_nascimento.data
            pessoa.biografia = form_data.biografia.data

            # Processa foto se fornecida (substitui a existente)
            # Verifica se há um novo arquivo de foto sendo enviado
            if form_data.foto.data and hasattr(form_data.foto.data,
                                               'filename') and form_data.foto.data.filename:
                pessoa.foto = form_data.foto.data

            # Gerencia o registro de Ator baseado no nome_artistico
            if hasattr(form_data, 'nome_artistico'):
                # Obtém o valor do campo, tratando None e string vazia
                raw_value = form_data.nome_artistico.data

                # Normaliza o valor: None, string vazia, ou string 'None' -> None
                if raw_value is None or raw_value == '' or str(raw_value).strip().lower() == 'none':
                    nome_artistico = None
                else:
                    nome_artistico = str(raw_value).strip()

                if nome_artistico:
                    # Se há nome artístico fornecido
                    if pessoa.ator:
                        # Atualiza o nome artístico do ator existente
                        pessoa.ator.nome_artistico = nome_artistico
                        session.add(pessoa.ator)  # Marca explicitamente para update
                    else:
                        novo_ator = Ator(pessoa_id=pessoa.id, nome_artistico=nome_artistico)
                        session.add(novo_ator)
                else:
                    # Se nome artístico foi removido e pessoa é ator
                    if pessoa.ator:
                        # Remove o nome artístico (mas mantém o registro de Ator se houver atuações)
                        pessoa.ator.nome_artistico = None
                        session.add(pessoa.ator)  # Marca explicitamente para update

            # O AuditMixin automaticamente atualiza updated_at
            if auto_commit:
                session.commit()

        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            raise PessoaError(f"Erro de banco de dados ao atualizar pessoa: {str(e)}") from e
        except Exception as e:
            if auto_commit:
                session.rollback()
            raise PessoaError(f"Erro ao atualizar pessoa: {str(e)}") from e

        return pessoa

    @classmethod
    def deletar_pessoa(cls,
                       pessoa,
                       session=None,
                       auto_commit: bool = True):
        """Deleta uma pessoa verificando relacionamentos existentes.

        Verifica se a pessoa possui relacionamentos com filmes (como ator ou equipe técnica).
        Se houver relacionamentos, a deleção é abortada conforme requirement 4.3.

        Args:
            pessoa (Pessoa): Instância da pessoa a ser deletada
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            dict: Dicionário com informações sobre a operação:
                - success (bool): Se a operação foi bem-sucedida
                - message (str): Mensagem explicativa sobre o resultado
                - relacionamentos (dict): Contadores dos relacionamentos encontrados

        Raises:
            PessoaError: Para erros de banco de dados ou outros erros durante a deleção

        Examples:
            >>> pessoa = Pessoa.query.get(pessoa_id)
            >>> resultado = PessoaService.deletar_pessoa(pessoa)
            >>> if not resultado['success']:
            ...     print(f"Erro: {resultado['message']}")
        """
        if session is None:
            session = cls._default_session

        # Verifica relacionamentos existentes
        relacionamentos = {
            'ator'            : 1 if pessoa.ator else 0,
            'funcoes_tecnicas': len(pessoa.funcoes_tecnicas)
        }

        # Calcula total de relacionamentos com filmes
        total_relacionamentos = relacionamentos['funcoes_tecnicas']
        if pessoa.ator:
            # Conta atuações do ator
            total_relacionamentos += len(pessoa.ator.filmes)

        # Se há relacionamentos, aborta a deleção
        if total_relacionamentos > 0:
            return {
                'success'        : False,
                'message'        : 'Não é possível deletar esta pessoa pois ela possui '
                                   'relacionamentos com filmes.',
                'relacionamentos': relacionamentos
            }

        # Se não há relacionamentos, pode deletar
        session.delete(pessoa)
        if auto_commit:
            try:
                session.commit()
            except SQLAlchemyError as e:
                session.rollback()
                raise PessoaError(f"Erro de banco de dados ao deletar pessoa: {str(e)}") from e
            except Exception as e:
                session.rollback()
                raise PessoaError(f"Erro ao deletar pessoa: {str(e)}") from e

        return {
            'success'        : True,
            'message'        : 'Pessoa deletada com sucesso.',
            'relacionamentos': relacionamentos
        }

    @classmethod
    def validar_pessoa_unica(cls,
                             nome: str,
                             data_nascimento=None,
                             pessoa_id=None,
                             session=None):
        """Valida se uma pessoa é única baseada em nome e data de nascimento.

        Verifica se já existe uma pessoa com a mesma combinação de nome e data
        de nascimento. Durante edição, exclui o registro atual da verificação.

        Args:
            nome (str): Nome da pessoa a ser validado
            data_nascimento: Data de nascimento da pessoa (opcional)
            pessoa_id: ID da pessoa atual (para exclusão durante edição)
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.

        Returns:
            bool: True se a pessoa é única, False se já existe

        Examples:
            >>> # Validar nova pessoa
            >>> is_unique = PessoaService.validar_pessoa_unica("João Silva", date(1980, 1, 1))

            >>> # Validar durante edição (exclui pessoa atual)
            >>> is_unique = PessoaService.validar_pessoa_unica(
            ...     "João Silva", date(1980, 1, 1), pessoa_id=existing_id
            ... )
        """
        if session is None:
            session = cls._default_session

        # Statement base para buscar pessoa com mesmo nome
        stmt = select(Pessoa).where(Pessoa.nome == nome)

        # Adiciona filtro de data de nascimento se fornecida
        if data_nascimento:
            stmt = stmt.where(Pessoa.data_nascimento == data_nascimento)

        # Exclui a pessoa atual durante edição
        if pessoa_id:
            stmt = stmt.where(Pessoa.id != pessoa_id)

        # Verifica se existe algum registro
        existing_pessoa = session.execute(stmt).scalar_one_or_none()
        return existing_pessoa is None
