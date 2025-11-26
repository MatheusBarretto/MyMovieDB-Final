"""Serviço de gerenciamento de filmes.

Este módulo fornece a camada de serviço para operações relacionadas a filmes,
incluindo cálculo de estatísticas, avaliações, operações CRUD e outras operações de negócio.

Classes principais:
    - FilmeService: Serviço principal com métodos para operações de filmes
    - FilmeReviewStats: Estatísticas de avaliações de filmes
    - FilmeOperationResult: Resultado das operações CRUD
"""
import uuid
from dataclasses import dataclass
from typing import Optional

from flask import current_app
from sqlalchemy import desc, func, Integer, or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.infra.modulos import db
from app.models.filme import Filme, Genero
from app.models.juncoes import FilmeGenero
from .utils import aplicar_filtro_creditado


class FilmeServiceError(Exception):
    """Exceção customizada para operações do FilmeService."""
    pass


@dataclass
class FilmeReviewStats:
    nota_media: float
    total_avaliacoes: int
    total_recomendacoes: int
    percentual_recomendacoes: float
    distribuicao_notas: dict[int, float]  # {nota: percentual}


@dataclass
class FilmeOperationResult:
    """Objeto de resultado para operações CRUD."""
    success: bool
    message: str
    filme: Optional[Filme] = None


