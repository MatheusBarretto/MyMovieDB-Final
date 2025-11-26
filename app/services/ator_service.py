"""Serviço de gerenciamento de atores.

Este módulo fornece a camada de serviço para operações relacionadas a atores,
incluindo consulta de papéis, filmografia, e outras operações de negócio.

Classes principais:
    - AtorService: Serviço principal com métodos para operações de atores
"""
from collections import defaultdict

from sqlalchemy import desc, select

from app.infra.modulos import db
from app.models.pessoa import Ator
from .utils import aplicar_filtro_creditado


class AtorService:
    """Serviço para operações relacionadas a atores.

    Centraliza a lógica de negócio relacionada a atores, separando-a dos modelos.
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
    def obter_papeis(cls,
                     ator: Ator,
                     creditado: bool = True,
                     nao_creditado: bool = True,
                     year_reverse: bool = True,
                     session=None) -> list:
        """Retorna lista de filmes e personagens interpretados pelo ator.

        Args:
            ator (Ator): Instância do ator
            creditado (bool): Se True, inclui papéis creditados. Default: True
            nao_creditado (bool): Se True, inclui papéis não creditados. Default: True
            year_reverse (bool): Se True, ordena do filme mais recente para o mais antigo.
            Default: True
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.

        Returns:
            list: Lista de dicionários com estrutura:
                [
                    {
                        'filme': Filme,
                        'personagens': [
                            ('Personagem 1', True),   # (nome, creditado)
                            ('Personagem 2', False)
                        ]
                    },
                    ...
                ]
                Retorna lista vazia se nenhum dos filtros estiver ativo.
                A lista é ordenada por ano de lançamento do filme.

        Raises:
            ValueError: Se ambos os filtros forem False

        Examples:
            >>> # Apenas papéis creditados
            >>> AtorService.obter_papeis(ator, nao_creditado=False)

            >>> # Apenas papéis não creditados
            >>> AtorService.obter_papeis(ator, creditado=False)

            >>> # Todos os papéis
            >>> AtorService.obter_papeis(ator)
        """
        from app.models.juncoes import Atuacao
        from app.models.filme import Filme

        if session is None:
            session = cls._default_session

        # Constrói a query base com join no Filme para ordenação
        stmt = (
            select(Atuacao)
            .join(Filme, Atuacao.filme_id == Filme.id)
            .where(Atuacao.ator_id == ator.id)
        )
        if year_reverse:
            stmt = stmt.order_by(desc(Filme.ano_lancamento))
        else:
            stmt = stmt.order_by(Filme.ano_lancamento)

        # Aplica filtros de creditado usando função utilitária
        stmt = aplicar_filtro_creditado(stmt, Atuacao.creditado, creditado, nao_creditado)

        # Executa a query
        resultado = session.execute(stmt).scalars().all()

        # Agrupa personagens por filme
        filmes_personagens = defaultdict(list)
        filmes_obj = {}  # Guarda referência aos objetos Filme

        for atuacao in resultado:
            filme_id = atuacao.filme_id
            # Adiciona tupla (nome_personagem, creditado)
            filmes_personagens[filme_id].append((atuacao.personagem, atuacao.creditado))
            if filme_id not in filmes_obj:
                filmes_obj[filme_id] = atuacao.filme

        # Monta a lista de retorno mantendo a ordem do resultado
        papeis = []
        filmes_adicionados = set()
        for atuacao in resultado:
            if atuacao.filme_id not in filmes_adicionados:
                papeis.append({
                    'filme'      : atuacao.filme,
                    'personagens': filmes_personagens[atuacao.filme_id]
                })
                filmes_adicionados.add(atuacao.filme_id)

        return papeis
