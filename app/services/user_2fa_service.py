from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Union

import pyotp
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.infra.modulos import db
from app.models.autenticacao import User
from .backup2fa_service import Backup2FAService
from .token_service import JWT_action, JWTService


class Autenticacao2FA(Enum):
    """ Enumeração que define os resultados possíveis da autenticação de dois fatores."""
    ENABLED = 0
    NOT_ENABLED = 1
    ENABLING = 2
    ALREADY_ENABLED = 3
    DISABLED = 4
    INVALID_CODE = 5
    REUSED = 6
    TOTP = 7
    BACKUP = 8
    MISSING_TOKEN = 9
    INVALID_TOKEN = 10
    WRONG_USER = 11
    UNKNOWN = 99


@dataclass
class TwoFASetupResult:
    """Dados da configuração do 2FA."""
    status: Autenticacao2FA = Autenticacao2FA.UNKNOWN
    secret: str | None = None
    qr_code_base64: str | None = None
    backup_codes: list[str] | None = None
    token: str | None = None
    user_id: str | None = None


@dataclass
class TwoFAValidationResult:
    """Resultado da validação de código 2FA."""
    success: bool
    method_used: Optional[Autenticacao2FA]
    error_message: Optional[str]
    remaining_backup_codes: Optional[int]
    security_warnings: List[str]


class User2FAError(Exception):
    pass


