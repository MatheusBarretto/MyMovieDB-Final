"""Serviço de gerenciamento de avaliações de filmes.

Este módulo fornece a camada de serviço para operações relacionadas a avaliações,
incluindo criação, atualização, exclusão e consultas de avaliações.

Classes principais:
    - ReviewService: Serviço principal com métodos para operações de avaliações
"""
from dataclasses import dataclass
from typing import Optional, Tuple, Union
from enum import Enum
from uuid import UUID

from flask import current_app
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.infra.modulos import db
from app.models.juncoes import Avaliacao
from app.models.filme import Filme
from app.models.autenticacao import User


class ReviewOperationResult(Enum):
    """Enum para resultados de operações de avaliação."""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    VALIDATION_ERROR = "validation_error"
    DATABASE_ERROR = "database_error"


@dataclass
class ReviewResult:
    """Resultado de uma operação de avaliação."""
    status: ReviewOperationResult
    message: str
    avaliacao: Optional[Avaliacao] = None
    errors: Optional[dict] = None


class ReviewService:
    """Serviço para operações relacionadas a avaliações de filmes.

    Centraliza a lógica de negócio relacionada a avaliações, separando-a dos modelos e rotas.
    Utiliza uma sessão SQLAlchemy configurável para permitir uso em diferentes contextos.
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
    def obter_avaliacoes_filme(cls,
                               filme: Filme,
                               session=None) -> list[Avaliacao]:
        """Retorna lista de avaliações do filme ordenadas por data de criação.

        Args:
            filme (Filme): Instância do filme
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.

        Returns:
            list[Avaliacao]: Lista de objetos Avaliacao ordenados por created_at (decrescente).
                            Cada avaliação inclui dados do usuário através do relacionamento.
                            Retorna lista vazia se não houver avaliações.

        Examples:
            >>> # Obter todas as avaliações do filme
            >>> ReviewService.obter_avaliacoes_filme(filme)
            [<Avaliacao id=1 nota=8 usuario="João">, <Avaliacao id=2 nota=9 usuario="Maria">]
        """
        if session is None:
            session = cls._default_session

        # Query usando SQLAlchemy 2.x style
        stmt = (
            select(Avaliacao)
            .where(Avaliacao.filme_id == filme.id)
            .order_by(Avaliacao.created_at.desc())
        )
        
        avaliacoes = session.execute(stmt).scalars().all()
        return avaliacoes

    @classmethod
    def obter_avaliacao_usuario(cls,
                                filme: Filme,
                                usuario: User,
                                session=None) -> Optional[Avaliacao]:
        """Retorna a avaliação específica de um usuário para o filme.

        Args:
            filme (Filme): Instância do filme
            usuario (User): Instância do usuário
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.

        Returns:
            Avaliacao or None: Objeto Avaliacao se encontrado, None caso contrário.

        Examples:
            >>> # Obter avaliação do usuário atual
            >>> ReviewService.obter_avaliacao_usuario(filme, current_user)
            <Avaliacao id=1 nota=8 usuario="João">
        """
        if session is None:
            session = cls._default_session

        # Query usando SQLAlchemy 2.x style
        stmt = (
            select(Avaliacao)
            .where(Avaliacao.filme_id == filme.id, Avaliacao.usuario_id == usuario.id)
        )
        
        avaliacao = session.execute(stmt).scalar_one_or_none()
        return avaliacao

    @classmethod
    def criar_ou_atualizar_avaliacao(cls,
                                     filme: Filme,
                                     usuario: User,
                                     nota: int,
                                     comentario: Optional[str] = None,
                                     recomendaria: bool = False,
                                     session=None,
                                     auto_commit: bool = True) -> ReviewResult:
        """Cria uma nova avaliação ou atualiza uma existente.

        Args:
            filme (Filme): Instância do filme
            usuario (User): Instância do usuário
            nota (int): Nota de 0 a 10
            comentario (str, optional): Comentário opcional
            recomendaria (bool): Se o usuário recomendaria o filme
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automático. Padrão True.

        Returns:
            ReviewResult: Resultado da operação com status e mensagem

        Examples:
            >>> # Criar nova avaliação
            >>> result = ReviewService.criar_ou_atualizar_avaliacao(
            ...     filme, user, 8, "Ótimo filme!", True
            ... )
            >>> result.status == ReviewOperationResult.CREATED
            True
        """
        if session is None:
            session = cls._default_session

        # Validar nota
        if not isinstance(nota, int) or nota < 0 or nota > 10:
            return ReviewResult(
                status=ReviewOperationResult.VALIDATION_ERROR,
                message="A nota deve ser um número inteiro entre 0 e 10."
            )

        try:
            # Verificar se já existe avaliação do usuário
            avaliacao_existente = cls.obter_avaliacao_usuario(filme, usuario, session)

            if avaliacao_existente:
                # Atualizar avaliação existente
                avaliacao_existente.nota = nota
                avaliacao_existente.comentario = comentario
                avaliacao_existente.recomendaria = recomendaria

                if auto_commit:
                    session.commit()

                return ReviewResult(
                    status=ReviewOperationResult.UPDATED,
                    message="Avaliação atualizada com sucesso!",
                    avaliacao=avaliacao_existente
                )
            else:
                # Criar nova avaliação
                nova_avaliacao = Avaliacao(filme_id=filme.id,
                                           usuario_id=usuario.id,
                                           nota=nota,
                                           comentario=comentario,
                                           recomendaria=recomendaria)
                session.add(nova_avaliacao)

                if auto_commit:
                    session.commit()

                return ReviewResult(
                    status=ReviewOperationResult.CREATED,
                    message="Avaliação criada com sucesso!",
                    avaliacao=nova_avaliacao
                )

        except IntegrityError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("IntegrityError ao salvar avaliação para filme %s, "
                                     "usuario %s" % (filme.id, usuario.id))
            current_app.logger.error(str(e))
            return ReviewResult(
                status=ReviewOperationResult.DATABASE_ERROR,
                message="Erro interno na aplicação. Tente novamente."
            )
        except Exception as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Exceção ao salvar avaliação para filme %s, "
                                     "usuario %s" % (filme.id, usuario.id))
            current_app.logger.error(str(e))
            return ReviewResult(
                status=ReviewOperationResult.DATABASE_ERROR,
                message="Erro inesperado ao salvar avaliação."
            )

    @classmethod
    def excluir_avaliacao(cls,
                          avaliacao_id,
                          usuario: User,
                          session=None,
                          auto_commit: bool = True) -> ReviewResult:
        """Exclui uma avaliação do usuário.

        Args:
            avaliacao_id: ID da avaliação a ser excluída
            usuario (User): Usuário que está tentando excluir
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automático. Padrão True.

        Returns:
            ReviewResult: Resultado da operação com status e mensagem

        Examples:
            >>> # Excluir avaliação
            >>> result = ReviewService.excluir_avaliacao(avaliacao_id, current_user)
            >>> result.status == ReviewOperationResult.DELETED
            True
        """
        if session is None:
            session = cls._default_session

        try:
            # Buscar a avaliação usando SQLAlchemy 2.x style
            stmt = select(Avaliacao).where(Avaliacao.id == avaliacao_id)
            avaliacao = session.execute(stmt).scalar_one_or_none()

            if not avaliacao:
                return ReviewResult(
                    status=ReviewOperationResult.NOT_FOUND,
                    message="Avaliação não encontrada."
                )

            # Verificar se o usuário é o dono da avaliação
            if avaliacao.usuario_id != usuario.id:
                return ReviewResult(
                    status=ReviewOperationResult.PERMISSION_DENIED,
                    message="Você não tem permissão para excluir esta avaliação."
                )

            # Excluir a avaliação
            session.delete(avaliacao)
            if auto_commit:
                session.commit()

            return ReviewResult(
                status=ReviewOperationResult.DELETED,
                message="Avaliação excluída com sucesso!"
            )

        except Exception as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Exceção ao excluir avaliação %s por usuario %s"
                                     % (avaliacao_id, usuario.id))
            current_app.logger.error(str(e))
            return ReviewResult(
                status=ReviewOperationResult.DATABASE_ERROR,
                message="Erro ao excluir avaliação."
            )

    @classmethod
    def obter_avaliacao_por_id(cls,
                               avaliacao_id: Union[str, UUID],
                               session=None) -> Optional[Avaliacao]:
        """Retorna uma avaliação pelo ID.

        Args:
            avaliacao_id (Union[str, UUID]): ID da avaliação (aceita string ou UUID)
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.

        Returns:
            Avaliacao or None: Objeto Avaliacao se encontrado, None caso contrário.

        Raises:
            ValueError: Se avaliacao_id for uma string inválida de UUID
        """
        if session is None:
            session = cls._default_session

        # Converter string para UUID se necessário
        if isinstance(avaliacao_id, str):
            try:
                avaliacao_id = UUID(avaliacao_id)
            except ValueError:
                current_app.logger.error("ID de avaliação inválido: %s" % avaliacao_id)
                raise ValueError(f"ID de avaliação inválido: {avaliacao_id}")

        # Query usando SQLAlchemy 2.x style
        stmt = select(Avaliacao).where(Avaliacao.id == avaliacao_id)
        return session.execute(stmt).scalar_one_or_none()
