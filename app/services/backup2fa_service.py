import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import List

from sqlalchemy import delete, insert
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from app.infra.modulos import db
from app.models.autenticacao import Backup2FA, User


class KeepForDays(Enum):
    """Enumeração que define opções para o número de dias para manter dados antes de removê-los fisicamente.
    """
    ZERO = 0
    ONE_WEEK = 7
    TWO_WEEKS = 14
    THREE_WEEKS = 21
    ONE_MONTH = 30
    TWO_MONTHS = 60
    THREE_MONTHS = 90
    SIX_MONTHS = 180
    ONE_YEAR = 365


class Backup2FAService:
    """Serviço responsável pela gestão de códigos de backup 2FA.

    Utiliza uma sessão SQLAlchemy configurável para permitir uso em diferentes contextos,
    como testes ou transações customizadas.
    """

    # Conjunto de caracteres sem ambiguidade visual
    CHARSET = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
    CODIGO_LENGTH = 6

    # Sessão padrão a ser utilizada quando nenhuma sessão é fornecida
    _default_session = db.session

    @classmethod
    def set_default_session(cls, session):
        """Define a sessão padrão a ser utilizada pelo serviço.

        Args:
            session: Sessão SQLAlchemy a ser utilizada como padrão
        """
        cls._default_session = session

    @staticmethod
    def _obter_tokens(usuario: User, unused_only: bool = False) -> List['Backup2FA']:
        """Recupera todos os códigos de backup 2FA do usuário.

        Args:
            usuario (User): Instância do usuário cujos códigos serão listados.
            unused_only (bool): Se True, retorna apenas códigos não utilizados.

        Returns:
            typing.List[Backup2FA]: Lista de códigos de backup 2FA disponíveis.
        """
        query = usuario.codigos_otp
        if unused_only:
            query = query.filter_by(utilizado=False)
        return query.all()

    @staticmethod
    def _gerar_codigo_aleatorio() -> str:
        """Gera um código aleatório usando charset seguro.

        Returns:
            str: Código aleatório gerado.
        """
        return ''.join(
                secrets.choice(Backup2FAService.CHARSET)
                for _ in range(Backup2FAService.CODIGO_LENGTH)
        )

    @staticmethod
    def _invalidar_codigo(backup_code: Backup2FA,
                          keep_for_days: KeepForDays = KeepForDays.ONE_MONTH) -> None:
        """Marca o código como utilizado e define a data de remoção efetiva do banco.

        Args:
            backup_code (Backup2FA): Instância do código de backup a ser invalidado.
            keep_for_days (KeepForDays): Número de dias para manter o código marcado como usado antes de removê-lo fisicamente. Default: 30.

        Returns:
            None
        """
        backup_code.utilizado = True
        backup_code.dta_uso = datetime.now()
        backup_code.dta_para_remocao = datetime.now() + timedelta(days=keep_for_days.value)

    @classmethod
    def consumir_token(cls,
                       usuario: User,
                       token: str,
                       keep_for_days: KeepForDays = KeepForDays.ONE_MONTH,
                       session=None,
                       auto_commit: bool = True) -> bool:
        """Verifica e consome/invalida o token de backup 2FA, marcando-o como utilizado e definindo a data de remoção efetiva do banco.

        Args:
            usuario (User): Instância do usuário ao qual o código pertence.
            token (str): Código de backup 2FA a ser verificado.
            keep_for_days (KeepForDays): Número de dias para manter o código marcado como usado antes de removê-lo fisicamente. Default: 30.
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            bool: True se o código existir e estiver não utilizado, False caso contrário.

        Raises:
            SQLAlchemyError: Em caso de erro na transação (apenas se auto_commit=True).
        """
        if session is None:
            session = cls._default_session

        try:
            # Busca todos os códigos não utilizados do usuário
            codigos_disponiveis = cls._obter_tokens(usuario, unused_only=True)

            # Verifica se o token fornecido corresponde a algum código não utilizado
            for backup_code in codigos_disponiveis:
                if check_password_hash(backup_code.hash_codigo, token):
                    # Código válido encontrado, marca como utilizado
                    cls._invalidar_codigo(backup_code, keep_for_days)
                    if auto_commit:
                        session.commit()
                    return True

            # Token não encontrado ou já utilizado
            return False

        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            raise

    @staticmethod
    def contar_tokens_disponiveis(usuario: User) -> int:
        """Conta a quantidade de códigos de backup 2FA ainda não utilizados do usuário.

        Args:
            usuario (User): Instância do usuário cujo códigos serão contados.

        Returns:
            int: Número de códigos de backup 2FA disponíveis.
        """
        return usuario.codigos_otp.filter_by(utilizado=False).count()

    @classmethod
    def invalidar_codigos(cls,
                          usuario: User,
                          keep_for_days: KeepForDays = KeepForDays.ONE_MONTH,
                          session=None,
                          auto_commit: bool = True) -> int:
        """Marca todos os códigos do usuário como utilizados.

        Args:
            usuario (User): Instância do usuário cujos códigos serão invalidados.
            keep_for_days (KeepForDays): Número de dias para manter o código marcado como usado antes de removê-lo fisicamente. Default: 30.
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            int: Número de códigos marcados como usados.

        Raises:
            SQLAlchemyError: Em caso de erro na transação (apenas se auto_commit=True).
        """
        if session is None:
            session = cls._default_session

        try:
            # Busca todos os códigos não utilizados
            codigos_disponiveis = cls._obter_tokens(usuario, unused_only=True)

            # Marca cada um como inválido
            contador = 0
            for codigo in codigos_disponiveis:
                cls._invalidar_codigo(codigo, keep_for_days)
                contador += 1

            if auto_commit:
                session.commit()

            return contador

        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            raise

    @classmethod
    def gerar_novos_codigos(cls,
                            usuario: User,
                            quantidade: int = 5,
                            session=None,
                            auto_commit: bool = True) -> List[str]:
        """Gera novos códigos de backup, removendo os anteriores não utilizados.

        Args:
            usuario (User): Instância do usuário.
            quantidade (int): Número de códigos a gerar.
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            typing.List[str]: Lista com os códigos em texto plano (para exibir ao usuário).

        Raises:
            SQLAlchemyError: Em caso de erro na transação (apenas se auto_commit=True).
        """
        if session is None:
            session = cls._default_session

        try:
            # Remove todos os códigos não utilizados do usuário
            session.execute(
                    delete(Backup2FA).where(
                            Backup2FA.usuario_id == usuario.id,
                            Backup2FA.utilizado == False
                    )
            )

            # Gera novos códigos
            codigos_texto_plano = []
            registros_para_inserir = []

            for _ in range(quantidade):
                # Gera código aleatório em texto plano
                codigo_plano = cls._gerar_codigo_aleatorio()
                codigos_texto_plano.append(codigo_plano)

                # Prepara registro para inserção em batch
                registros_para_inserir.append({
                    'usuario_id' : usuario.id,
                    'hash_codigo': generate_password_hash(codigo_plano),
                    'utilizado'  : False
                })

            # Insere todos os códigos em batch
            session.execute(insert(Backup2FA), registros_para_inserir)

            if auto_commit:
                session.commit()

            return codigos_texto_plano

        except SQLAlchemyError:
            if auto_commit:
                session.rollback()
            raise

    @classmethod
    def remover_codigos_expirados(cls, session=None, auto_commit: bool = True) -> int:
        """Remove fisicamente do banco todos os códigos que já passaram da data de remoção.

        Idealmente executado por uma tarefa Celery periódica (uma vez ao dia).

        Args:
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            int: Número de códigos removidos.

        Raises:
            SQLAlchemyError: Em caso de erro na transação (apenas se auto_commit=True).
        """
        if session is None:
            session = cls._default_session

        try:
            # Remove códigos onde a data de remoção já passou
            resultado = session.execute(
                    delete(Backup2FA).where(
                            Backup2FA.dta_para_remocao.isnot(None),
                            Backup2FA.dta_para_remocao <= datetime.now()
                    )
            )

            if auto_commit:
                session.commit()

            return resultado.rowcount

        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            raise
