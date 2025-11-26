"""Serviço genérico para operações CRUD em classes de suporte.

Este módulo fornece funcionalidades genéricas para listagem, paginação e
filtros que podem ser reutilizadas em diferentes modelos de suporte.
"""
from typing import Optional, Type, TypeVar

from flask import current_app
from sqlalchemy.orm import DeclarativeBase
from werkzeug.exceptions import NotFound

from app.infra.modulos import db

# Type variable para representar qualquer modelo SQLAlchemy
ModelType = TypeVar('ModelType', bound=DeclarativeBase)


class CrudService:
    """Serviço genérico para operações CRUD em modelos de suporte.

    Fornece métodos reutilizáveis para operações comuns como listagem com
    paginação, filtros de busca e filtros de status ativo/inativo.
    """

    @staticmethod
    def listar_com_paginacao(
            model_class: Type[ModelType],
            page: int = 1,
            per_page: int = 50,
            search_field: Optional[str] = None,
            search_query: Optional[str] = None,
            active_filter: int = 0,
            order_by_field: Optional[str] = None,
            max_per_page: Optional[int] = None
    ) -> tuple[object, bool]:
        """Lista registros com paginação e filtros aplicados.

        Args:
            model_class: Classe do modelo SQLAlchemy a ser consultado
            page: Número da página desejada (padrão: 1)
            per_page: Quantidade de itens por página (padrão: 50)
            search_field: Nome do campo para aplicar filtro de busca parcial
            search_query: Texto a ser buscado no campo especificado
            active_filter: Filtro de status (0=todos, 1=ativos, 2=inativos)
            order_by_field: Nome do campo para ordenação (padrão: usa search_field)
            max_per_page: Limite máximo de itens por página (padrão: MAX_PER_PAGE do config)

        Returns:
            tuple: (resultado paginado, flag indicando se houve redirecionamento para página 1)

        Raises:
            AttributeError: Se search_field ou order_by_field não existirem no modelo
        """
        # Determina o limite máximo de itens por página
        if max_per_page is None:
            max_per_page = int(current_app.config.get('MAX_PER_PAGE', 500))

        # Aplica o limite máximo
        if per_page > max_per_page:
            per_page = max_per_page

        # Monta a query base
        query = db.select(model_class)

        # Aplica filtro de busca parcial (case-insensitive)
        if search_query and search_field:
            field = getattr(model_class, search_field)
            query = query.filter(field.ilike(f"%{search_query}%"))

        # Aplica filtro ativo/inativo (se o modelo tiver o campo 'ativo')
        if hasattr(model_class, 'ativo'):
            match active_filter:
                case 1:
                    query = query.filter_by(ativo=True)
                case 2:
                    query = query.filter_by(ativo=False)
                case _:
                    pass  # Não aplica filtro (mostra todos)

        # Aplica ordenação
        if order_by_field:
            field = getattr(model_class, order_by_field)
        elif search_field:
            field = getattr(model_class, search_field)
        else:
            # Se não especificou ordenação, tenta usar 'nome' ou 'id'
            if hasattr(model_class, 'nome'):
                field = model_class.nome
            else:
                field = model_class.id

        query = query.order_by(field)

        # Executa a paginação
        redirected = False
        try:
            result = db.paginate(
                query,
                page=page,
                per_page=per_page,
                max_per_page=max_per_page,
                error_out=True
            )
        except NotFound as e:
            # Se a página solicitada não existe, redireciona para a primeira
            current_app.logger.warning(f"Página {page} não encontrada: {e}")
            result = db.paginate(
                query,
                page=1,
                per_page=per_page,
                max_per_page=max_per_page,
                error_out=True
            )
            redirected = True

        return result, redirected