class User2FAService:
    """Serviço principal para gestão completa de 2FA de usuários.

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

    @staticmethod
    def iniciar_ativacao_2fa(usuario: User) -> Optional[TwoFASetupResult]:
        """Inicia o processo de configuração do 2FA para um usuário.

        IMPORTANTE: O secret TOTP é salvo temporariamente no banco de dados (criptografado)
        durante o processo de ativação. Ele NÃO é incluído no token JWT por segurança,
        pois tokens JWT são apenas codificados (não criptografados) e podem ser decodificados
        por qualquer um.

        Args:
            usuario (User): Instância do usuário

        Returns:
            typing.Optional[TwoFASetupResult]: Dados necessários para completar a configuração

        Raises:
            User2FAError: Em caso de erro na configuração
            ValueError: Para parâmetros inválidos
        """

        if usuario is None:
            raise ValueError("Parâmetro 'usuario' não pode ser None")

        if usuario.usa_2fa:
            return TwoFASetupResult(status=Autenticacao2FA.ALREADY_ENABLED)

        try:
            # Gera novo segredo TOTP
            secret = pyotp.random_base32()

            # Salva secret TEMPORARIAMENTE no banco (criptografado via EncryptedType)
            # Isso evita que o secret trafegue em plaintext no token JWT
            usuario.otp_secret = secret
            usuario.usa_2fa = False  # Ainda não ativado (apenas preparando)

            db.session.commit()

            # Token JWT SEM O SECRET (apenas indica que está em processo de ativação)
            # O secret será recuperado do banco durante a validação
            # O QR code será gerado on-demand na rota ativar_2fa()
            token = JWTService.create(action=JWT_action.ACTIVATING_2FA,
                                      sub=usuario.id,
                                      expires_in=current_app.config.get('2FA_SESSION_TIMEOUT', 90))

            current_app.logger.debug(
                    "Iniciado processo de ativação 2FA para %s (secret salvo no banco, "
                    "não no token)" % (usuario.email,))

            return TwoFASetupResult(
                    status=Autenticacao2FA.ENABLING,
                    token=token)

        except SQLAlchemyError as e:
            db.session.rollback()
            raise User2FAError(f"Erro ao iniciar ativação 2FA: {str(e)}") from e

    @classmethod
    def confirmar_ativacao_2fa(cls,
                               usuario: User,
                               secret: str,
                               codigo_confirmacao: str,
                               gerar_backup_codes: bool = True,
                               quantidade_backup: int = 10,
                               session=None,
                               auto_commit: bool = True) -> TwoFASetupResult:
        """Confirma a ativação do 2FA para o usuário, validando o código TOTP.

        Args:
            usuario (User): Instância do usuário
            secret (str): Segredo TOTP gerado
            codigo_confirmacao (str): Código TOTP fornecido pelo usuário
            gerar_backup_codes (bool): Se deve gerar códigos de backup. (Default: True)
            quantidade_backup (int): Quantidade de códigos de backup (mínimo 0, máximo 20).
                (Default: 10)
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            TwoFASetupResult: Resultado da ativação, incluindo códigos de backup se gerados
        """
        if session is None:
            session = cls._default_session

        try:
            if usuario.usa_2fa:
                return TwoFASetupResult(status=Autenticacao2FA.ALREADY_ENABLED)

            totp = pyotp.TOTP(secret)
            if not totp.verify(codigo_confirmacao, valid_window=1):
                return TwoFASetupResult(status=Autenticacao2FA.INVALID_CODE)

            # Código válido, ativa 2FA
            usuario.usa_2fa = True
            usuario.otp_secret = secret
            usuario.ultimo_otp = codigo_confirmacao

            backup_codes = None
            if gerar_backup_codes:
                quantidade_backup = max(0, min(quantidade_backup, 20))
                backup_codes = Backup2FAService.\
                    gerar_novos_codigos(usuario,
                                        quantidade_backup,
                                        session=session,
                                        auto_commit=False)
                current_app.logger.debug(
                        "Gerados %d códigos de reserva para usuário %s." % (quantidade_backup,
                                                                            usuario.email,))

            if auto_commit:
                session.commit()
                current_app.logger.info("Ativado 2FA para usuário %s." % (usuario.email,))
            else:
                current_app.logger.debug(
                        "2FA marcado para ativação (sem commit) para "
                        "usuário %s." % (usuario.email,))

            return TwoFASetupResult(status=Autenticacao2FA.ENABLED,
                                    backup_codes=backup_codes)
        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            raise User2FAError(f"Erro de banco de dados ao ativar 2FA: {str(e)}") from e
        except Exception as e:
            if auto_commit:
                session.rollback()
            raise User2FAError(f"Erro ao ativar 2FA: {str(e)}") from e

    @classmethod
    def desativar_2fa(cls,
                      usuario: User,
                      session=None,
                      auto_commit: bool = True) -> TwoFASetupResult:
        """Desativa o 2FA para o usuário, removendo segredos e códigos de backup.

        Args:
            usuario (User): Instância do usuário
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            TwoFASetupResult: Resultado da desativação
        """
        if session is None:
            session = cls._default_session

        try:
            if not usuario.usa_2fa:
                return TwoFASetupResult(status=Autenticacao2FA.NOT_ENABLED)

            # Desativa 2FA
            codigos_invalidados = Backup2FAService.invalidar_codigos(usuario,
                                                                     session=session,
                                                                     auto_commit=False)
            usuario.usa_2fa = False
            usuario.otp_secret = None
            usuario.ultimo_otp = None

            if auto_commit:
                session.commit()
                current_app.logger.warning("Desativado 2FA para usuário %s." % (usuario.email,))
                current_app.logger.warning(
                    "Códigos de backup invalidados: %d" % (codigos_invalidados,))
            else:
                current_app.logger.debug(
                        "2FA marcado para desativação (sem commit) "
                        "para usuário %s." % (usuario.email,))

            return TwoFASetupResult(status=Autenticacao2FA.DISABLED)

        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            raise User2FAError(f"Erro de banco de dados ao desativar 2FA: {str(e)}") from e
        except Exception as e:
            if auto_commit:
                session.rollback()
            raise User2FAError(f"Erro ao desativar 2FA: {str(e)}") from e

    @classmethod
    def validar_codigo_2fa(cls,
                           usuario: User,
                           codigo: str,
                           session=None,
                           auto_commit: bool = True) -> TwoFAValidationResult:
        """Valida um código 2FA (TOTP ou backup) para o usuário.

        Args:
            usuario (User): Instância do usuário
            codigo (str): Código 2FA fornecido
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            TwoFAValidationResult: Resultado da validação, incluindo metodo usado e mensagens de
            erro
        """
        if session is None:
            session = cls._default_session

        warnings = []

        try:
            # Confirma se 2FA está habilitado
            if not usuario.usa_2fa or not usuario.otp_secret:
                current_app.logger.warning(
                        "Tentativa de uso de 2FA por usuário sem 2FA ativado (%s)." % (
                            usuario.email,))
                return TwoFAValidationResult(
                        success=False,
                        method_used=Autenticacao2FA.NOT_ENABLED,
                        error_message="2FA não está habilitado para este usuário.",
                        remaining_backup_codes=None,
                        security_warnings=warnings)

            # Verifica se o código já foi usado recentemente
            if codigo == usuario.ultimo_otp:
                current_app.logger.warning(
                        "Tentativa de uso de código 2FA repetido pelo usuário %s." % (
                            usuario.email,))
                warnings.append("Atenção: Este código já foi utilizado recentemente.")
                return TwoFAValidationResult(
                        success=False,
                        method_used=Autenticacao2FA.REUSED,
                        error_message="Código 2FA já foi utilizado recentemente.",
                        remaining_backup_codes=None,
                        security_warnings=warnings)

            # Tenta TOTP primeiro
            totp = pyotp.TOTP(usuario.otp_secret)
            if totp.verify(codigo, valid_window=1):
                current_app.logger.debug("Código 2FA validado para usuário %s." % (usuario.email,))
                usuario.ultimo_otp = codigo

                if auto_commit:
                    session.commit()
                else:
                    current_app.logger.debug(
                            "Código 2FA validado (sem commit) para usuário %s." % (usuario.email,))

                # Verifica status dos códigos de backup
                backup_count = Backup2FAService.contar_tokens_disponiveis(usuario)
                current_app.logger.debug(
                        "Códigos 2FA reservas disponíveis para %s: %d." % (usuario.email,
                                                                           backup_count))
                if backup_count == 0:
                    warnings.append("CRÍTICO: Nenhum código reserva restante")
                elif backup_count <= 2:
                    warnings.append(
                            f"ATENÇÃO: Apenas {backup_count} código(s) reserva restante(s)")

                return TwoFAValidationResult(
                        success=True,
                        method_used=Autenticacao2FA.TOTP,
                        error_message=None,
                        remaining_backup_codes=backup_count,
                        security_warnings=warnings
                )

            # Tenta código de backup
            if Backup2FAService.consumir_token(usuario,
                                               codigo,
                                               session=session,
                                               auto_commit=auto_commit):
                backup_count = Backup2FAService.contar_tokens_disponiveis(usuario)
                current_app.logger.debug(
                        "Código 2FA reserva validado para usuário %s." % (usuario.email,))
                current_app.logger.debug(
                        "Códigos 2FA reservas disponíveis para %s: %d." % (usuario.email,
                                                                           backup_count))
                warnings.append("Código reserva utilizado")
                if backup_count == 0:
                    warnings.append("CRÍTICO: Nenhum código reserva restante")
                elif backup_count <= 2:
                    warnings.append(
                            f"ATENÇÃO: Apenas {backup_count} código(s) reserva restante(s)")

                return TwoFAValidationResult(
                        success=True,
                        method_used=Autenticacao2FA.BACKUP,
                        error_message=None,
                        remaining_backup_codes=backup_count,
                        security_warnings=warnings
                )

            # Codigo inválido
            current_app.logger.warning("Código 2FA inválido para usuário %s." % (usuario.email,))
            return TwoFAValidationResult(
                    success=False,
                    method_used=Autenticacao2FA.INVALID_CODE,
                    error_message="Código 2FA inválido.",
                    remaining_backup_codes=None,
                    security_warnings=warnings)
        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            return TwoFAValidationResult(
                    success=False,
                    method_used=Autenticacao2FA.UNKNOWN,
                    error_message=f"Erro ao validar código 2FA: {str(e)}",
                    remaining_backup_codes=None,
                    security_warnings=warnings)
        except Exception as e:
            current_app.logger.error("Erro na validação 2FA para %s: %s" % (usuario.email, str(e),))
            return TwoFAValidationResult(
                    success=False,
                    method_used=Autenticacao2FA.UNKNOWN,
                    error_message=f"Erro ao validar código 2FA: {str(e)}",
                    remaining_backup_codes=None,
                    security_warnings=warnings)

    @staticmethod
    def otp_secret_formatted(value: Union[User, str]) -> Optional[str]:
        """Obtém o segredo OTP formatado para exibição.

        Args:
            value (Union[User, str]): Instância do usuário ou string do segredo OTP

        Returns:
            typing.Optional[str]: Segredo OTP formatado ou None se não disponível

        Raises:
            ValueError: Se o parâmetro 'value' for inválido
        """
        if isinstance(value, str):
            secret = value
        elif isinstance(value, User):
            secret = value.otp_secret
        else:
            raise ValueError("Parâmetro 'value' deve ser uma instância de User ou str")
        if not secret:
            return None
        # Formata em grupos de 4 caracteres
        return ' '.join(secret[i:i + 4] for i in range(0, len(secret), 4))

    @staticmethod
    def validar_token_ativacao_2fa(usuario: User,
                                   token_sessao: str) -> TwoFASetupResult:
        """Valida o token de ativação 2FA da sessão e recupera os dados do banco.

        IMPORTANTE: O secret TOTP é recuperado do banco de dados (onde está criptografado),
        NÃO do token JWT. O token apenas confirma que o usuário iniciou o processo de ativação.

        Args:
            usuario (User): Instância do usuário atual
            token_sessao (str): Token JWT da sessão ('activating_2fa_token')

        Returns:
            TwoFASetupResult: Resultado da validação com secret do banco e status
        """
        if not token_sessao:
            current_app.logger.warning(
                    "Tentativa de ativação 2FA sem token de sessão para usuário %s" % (
                        usuario.email,))
            return TwoFASetupResult(status=Autenticacao2FA.MISSING_TOKEN)

        # Verifica o token JWT
        resultado_token = JWTService.verify(token_sessao)
        if not resultado_token.valid:
            current_app.logger.warning(
                    "Token de ativação 2FA inválido para usuário %s" % (usuario.email,))
            return TwoFASetupResult(status=Autenticacao2FA.INVALID_TOKEN)

        # Valida a ação do token
        if resultado_token.action != JWT_action.ACTIVATING_2FA:
            current_app.logger.warning(
                    "Token com ação inválida para ativação 2FA: %s" % (resultado_token.action,))
            return TwoFASetupResult(status=Autenticacao2FA.INVALID_TOKEN)

        # Extrai user_id do token
        user_id = resultado_token.sub

        # Valida se o token é para o usuário correto
        if str(usuario.id) != str(user_id):
            current_app.logger.warning(
                    "Tentativa de uso de token 2FA de outro usuário por %s" % (usuario.email,))
            return TwoFASetupResult(status=Autenticacao2FA.WRONG_USER)

        # Busca o secret TEMPORÁRIO do banco de dados (salvo durante iniciar_ativacao_2fa)
        # O secret está criptografado via EncryptedType
        tentative_otp = usuario.otp_secret

        # Valida se existe um secret no banco (usuário deve ter iniciado a ativação)
        if not tentative_otp:
            current_app.logger.warning(
                    "Usuário %s não possui secret temporário no banco durante ativação 2FA" % (
                        usuario.email,))
            return TwoFASetupResult(status=Autenticacao2FA.INVALID_TOKEN)

        # Valida se o usuário ainda não ativou o 2FA
        # (se usa_2fa=True, significa que já concluiu a ativação)
        if usuario.usa_2fa:
            current_app.logger.warning(
                    "Usuário %s tentou revalidar token mas 2FA já está ativo" % (usuario.email,))
            return TwoFASetupResult(status=Autenticacao2FA.ALREADY_ENABLED)

        current_app.logger.debug(
                "Token de ativação 2FA validado com sucesso para usuário %s (secret recuperado do "
                "banco)" % (usuario.email,))

        # Retorna o secret do banco para uso na confirmação
        # O QR code não é retornado aqui pois deve ser regenerado na rota se necessário
        return TwoFASetupResult(
                status=Autenticacao2FA.ENABLING,
                secret=tentative_otp,
                user_id=user_id
        )
