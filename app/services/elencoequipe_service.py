"""Serviço de gerenciamento de elenco e equipe técnica de filmes.

Este módulo fornece a camada de serviço para operações relacionadas ao elenco (atores)
e equipe técnica dos filmes, incluindo adição, edição e remoção de membros.

Classes principais:
    - ElencoEquipeService: Serviço principal com métodos para operações de elenco e equipe técnica
    - ElencoEquipeOperationResult: Resultado das operações CRUD
"""
import uuid
from dataclasses import dataclass
from typing import Optional

from flask import current_app
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.infra.modulos import db
from app.models.filme import Filme, FuncaoTecnica
from app.models.juncoes import Atuacao, EquipeTecnica
from app.models.pessoa import Ator, Pessoa


class ElencoEquipeServiceError(Exception):
    """Exceção customizada para operações do ElencoEquipeService."""
    pass


@dataclass
class ElencoEquipeOperationResult:
    """Objeto de resultado para operações CRUD de elenco e equipe técnica."""
    success: bool
    message: str
    atuacao: Optional[Atuacao] = None
    equipe_tecnica: Optional[EquipeTecnica] = None


class ElencoEquipeService:
    """Serviço para operações relacionadas a elenco e equipe técnica de filmes.

    Centraliza a lógica de negócio relacionada ao gerenciamento de elenco (atores) e
    equipe técnica dos filmes, separando-a dos modelos e rotas.
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
    def adicionar_elenco(cls,
                         filme_id: uuid.UUID,
                         pessoa_id: uuid.UUID,
                         personagem: str,
                         creditado: bool = True,
                         tempo_de_tela_minutos: Optional[int] = None,
                         session=None,
                         auto_commit: bool = True) -> ElencoEquipeOperationResult:
        """Adiciona um ator ao elenco do filme.

        Args:
            filme_id: UUID do filme
            pessoa_id: UUID da pessoa (será criado como ator se necessário)
            personagem: Nome do personagem interpretado
            creditado: Se o ator é creditado no filme (padrão True)
            tempo_de_tela_minutos: Tempo de tela em minutos (opcional)
            session: Sessão SQLAlchemy opcional
            auto_commit: Se deve fazer auto-commit da transação

        Returns:
            ElencoEquipeOperationResult: Resultado da operação

        Raises:
            ElencoEquipeServiceError: Quando a operação falha
        """
        if session is None:
            session = cls._default_session

        try:
            # Validar dados de entrada
            if not personagem or not personagem.strip():
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Nome do personagem é obrigatório",
                )

            if len(personagem.strip()) > 100:
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Nome do personagem não pode exceder 100 caracteres",
                )

            # Verificar se o filme existe
            try:
                filme = Filme.get_by_id(filme_id, raise_if_not_found=True)
            except Filme.RecordNotFoundError:
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Filme não encontrado",
                )

            # Verificar se a pessoa existe
            try:
                pessoa = Pessoa.get_by_id(pessoa_id, raise_if_not_found=True)
            except Pessoa.RecordNotFoundError:
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Pessoa não encontrada",
                )

            # Verificar se a pessoa é um ator, se não for, criar o registro de ator
            stmt = select(Ator).where(Ator.pessoa_id == pessoa_id)
            ator = session.execute(stmt).scalar_one_or_none()
            if not ator:
                # Criar novo registro de ator para esta pessoa
                ator = Ator(pessoa_id=pessoa_id)
                session.add(ator)
                session.flush()  # Para obter o ID do ator antes de continuar

            # Verificar se já existe a combinação filme-ator-personagem
            stmt = (
                select(Atuacao)
                .where(Atuacao.filme_id == filme_id,
                       Atuacao.ator_id == ator.id,
                       Atuacao.personagem == personagem.strip())
            )
            atuacao_existente = session.execute(stmt).scalar_one_or_none()
            if atuacao_existente:
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Esta combinação de ator e personagem já existe para este filme",
                )

            # Criar nova atuação
            nova_atuacao = Atuacao(filme_id=filme_id,
                                   ator_id=ator.id,
                                   personagem=personagem.strip(),
                                   creditado=creditado,
                                   tempo_de_tela_minutos=tempo_de_tela_minutos)
            session.add(nova_atuacao)

            if auto_commit:
                session.commit()

            return ElencoEquipeOperationResult(
                    success=True,
                    message="Ator adicionado ao elenco com sucesso",
                    atuacao=nova_atuacao
            )

        except IntegrityError as e:
            if auto_commit:
                session.rollback()
            return ElencoEquipeOperationResult(
                    success=False,
                    message="Esta combinação de ator e personagem já existe para este filme",
            )
        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro de banco de dados: %s", str(e))
            raise ElencoEquipeServiceError from e
        except Exception as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro inesperado: %s", str(e))
            raise ElencoEquipeServiceError from e

    @classmethod
    def editar_elenco(cls,
                      atuacao_id: uuid.UUID,
                      pessoa_id: uuid.UUID,
                      personagem: str,
                      creditado: bool = True,
                      tempo_de_tela_minutos: Optional[int] = None,
                      session=None,
                      auto_commit: bool = True) -> ElencoEquipeOperationResult:
        """Edita uma atuação existente no elenco do filme.

        Args:
            atuacao_id: UUID da atuação a ser editada
            pessoa_id: UUID da nova pessoa (será criado como ator se necessário)
            personagem: Novo nome do personagem
            creditado: Se o ator é creditado no filme (padrão True)
            tempo_de_tela_minutos: Tempo de tela em minutos (opcional)
            session: Sessão SQLAlchemy opcional
            auto_commit: Se deve fazer auto-commit da transação

        Returns:
            ElencoEquipeOperationResult: Resultado da operação

        Raises:
            ElencoEquipeServiceError: Quando a operação falha
        """
        if session is None:
            session = cls._default_session

        try:
            # Validar dados de entrada
            if not personagem or not personagem.strip():
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Nome do personagem é obrigatório"
                )

            if len(personagem.strip()) > 100:
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Nome do personagem não pode exceder 100 caracteres"
                )

            # Verificar se a atuação existe
            try:
                atuacao = Atuacao.get_by_id(atuacao_id, raise_if_not_found=True)
            except Atuacao.RecordNotFoundError:
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Atuação não encontrada"
                )

            # Verificar se a pessoa existe
            try:
                pessoa = Pessoa.get_by_id(pessoa_id, raise_if_not_found=True)
            except Pessoa.RecordNotFoundError:
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Pessoa não encontrada"
                )

            # Verificar se a pessoa é um ator, se não for, criar o registro de ator
            stmt = select(Ator).where(Ator.pessoa_id == pessoa_id)
            ator = session.execute(stmt).scalar_one_or_none()
            if not ator:
                # Criar novo registro de ator para esta pessoa
                ator = Ator(pessoa_id=pessoa_id)
                session.add(ator)
                session.flush()  # Para obter o ID do ator antes de continuar

            # Verificar se já existe a combinação filme-ator-personagem (exceto a atual)
            stmt = (
                select(Atuacao)
                .where(Atuacao.filme_id == atuacao.filme_id,
                       Atuacao.ator_id == ator.id,
                       Atuacao.personagem == personagem.strip(),
                       Atuacao.id != atuacao_id)
            )
            atuacao_existente = session.execute(stmt).scalar_one_or_none()
            if atuacao_existente:
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Esta combinação de ator e personagem já existe para este filme"
                )

            # Atualizar atuação
            atuacao.ator_id = ator.id
            atuacao.personagem = personagem.strip()
            atuacao.creditado = creditado
            atuacao.tempo_de_tela_minutos = tempo_de_tela_minutos

            if auto_commit:
                session.commit()

            return ElencoEquipeOperationResult(
                    success=True,
                    message="Atuação editada com sucesso",
                    atuacao=atuacao
            )

        except IntegrityError as e:
            if auto_commit:
                session.rollback()
            return ElencoEquipeOperationResult(
                    success=False,
                    message="Esta combinação de ator e personagem já existe para este filme"
            )
        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro de banco de dados: %s", str(e))
            raise ElencoEquipeServiceError from e
        except Exception as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro inesperado: %s", str(e))
            raise ElencoEquipeServiceError from e

    @classmethod
    def remover_elenco(cls,
                       atuacao_id: uuid.UUID,
                       session=None,
                       auto_commit: bool = True) -> ElencoEquipeOperationResult:
        """Remove uma atuação do elenco do filme.

        Args:
            atuacao_id: UUID da atuação a ser removida
            session: Sessão SQLAlchemy opcional
            auto_commit: Se deve fazer auto-commit da transação

        Returns:
            ElencoEquipeOperationResult: Resultado da operação

        Raises:
            ElencoEquipeServiceError: Quando a operação falha
        """
        if session is None:
            session = cls._default_session

        try:
            # Verificar se a atuação existe
            try:
                atuacao: Atuacao = Atuacao.get_by_id(atuacao_id, raise_if_not_found=True)
            except Atuacao.RecordNotFoundError:
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Atuação não encontrada"
                )

            # Guardar informações para a mensagem
            ator_nome = atuacao.ator.nome_artistico if atuacao.ator.nome_artistico else \
                atuacao.ator.pessoa.nome
            personagem = atuacao.personagem

            # Remover atuação
            session.delete(atuacao)

            if auto_commit:
                session.commit()

            return ElencoEquipeOperationResult(
                    success=True,
                    message=f"Ator {ator_nome} ({personagem}) removido do elenco com sucesso"
            )
        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro de banco de dados: %s", str(e))
            raise ElencoEquipeServiceError from e
        except Exception as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro inesperado: %s", str(e))
            raise ElencoEquipeServiceError from e

    @classmethod
    def adicionar_equipe_tecnica(cls,
                                 filme_id: uuid.UUID,
                                 pessoa_id: uuid.UUID,
                                 funcao_tecnica_id: uuid.UUID,
                                 creditado: bool = True,
                                 session=None,
                                 auto_commit: bool = True) -> ElencoEquipeOperationResult:
        """Adiciona uma pessoa à equipe técnica do filme.

        Args:
            filme_id: UUID do filme
            pessoa_id: UUID da pessoa
            funcao_tecnica_id: UUID da função técnica
            creditado: Se a pessoa é creditada no filme (padrão True)
            session: Sessão SQLAlchemy opcional
            auto_commit: Se deve fazer auto-commit da transação

        Returns:
            ElencoEquipeOperationResult: Resultado da operação

        Raises:
            ElencoEquipeServiceError: Quando a operação falha
        """
        if session is None:
            session = cls._default_session

        try:
            # Verificar se o filme existe
            try:
                filme = Filme.get_by_id(filme_id,
                                        raise_if_not_found=True)
            except Filme.RecordNotFoundError:
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Filme não encontrado"
                )

            # Verificar se a pessoa existe
            try:
                pessoa = Pessoa.get_by_id(pessoa_id,
                                          raise_if_not_found=True)
            except Pessoa.RecordNotFoundError:
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Pessoa não encontrada"
                )

            # Verificar se a função técnica existe
            try:
                funcao_tecnica = FuncaoTecnica.get_by_id(funcao_tecnica_id,
                                                         raise_if_not_found=True)
            except FuncaoTecnica.RecordNotFoundError:
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Função técnica não encontrada"
                )

            # Verificar se já existe a combinação filme-pessoa-função
            stmt = (
                select(EquipeTecnica)
                .where(EquipeTecnica.filme_id == filme_id,
                       EquipeTecnica.pessoa_id == pessoa_id,
                       EquipeTecnica.funcao_tecnica_id == funcao_tecnica_id)
            )
            equipe_existente = session.execute(stmt).scalar_one_or_none()
            if equipe_existente:
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Esta combinação de pessoa e função "
                                "técnica já existe para este filme"
                )

            # Criar nova entrada na equipe técnica
            nova_equipe = EquipeTecnica(filme_id=filme_id,
                                        pessoa_id=pessoa_id,
                                        funcao_tecnica_id=funcao_tecnica_id,
                                        creditado=creditado)
            session.add(nova_equipe)

            if auto_commit:
                session.commit()

            return ElencoEquipeOperationResult(
                    success=True,
                    message="Pessoa adicionada à equipe técnica com sucesso",
                    equipe_tecnica=nova_equipe
            )

        except IntegrityError as e:
            if auto_commit:
                session.rollback()
            return ElencoEquipeOperationResult(
                    success=False,
                    message="Esta combinação de pessoa e função técnica já existe para este filme"
            )
        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro de banco de dados: %s", str(e))
            raise ElencoEquipeServiceError from e
        except Exception as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro inesperado: %s", str(e))
            raise ElencoEquipeServiceError from e

    @classmethod
    def editar_equipe_tecnica(cls,
                              equipe_id: uuid.UUID,
                              pessoa_id: uuid.UUID,
                              funcao_tecnica_id: uuid.UUID,
                              creditado: bool = True,
                              session=None,
                              auto_commit: bool = True) -> ElencoEquipeOperationResult:
        """Edita uma entrada existente na equipe técnica do filme.

        Args:
            equipe_id: UUID da entrada na equipe técnica a ser editada
            pessoa_id: UUID da nova pessoa
            funcao_tecnica_id: UUID da nova função técnica
            creditado: Se a pessoa é creditada no filme (padrão True)
            session: Sessão SQLAlchemy opcional
            auto_commit: Se deve fazer auto-commit da transação

        Returns:
            ElencoEquipeOperationResult: Resultado da operação

        Raises:
            ElencoEquipeServiceError: Quando a operação falha
        """
        if session is None:
            session = cls._default_session

        try:
            # Verificar se a entrada na equipe técnica existe
            try:
                equipe_tecnica = EquipeTecnica.get_by_id(equipe_id,
                                                         raise_if_not_found=True)
            except EquipeTecnica.RecordNotFoundError:
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Entrada na equipe técnica não encontrada"
                )

            # Verificar se a pessoa existe
            try:
                pessoa = Pessoa.get_by_id(pessoa_id,
                                          raise_if_not_found=True)
            except Pessoa.RecordNotFoundError:
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Pessoa não encontrada"
                )

            # Verificar se a função técnica existe
            try:
                funcao_tecnica = FuncaoTecnica.get_by_id(funcao_tecnica_id,
                                                         raise_if_not_found=True)
            except FuncaoTecnica.RecordNotFoundError:
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Função técnica não encontrada"
                )

            # Verificar se já existe a combinação filme-pessoa-função (exceto a atual)
            stmt = (
                select(EquipeTecnica)
                .where(EquipeTecnica.filme_id == equipe_tecnica.filme_id,
                       EquipeTecnica.pessoa_id == pessoa_id,
                       EquipeTecnica.funcao_tecnica_id == funcao_tecnica_id,
                       EquipeTecnica.id != equipe_id)
            )
            equipe_existente = session.execute(stmt).scalar_one_or_none()
            if equipe_existente:
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Esta combinação de pessoa e função técnica "
                                "já existe para este filme"
                )

            # Atualizar entrada na equipe técnica
            equipe_tecnica.pessoa_id = pessoa_id
            equipe_tecnica.funcao_tecnica_id = funcao_tecnica_id
            equipe_tecnica.creditado = creditado

            if auto_commit:
                session.commit()

            return ElencoEquipeOperationResult(
                    success=True,
                    message="Entrada na equipe técnica editada com sucesso",
                    equipe_tecnica=equipe_tecnica
            )

        except IntegrityError as e:
            session.rollback()
            return ElencoEquipeOperationResult(
                    success=False,
                    message="Esta combinação de pessoa e função técnica já existe para este filme"
            )
        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro de banco de dados: %s", str(e))
            raise ElencoEquipeServiceError from e
        except Exception as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro inesperado: %s", str(e))
            raise ElencoEquipeServiceError from e

    @classmethod
    def remover_equipe_tecnica(cls,
                               equipe_id: uuid.UUID,
                               session=None,
                               auto_commit: bool = True) -> ElencoEquipeOperationResult:
        """Remove uma entrada da equipe técnica do filme.

        Args:
            equipe_id: UUID da entrada na equipe técnica a ser removida
            session: Sessão SQLAlchemy opcional
            auto_commit: Se deve fazer auto-commit da transação

        Returns:
            ElencoEquipeOperationResult: Resultado da operação

        Raises:
            ElencoEquipeServiceError: Quando a operação falha
        """
        if session is None:
            session = cls._default_session

        try:
            # Verificar se a entrada na equipe técnica existe
            try:
                equipe_tecnica: EquipeTecnica = EquipeTecnica.get_by_id(equipe_id,
                                                         raise_if_not_found=True)
            except EquipeTecnica.RecordNotFoundError:
                return ElencoEquipeOperationResult(
                        success=False,
                        message="Entrada na equipe técnica não encontrada"
                )

            # Guardar informações para a mensagem
            pessoa_nome = equipe_tecnica.pessoa.nome
            funcao_nome = equipe_tecnica.funcao_tecnica.nome

            # Remover entrada da equipe técnica
            session.delete(equipe_tecnica)

            if auto_commit:
                session.commit()

            return ElencoEquipeOperationResult(
                    success=True,
                    message=f"{pessoa_nome} ({funcao_nome}) removido da equipe técnica com sucesso"
            )
        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro de banco de dados: %s", str(e))
            raise ElencoEquipeServiceError from e
        except Exception as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro inesperado: %s", str(e))
            raise ElencoEquipeServiceError from e