class FilmeService:
    """Serviço para operações relacionadas a filmes.

    Centraliza a lógica de negócio relacionada a filmes, separando-a dos modelos.
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
    def obter_estatisticas_avaliacoes(cls,
                                      filme: Filme,
                                      session=None) -> FilmeReviewStats:
        """Retorna estatísticas de avaliações do filme.

        Args:
            filme (Filme): Instância do filme para calcular estatísticas
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.

        Returns:
            FilmeReviewStats: Objeto contendo estatísticas de avaliações do filme
        """
        from app.models.juncoes import Avaliacao

        if session is None:
            session = cls._default_session

        # Query para agregar estatísticas das avaliações
        stmt = (
            select(func.avg(Avaliacao.nota).label('nota_media'),
                func.count(Avaliacao.id).label('total_avaliacoes'),
                func.sum(func.cast(Avaliacao.recomendaria, Integer)).label('total_recomendacoes'))
            .where(Avaliacao.filme_id == filme.id)
        )
        resultado = session.execute(stmt).one()

        # Extrai os valores do resultado
        nota_media = float(resultado.nota_media) if resultado.nota_media is not None else 0.0
        total_avaliacoes = int(
                resultado.total_avaliacoes) if resultado.total_avaliacoes is not None else 0
        total_recomendacoes = int(
                resultado.total_recomendacoes) if resultado.total_recomendacoes is not None else 0

        # Calcula percentual de recomendações
        percentual_recomendacoes = (
                total_recomendacoes / total_avaliacoes * 100) if total_avaliacoes > 0 else 0.0

        # Calcula distribuição de notas (0 a 10)
        distribuicao_notas = {}
        if total_avaliacoes > 0:
            # Query para contar avaliações por nota
            stmt_distribuicao = select(
                    Avaliacao.nota,
                    func.count(Avaliacao.id).label('count')
            ).where(Avaliacao.filme_id == filme.id).group_by(Avaliacao.nota)

            resultado_distribuicao = session.execute(stmt_distribuicao).all()

            # Inicializa todas as notas com 0%
            for nota in range(0, 11):
                distribuicao_notas[nota] = 0.0

            # Calcula percentuais para notas que existem
            for row in resultado_distribuicao:
                nota = row.nota
                count = row.count
                percentual = (count / total_avaliacoes * 100)
                distribuicao_notas[nota] = round(percentual, 2)
        else:
            # Se não há avaliações, todas as notas têm 0%
            for nota in range(0, 11):
                distribuicao_notas[nota] = 0.0

        return FilmeReviewStats(nota_media=round(nota_media, 2),
                                total_avaliacoes=total_avaliacoes,
                                total_recomendacoes=total_recomendacoes,
                                percentual_recomendacoes=round(percentual_recomendacoes, 2),
                                distribuicao_notas=distribuicao_notas)

    @classmethod
    def listar_filmes(cls,
                      page: int = 1,
                      per_page: int = 24,
                      search: str = None,
                      eager_load_generos: bool = False,
                      session=None):
        """Lista filmes com paginação e busca por título.

        Args:
            page (int): Número da página (começa em 1). Default: 1
            per_page (int): Número de registros por página. Default: 24
            search (str): Termo de busca para filtrar por título (original ou português). Default: None
            eager_load_generos (bool): Se True, carrega gêneros com joinedload para evitar N+1. Default: False
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.

        Returns:
            Pagination: Objeto de paginação do Flask-SQLAlchemy contendo:
                - items: Lista de objetos Filme
                - page: Página atual
                - pages: Total de páginas
                - per_page: Registros por página
                - total: Total de registros
                - has_next: Se há próxima página
                - has_prev: Se há página anterior

        Examples:
            >>> # Listar primeira página
            >>> resultado = FilmeService.listar_filmes()
            >>> filmes = resultado.items

            >>> # Buscar por título
            >>> resultado = FilmeService.listar_filmes(search="Matrix")

            >>> # Página """
        if session is None:
            session = cls._default_session

        # Constrói statement base ordenado por ano de lançamento (mais recente primeiro)
        stmt = (
            select(Filme)
            .order_by(desc(Filme.ano_lancamento), Filme.titulo_original)
        )

        # Aplica filtro de busca se fornecido
        # Busca tanto em titulo_original quanto em titulo_portugues
        if search and search.strip():
            search_term = f"%{search.strip()}%"
            stmt = stmt.where(
                    or_(
                            Filme.titulo_original.ilike(search_term),
                            Filme.titulo_portugues.ilike(search_term)
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
    def listar_filmes_por_genero(cls,
                                 genero: Genero,
                                 page: int = 1,
                                 per_page: int = 24,
                                 search: str = None,
                                 session=None):
        """Lista filmes de um gênero específico com paginação e busca.

        Args:
            genero (Genero): Instância do gênero para filtrar filmes
            page (int): Número da página (começa em 1). Default: 1
            per_page (int): Número de registros por página. Default: 24
            search (str): Termo de busca para filtrar por título (original ou português). Default: None
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.

        Returns:
            Pagination: Objeto de paginação do Flask-SQLAlchemy contendo:
                - items: Lista de objetos Filme do gênero especificado
                - page: Página atual
                - pages: Total de páginas
                - per_page: Registros por página
                - total: Total de registros
                - has_next: Se há próxima página
                - has_prev: Se há página anterior

        Examples:
            >>> # Listar filmes de ação
            >>> genero_acao = Genero.get_by_id(genero_id)
            >>> resultado = FilmeService.listar_filmes_por_genero(genero_acao)
            >>> filmes = resultado.items

            >>> # Buscar filmes de drama com "amor" no título
            >>> resultado = FilmeService.listar_filmes_por_genero(genero_drama, search="amor")

            >>> # Página específica
            >>> resultado = FilmeService.listar_filmes_por_genero(genero, page=2, per_page=48)
        """
        if session is None:
            session = cls._default_session

        # Constrói statement com join na tabela de associação
        stmt = (
            select(Filme)
            .join(FilmeGenero, Filme.id == FilmeGenero.filme_id)
            .where(FilmeGenero.genero_id == genero.id)
            .order_by(desc(Filme.ano_lancamento), Filme.titulo_original)
        )

        # Aplica filtro de busca se fornecido
        if search and search.strip():
            search_term = f"%{search.strip()}%"
            stmt = stmt.where(
                    or_(
                            Filme.titulo_original.ilike(search_term),
                            Filme.titulo_portugues.ilike(search_term)
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
    def obter_elenco(cls,
                     filme: Filme,
                     creditado: bool = True,
                     nao_creditado: bool = True,
                     usar_nome_artistico: bool = True,
                     incluir_atuacao_id: bool = False,
                     session=None) -> list:
        """Retorna lista de atores e personagens do filme.

        Args:
            filme (Filme): Instância do filme
            creditado (bool): Se True, inclui atuações creditadas. Default: True
            nao_creditado (bool): Se True, inclui atuações não creditadas. Default: True
            usar_nome_artistico (bool): Se True, usa o nome artístico do ator se disponível.
                                        Caso contrário, usa o nome real. Default: True
            incluir_atuacao_id (bool): Se True, inclui o ID da atuação. Default: False
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.

        Returns:
            list: Lista de tuplas com estrutura:
                Sem incluir_atuacao_id:
                [
                    ('Christian Bale', 'Batman', True, 21040b96-4794-41a7-9253-f135743ce482),
                        # (nome_ator, personagem, creditado, id_ator)
                    ...
                ]
                Com incluir_atuacao_id:
                [
                    ('Christian Bale', 'Batman', True, 21040b96-4794-41a7-9253-f135743ce482, ac6da361-6ccd-42f6-8ba4-004eeed10784),
                        # (nome_ator, personagem, creditado, id_ator, id_atuacao)
                    ...
                ]
                Ordenada por tempo_de_tela_minutos (decrescente) + ordem alfabética do nome.
                Se um ator interpreta múltiplos personagens, aparece múltiplas vezes.
                Retorna lista vazia se nenhum dos filtros estiver ativo.

        Raises:
            ValueError: Se ambos os filtros forem False

        Examples:
            >>> # Apenas elenco creditado
            >>> FilmeService.obter_elenco(filme,nao_creditado=False)

            >>> # Apenas elenco não creditado
            >>> FilmeService.obter_elenco(filme,creditado=False)

            >>> # Elenco completo
            >>> FilmeService.obter_elenco(filme)
        """
        from app.models.juncoes import Atuacao
        from app.models.pessoa import Ator, Pessoa

        if session is None:
            session = cls._default_session

        # Constrói a query base com joins para acessar o nome do ator
        stmt = (
            select(Atuacao)
            .join(Atuacao.ator)
            .join(Ator.pessoa)
            .where(Atuacao.filme_id == filme.id)
        )

        # Aplica filtros de creditado usando função utilitária
        stmt = aplicar_filtro_creditado(stmt, Atuacao.creditado, creditado, nao_creditado)

        # Ordena por tempo de tela (decrescente) e depois por nome alfabético
        stmt = stmt.order_by(desc(Atuacao.tempo_de_tela_minutos), Pessoa.nome)

        # Executa a query
        resultado = session.execute(stmt).scalars().all()

        # Monta a lista de tuplas (nome_ator, personagem, creditado, id_ator[, id_atuacao])
        if incluir_atuacao_id:
            elenco = [
                (atuacao.ator.nome_artistico if usar_nome_artistico and atuacao.ator.nome_artistico
                 else atuacao.ator.pessoa.nome,
                 atuacao.personagem,
                 atuacao.creditado,
                 atuacao.ator.pessoa.id,
                 atuacao.id)
                for atuacao in resultado
            ]
        else:
            elenco = [
                (atuacao.ator.nome_artistico if usar_nome_artistico and atuacao.ator.nome_artistico
                 else atuacao.ator.pessoa.nome,
                 atuacao.personagem,
                 atuacao.creditado,
                 atuacao.ator.pessoa.id)
                for atuacao in resultado
            ]

        return elenco

    @classmethod
    def obter_equipe_tecnica(cls,
                             filme: Filme,
                             creditado: bool = True,
                             nao_creditado: bool = True,
                             funcoes: list = None,
                             incluir_equipe_id: bool = False,
                             session=None) -> list:
        """Retorna lista de pessoas e funções técnicas da equipe do filme.

        Args:
            filme (Filme): Instância do filme
            creditado (bool): Se True, inclui funções creditadas. Default: True
            nao_creditado (bool): Se True, inclui funções não creditadas. Default: True
            funcoes (list[FuncaoTecnica]): Lista opcional de funções técnicas para filtrar.
                                          Se None, retorna todas as funções. Default: None
            incluir_equipe_id (bool): Se True, inclui o ID da equipe técnica. Default: False
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.

        Returns:
            list: Lista de tuplas com estrutura:
                Sem incluir_equipe_id:
                [
                    ('Diretor', 'Christopher Nolan', True, d3ebd0ba-f5e9-412f-8f4a-4c21e1cd5ff1),
                       # (nome_funcao, nome_pessoa, creditado, id_pessoa)
                    ...
                ]
                Com incluir_equipe_id:
                [
                    ('Diretor', 'Christopher Nolan', True, d3ebd0ba-f5e9-412f-8f4a-4c21e1cd5ff1, equipe_uuid, funcao_uuid),
                       # (nome_funcao, nome_pessoa, creditado, id_pessoa, id_equipe, id_funcao)
                    ...
                ]
                Ordenada por nome da função (alfabética).
                Se uma pessoa tem múltiplas funções, aparece múltiplas vezes.
                Retorna lista vazia se nenhum dos filtros estiver ativo.

        Raises:
            ValueError: Se ambos os filtros forem False

        Examples:
            >>> # Toda a equipe técnica
            >>> FilmeService.obter_equipe_tecnica(filme)

            >>> # Apenas equipe creditada
            >>> FilmeService.obter_equipe_tecnica(filme, nao_creditado=False)

            >>> # Apenas diretores e roteiristas
            >>> diretor = FuncaoTecnica.query.filter_by(nome='Diretor').first()
            >>> roteirista = FuncaoTecnica.query.filter_by(nome='Roteirista').first()
            >>> FilmeService.obter_equipe_tecnica(filme, funcoes=[diretor, roteirista])
        """
        from app.models.juncoes import EquipeTecnica
        from app.models.filme import FuncaoTecnica

        if session is None:
            session = cls._default_session

        # Constrói a query base com joins para acessar nome da pessoa e da função
        stmt = (
            select(EquipeTecnica)
            .join(EquipeTecnica.pessoa)
            .join(EquipeTecnica.funcao_tecnica)
            .where(EquipeTecnica.filme_id == filme.id)
        )

        # Aplica filtros de creditado usando função utilitária
        stmt = aplicar_filtro_creditado(stmt, EquipeTecnica.creditado, creditado, nao_creditado)

        # Aplica filtro de funções específicas, se fornecido
        if funcoes is not None and len(funcoes) > 0:
            funcoes_ids = [funcao.id_pessoa for funcao in funcoes]
            stmt = stmt.where(EquipeTecnica.funcao_tecnica_id.in_(funcoes_ids))

        # Ordena por nome da função (alfabético)
        stmt = stmt.order_by(FuncaoTecnica.nome)

        # Executa a query
        resultado = session.execute(stmt).scalars().all()

        # Monta a lista de tuplas (nome_funcao, nome_pessoa, creditado, id_pessoa[, id_equipe, id_funcao])
        if incluir_equipe_id:
            equipe = [
                (equipe_membro.funcao_tecnica.nome,
                 equipe_membro.pessoa.nome,
                 equipe_membro.creditado,
                 equipe_membro.pessoa.id,
                 equipe_membro.id,
                 equipe_membro.funcao_tecnica.id)
                for equipe_membro in resultado
            ]
        else:
            equipe = [
                (equipe_membro.funcao_tecnica.nome,
                 equipe_membro.pessoa.nome,
                 equipe_membro.creditado,
                 equipe_membro.pessoa.id)
                for equipe_membro in resultado
            ]

        return equipe

    @classmethod
    def _aplicar_atributos_basicos_filme(cls, filme: Filme, form_data: dict) -> None:
        """Aplica atributos básicos do formulário ao filme (antes do flush).

        Args:
            filme: Instância do filme a ser atualizada
            form_data: Dicionário contendo dados do formulário

        Note:
            Este método deve ser chamado ANTES do flush para validação.
            Não inclui associações de gêneros (que requerem ID do filme).
        """
        # Atualiza os atributos básicos
        filme.titulo_original = form_data.get('titulo_original')
        filme.titulo_portugues = form_data.get('titulo_portugues')
        filme.ano_lancamento = form_data.get('ano_lancamento')
        filme.lancado = form_data.get('lancado', False)
        filme.duracao_minutos = form_data.get('duracao_minutos')
        filme.sinopse = form_data.get('sinopse')
        filme.orcamento_milhares = form_data.get('orcamento_milhares')
        filme.faturamento_lancamento_milhares = form_data.get('faturamento_lancamento_milhares')
        filme.trailer_youtube = form_data.get('trailer_youtube')

        # Manipula o upload do poster se fornecido
        poster_file = form_data.get('poster')
        if poster_file:
            filme.poster = poster_file

    @classmethod
    def _aplicar_generos_filme(cls, filme: Filme, form_data: dict, session) -> None:
        """Aplica associações de gêneros ao filme (após o flush).

        Args:
            filme: Instância do filme (deve ter ID)
            form_data: Dicionário contendo dados do formulário
            session: Sessão SQLAlchemy

        Note:
            Este metodo deve ser chamado APÓS o flush, pois requer o ID do filme.
        """
        # Manipula as associações de gêneros
        genero_ids = form_data.get('generos_selecionados', [])
        if genero_ids:
            cls.update_filme_generos(filme, genero_ids, session)

    @classmethod
    def create_filme(cls,
                     form_data: dict,
                     session=None,
                     auto_commit: bool = True) -> FilmeOperationResult:
        """Cria um novo filme com tratamento de transação.

        Args:
            form_data: Dicionário contendo dados do filme do formulário
            session: Sessão SQLAlchemy opcional
            auto_commit: Se deve fazer auto-commit da transação

        Returns:
            FilmeOperationResult: Resultado da operação

        Raises:
            FilmeServiceError: Quando a operação falha
        """
        if session is None:
            session = cls._default_session

        try:
            # Cria uma nova instância de Filme
            filme = Filme()

            # Aplica atributos básicos ANTES do flush (para validação)
            cls._aplicar_atributos_basicos_filme(filme, form_data)

            # Adiciona o filme à sessão e faz flush para obter ID
            session.add(filme)
            session.flush()  # Obtém o ID para as associações de gêneros

            # Aplica gêneros APÓS o flush (requer ID do filme)
            cls._aplicar_generos_filme(filme, form_data, session)

            if auto_commit:
                session.commit()

            return FilmeOperationResult(
                    success=True,
                    message="Filme criado com sucesso",
                    filme=filme
            )

        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro de banco de dados: %s", str(e))
            raise FilmeServiceError from e
        except Exception as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro inesperado: %s", str(e))
            raise FilmeServiceError from e


    @classmethod
    def update_filme(cls,
                     filme_id: uuid.UUID,
                     form_data: dict,
                     session=None,
                     auto_commit: bool = True) -> FilmeOperationResult:
        """Atualiza um filme existente com validação de registro existente.

        Args:
            filme_id: UUID do filme a ser atualizado
            form_data: Dicionário contendo dados atualizados do filme do formulário
            session: Sessão SQLAlchemy opcional
            auto_commit: Se deve fazer auto-commit da transação

        Returns:
            FilmeOperationResult: Resultado da operação

        Raises:
            FilmeServiceError: Quando a operação falha
        """
        if session is None:
            session = cls._default_session

        try:
            # Obtém o filme existente
            try:
                filme = Filme.get_by_id(filme_id,
                                        raise_if_not_found=True)
            except Filme.RecordNotFoundError:
                return FilmeOperationResult(
                        success=False,
                        message="Filme não encontrado"
                )

            # Aplica atributos básicos
            cls._aplicar_atributos_basicos_filme(filme, form_data)

            # Aplica gêneros (filme já tem ID)
            cls._aplicar_generos_filme(filme, form_data, session)

            if auto_commit:
                session.commit()

            return FilmeOperationResult(
                    success=True,
                    message="Filme atualizado com sucesso",
                    filme=filme
            )
        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro de banco de dados: %s", str(e))
            raise FilmeServiceError from e
        except Exception as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro inesperado: %s", str(e))
            raise FilmeServiceError from e

    @classmethod
    def delete_filme(cls,
                     filme_id: uuid.UUID,
                     session=None,
                     auto_commit: bool = True) -> FilmeOperationResult:
        """Exclui um filme com limpeza de relacionamentos.

        Args:
            filme_id: UUID do filme a ser excluído
            session: Sessão SQLAlchemy opcional
            auto_commit: Se deve fazer auto-commit da transação

        Returns:
            FilmeOperationResult: Resultado da operação

        Raises:
            FilmeServiceError: Quando a operação falha
        """
        if session is None:
            session = cls._default_session

        try:
            # Obtém o filme existente
            try:
                filme = Filme.get_by_id(filme_id,
                                        raise_if_not_found=True)
            except Filme.RecordNotFoundError:
                return FilmeOperationResult(
                        success=False,
                        message="Filme não encontrado"
                )

            filme_title = filme.titulo_original

            # Remove o filme da sessão (cascata deve cuidar dos relacionamentos)
            session.delete(filme)

            if auto_commit:
                session.commit()

            return FilmeOperationResult(
                    success=True,
                    message=f"Filme '{filme_title}' excluído com sucesso"
            )

        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro de banco de dados: %s", str(e))
            raise FilmeServiceError from e
        except Exception as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro inesperado: %s", str(e))
            raise FilmeServiceError from e

    @classmethod
    def obter_genero_ids(cls,
                         filme: Filme,
                         session=None) -> list[str]:
        """Retorna lista de IDs de gêneros associados ao filme.

        Args:
            filme: Instância do filme para obter os gêneros
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.

        Returns:
            list[str]: Lista de IDs de gêneros convertidos para string (UUID)

        Raises:
            FilmeServiceError: Quando ocorre erro na operação
        """
        if session is None:
            session = cls._default_session

        try:
            stmt = select(FilmeGenero.genero_id).where(FilmeGenero.filme_id == filme.id)
            genero_ids = [str(genero_id) for genero_id in session.execute(stmt).scalars().all()]
            return genero_ids

        except SQLAlchemyError as e:
            current_app.logger.error("Erro de banco de dados: %s", str(e))
            raise FilmeServiceError from e
        except Exception as e:
            current_app.logger.error("Erro inesperado: %s", str(e))
            raise FilmeServiceError from e

    @classmethod
    def update_filme_generos(cls,
                             filme: Filme,
                             genero_ids: list[uuid.UUID | str],
                             session=None,
                             auto_commit: bool = False) -> None:
        """Gerencia as associações de gêneros de um filme.

        Args:
            filme: Instância do filme para atualizar os gêneros
            genero_ids: Lista de UUIDs de gêneros (como UUID ou string) para associar ao filme
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit: Se deve fazer auto-commit da transação. Default: False

        Raises:
            FilmeServiceError: Quando ocorre erro na operação
        """
        if session is None:
            session = cls._default_session

        try:
            # Remove associações de gêneros existentes
            stmt = select(FilmeGenero).where(FilmeGenero.filme_id == filme.id)
            existing_associations = session.execute(stmt).scalars().all()
            for association in existing_associations:
                session.delete(association)

            # Adiciona novas associações de gêneros
            for genero_id in genero_ids:
                # Converte string para UUID se necessário
                if isinstance(genero_id, str):
                    try:
                        genero_id = uuid.UUID(genero_id)
                    except ValueError:
                        continue  # Skip invalid UUID strings

                # Verifica se o gênero existe antes de associar
                try:
                    genero = Genero.get_by_id(genero_id,
                                              raise_if_not_found=True)
                except Genero.RecordNotFoundError:
                    pass  # Pula o gênero inválido
                else:
                    filme_genero = FilmeGenero(filme_id=filme.id, genero_id=genero_id)
                    session.add(filme_genero)

            if auto_commit:
                session.commit()

        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro de banco de dados: %s", str(e))
            raise FilmeServiceError from e
        except Exception as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro inesperado: %s", str(e))
            raise FilmeServiceError from e
