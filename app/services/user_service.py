"""Serviço de gerenciamento de usuários.

Este módulo fornece a camada de serviço para todas as operações relacionadas a usuários,
incluindo registro, autenticação, ativação de conta, reset de senha, e gerenciamento de perfil.

Classes principais:
    - UserService: Serviço principal com métodos para operações de usuário
    - UserOperationStatus: Enum com status de resultados de operações
    - UserServiceResult: Dataclass com resultado de operações de usuário
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from flask import current_app, render_template, url_for
from flask_login import login_user, logout_user
from sqlalchemy.exc import SQLAlchemyError

from app.infra.modulos import db
from app.models.autenticacao import User
from .email_service import EmailValidationService
from .token_service import JWT_action, JWTService


class UserOperationStatus(Enum):
    """Status das operações de usuário."""
    SUCCESS = 0
    USER_NOT_FOUND = 1
    USER_ALREADY_ACTIVE = 2
    USER_INACTIVE = 3
    INVALID_TOKEN = 4
    TOKEN_EXPIRED = 5
    INVALID_UUID = 6
    SEND_EMAIL_ERROR = 7
    DATABASE_ERROR = 8
    INVALID_CREDENTIALS = 9
    UNKNOWN = 99


@dataclass
class UserServiceResult:
    """Resultado unificado de operações do serviço de usuários.

    Esta classe é usada como retorno para todas as operações do UserService,
    incluindo registro, ativação, reset de senha, e atualização de perfil.
    """
    status: UserOperationStatus  # Status da operação (SUCCESS, DATABASE_ERROR, etc.)
    user: Optional[User] = None  # Instância do usuário (se disponível)
    error_message: Optional[str] = None  # Mensagem de erro detalhada (se falha)
    token: Optional[str] = None  # Token JWT (usado em registro e reset de senha)
    email_sent: bool = False  # Indica se email foi enviado com sucesso (usado em registro)
    extra_data: Optional[dict] = None  # Dados adicionais (se necessário)


class UserService:
    """Serviço para operações relacionadas a usuários.

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
    def registrar_usuario(cls,
                          nome: str,
                          email: str,
                          password: str,
                          email_service,
                          session=None,
                          auto_commit: bool = True) -> UserServiceResult:
        """Registra um novo usuário no sistema.

        Args:
            nome (str): Nome completo do usuário
            email (str): Email do usuário (será normalizado)
            password (str): Senha em texto plano (será hasheada)
            email_service (EmailService): Instância do serviço de email
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            UserServiceResult: Resultado da operação com usuário e token
        """
        if session is None:
            session = cls._default_session

        try:
            # Cria o usuário
            usuario = User()
            usuario.nome = nome
            usuario.email = email  # Será normalizado pelo setter
            usuario.ativo = False
            usuario.password = password  # Será hasheado pelo setter

            session.add(usuario)
            session.flush()
            session.refresh(usuario)

            # Gera token e envia email de confirmação
            token, email_sent = UserService._enviar_email_ativacao(usuario, email_service)

            if auto_commit:
                session.commit()
                current_app.logger.info("Usuário registrado: %s" % (usuario.email,))
            else:
                current_app.logger.debug(
                        "Usuário marcado para registro (sem commit): %s" % (usuario.email,))

            return UserServiceResult(
                    status=UserOperationStatus.SUCCESS,
                    user=usuario,
                    token=token,
                    email_sent=email_sent
            )

        except ValueError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro ao registrar usuário: %s" % (str(e),))
            return UserServiceResult(
                    status=UserOperationStatus.UNKNOWN,
                    error_message=str(e)
            )
        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro de banco de dados ao registrar usuário: %s" % (str(e),))
            return UserServiceResult(
                    status=UserOperationStatus.DATABASE_ERROR,
                    error_message=str(e)
            )

    @staticmethod
    def reativar_usuario(user_id: UUID, email_service) -> UserServiceResult:
        """Reenvia o email de validação para um usuário inativo.

        Args:
            user_id (uuid.UUID): UUID do usuário
            email_service (EmailService): Instância do serviço de email

        Returns:
            EmailValidationResult: Resultado da operação
        """
        try:
            uuid_obj = UUID(str(user_id))
        except (ValueError, TypeError):
            current_app.logger.warning("UUID inválido fornecido: %s" % (user_id,))
            return UserServiceResult(
                    status=UserOperationStatus.INVALID_CREDENTIALS,
                    error_message="ID de usuário inválido"
            )

        try:
            usuario = User.get_by_id(uuid_obj,
                                     raise_if_not_found=True)
        except User.RecordNotFoundError:
            current_app.logger.warning(
                    "Tentativa de reenvio de email para usuário inexistente: %s" % (user_id,))
            return UserServiceResult(
                    status=UserOperationStatus.USER_NOT_FOUND,
                    error_message="Usuário inexistente"
            )

        if usuario.ativo:
            current_app.logger.info("Usuário %s já está ativo" % (usuario.email,))
            return UserServiceResult(
                    status=UserOperationStatus.USER_ALREADY_ACTIVE,
                    user=usuario,
                    error_message="Usuário já está ativo"
            )

        # Gera token e envia email de confirmação
        token, email_sent = UserService._enviar_email_ativacao(usuario, email_service)

        if not email_sent:
            return UserServiceResult(
                    status=UserOperationStatus.SEND_EMAIL_ERROR,
                    user=usuario,
                    token=token,
                    email_sent=False,
                    error_message="Erro no envio do email"
            )

        current_app.logger.info("Email de reativação enviado para %s" % (usuario.email,))
        return UserServiceResult(
                status=UserOperationStatus.SUCCESS,
                user=usuario,
                token=token,
                email_sent=True
        )

    @classmethod
    def ativar_conta(cls,
                     usuario: User,
                     session=None,
                     auto_commit: bool = True) -> bool:
        """Confirma o email do usuário, ativando sua conta.

        Args:
            usuario (User): Instância do usuário
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            bool: True se a operação foi bem-sucedida

        Raises:
            SQLAlchemyError: Em caso de erro na transação (apenas se auto_commit=True)
        """
        if session is None:
            session = cls._default_session

        try:
            if usuario.ativo:
                current_app.logger.warning(
                        "Tentativa de ativar conta já ativa: %s" % (usuario.email,))
                return True  # Já está confirmado, não é erro

            usuario.ativo = True
            usuario.dta_validacao_email = datetime.now()

            if auto_commit:
                session.commit()
                current_app.logger.info("Conta ativada para usuário: %s" % (usuario.email,))
            else:
                current_app.logger.debug(
                        "Conta marcada para ativação (sem commit): %s" % (usuario.email,))

            return True

        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error(
                    "Erro ao ativar conta do usuário %s: %s" % (usuario.email, str(e)))
            raise e

    @classmethod
    def desativar_conta(cls,
                        usuario: User,
                        session=None,
                        auto_commit: bool = True) -> bool:
        """Desconfirma o email do usuário, inativando sua conta.

        Args:
            usuario (User): Instância do usuário
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            bool: True se a operação foi bem-sucedida

        Raises:
            SQLAlchemyError: Em caso de erro na transação (apenas se auto_commit=True)
        """
        if session is None:
            session = cls._default_session

        try:
            if not usuario.ativo:
                current_app.logger.warning(
                        "Tentativa de desativar conta inativa: %s" % (usuario.email,))
                return True  # Não está confirmado, não é erro

            usuario.ativo = False
            usuario.dta_validacao_email = None

            if auto_commit:
                session.commit()
                current_app.logger.info("Conta desativada para usuário: %s" % (usuario.email,))
            else:
                current_app.logger.debug(
                        "Conta marcada para desativação (sem commit): %s" % (usuario.email,))

            return True

        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error(
                    "Erro ao desativar conta do usuário %s: %s" % (usuario.email, str(e)))
            raise e

    @staticmethod
    def conta_ativa(usuario: User) -> bool:
        """Verifica se o usuário está ativo e pode efetuar login.

        Args:
            usuario (User): Instância do usuário

        Returns:
            bool: True se o usuário pode logar, False caso contrário
        """
        if not usuario.ativo:
            current_app.logger.warning("Usuário inativo tentou logar: %s" % (usuario.email,))
            return False
        return True

    @staticmethod
    def verificar_idade_senha(usuario: User) -> Optional[int]:
        """Verifica a idade da senha em dias.

        Args:
            usuario (User): Instância do usuário

        Returns:
            Optional[int]: Idade da senha em dias, ou None se não houver data registrada
        """
        if usuario.dta_ultima_alteracao_senha is None:
            return None

        from datetime import datetime
        idade = datetime.now() - usuario.dta_ultima_alteracao_senha
        return idade.days

    @staticmethod
    def ativar_usuario_por_token(token: str) -> UserServiceResult:
        """Valida o email de um usuário através de um token JWT.

        Args:
            token (str): Token JWT de validação de email

        Returns:
            UserServiceResult: Resultado da validação
        """
        claims = JWTService.verify(token)

        if not claims.valid:
            current_app.logger.error("Token inválido: %s" % (claims.reason,))
            return UserServiceResult(
                    status=UserOperationStatus.INVALID_TOKEN,
                    error_message=f"Token inválido: {claims.reason}"
            )

        if claims.action != JWT_action.VALIDAR_EMAIL:
            current_app.logger.error("Ação de token inválida: %s" % (claims.action,))
            return UserServiceResult(
                    status=UserOperationStatus.INVALID_TOKEN,
                    error_message="Token inválido"
            )

        usuario = User.get_by_email(claims.sub)
        if usuario is None:
            current_app.logger.warning("Tentativa de validação de email para usuário inexistente")
            return UserServiceResult(
                    status=UserOperationStatus.USER_NOT_FOUND,
                    error_message="Usuário não encontrado"
            )

        if usuario.ativo:
            current_app.logger.info("Usuário %s já estava ativo" % (usuario.email,))
            return UserServiceResult(
                    status=UserOperationStatus.USER_ALREADY_ACTIVE,
                    user=usuario,
                    error_message="Usuário já está ativo"
            )

        # Confirma o email
        UserService.ativar_conta(usuario)
        current_app.logger.info("Email validado com sucesso para %s" % (usuario.email,))

        return UserServiceResult(
                status=UserOperationStatus.SUCCESS,
                user=usuario
        )

    @staticmethod
    def set_pending_2fa_token_data(usuario: User, remember_me: bool = False,
                                   next_page: str = None) -> str:
        """Cria um token para iniciar o fluxo de autenticação de dois fatores (2FA).

        Args:
            usuario (User): Instância do usuário
            remember_me (bool): Se True, mantém o usuário logado por mais tempo. Default: False
            next_page (str): Página para redirecionamento após 2FA. Default: None

        Returns:
            str: Token gerado para 2FA
        """
        return JWTService.create(action=JWT_action.PENDING_2FA,
                                 sub=usuario.id,
                                 expires_in=current_app.config.get('2FA_SESSION_TIMEOUT', 90),
                                 extra_data={
                                     'remember_me': remember_me,
                                     'next'       : next_page
                                 })

    @staticmethod
    def get_pending_2fa_token_data(token: str) -> UserServiceResult:
        """Decodifica o token de ativação do 2FA e retorna os dados contidos nele.

        Args:
            token (str): Token JWT de 2FA

        Returns:
            dict: Dados extraídos do token
        """

        dados_token = JWTService.verify(token)
        if not dados_token.valid or \
                dados_token.action != JWT_action.PENDING_2FA or \
                dados_token.extra_data is None:
            current_app.logger.error("Token de 2FA inválido: %s" % (dados_token.reason,))
            return UserServiceResult(status=UserOperationStatus.INVALID_TOKEN,
                                     error_message=dados_token.reason)
        if dados_token.sub is None:
            current_app.logger.error("Token de 2FA sem subject")
            return UserServiceResult(status=UserOperationStatus.INVALID_CREDENTIALS)
        try:
            usuario = User.get_by_id(dados_token.sub,
                                     raise_if_not_found=True)
        except User.RecordNotFoundError:
            current_app.logger.warning("Tentativa de 2FA para usuário inexistente")
            return UserServiceResult(status=UserOperationStatus.USER_NOT_FOUND)

        return UserServiceResult(status=UserOperationStatus.SUCCESS,
                                 user=usuario,
                                 extra_data=dados_token.extra_data)

    @classmethod
    def efetuar_login(cls,
                      usuario: User,
                      remember_me: bool = False,
                      session=None,
                      auto_commit: bool = True) -> bool:
        """Efetua o login do usuário no sistema utilizando Flask-Login.

        Args:
            usuario (User): Instância do usuário
            remember_me (bool): Se True, mantém o usuário logado por mais tempo
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            bool: True se o login foi bem-sucedido

        Raises:
            ValueError: Se o usuário não estiver ativo
            SQLAlchemyError: Em caso de erro na transação
        """
        if session is None:
            session = cls._default_session

        try:
            if not UserService.conta_ativa(usuario):
                raise ValueError(f"Usuário {usuario.email} não está ativo")

            # Efetua login usando Flask-Login
            login_user(usuario, remember=remember_me)
            current_app.logger.info("Login efetuado para usuário: %s" % (usuario.email,))

            # Atualiza timestamp de último login
            usuario.ultimo_login = db.func.now()

            if auto_commit:
                session.commit()
                current_app.logger.info(
                        "Informação sobre último login de %s atualizada" % (usuario.email,))
            else:
                current_app.logger.info(
                        "Informação sobre último login de %s marcada para atualizar" % (
                            usuario.email,))

            return True

        except ValueError:
            raise  # Re-propaga erro de validação
        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error(
                    "Erro ao efetuar login do usuário %s: %s" % (usuario.email, str(e)))
            raise e

    @staticmethod
    def efetuar_logout(usuario: User) -> bool:
        """Efetua o logout do usuário do sistema utilizando Flask-Login.

        Args:
            usuario (User): Instância do usuário

        Returns:
            bool: True se o logout foi bem-sucedido
        """
        try:
            user_email = usuario.email  # Captura antes do logout
            logout_user()

            current_app.logger.info("Logout efetuado para usuário: %s" % (user_email,))
            return True

        except Exception as e:
            current_app.logger.error("Erro ao efetuar logout: %s" % (str(e),))
            return False

    @classmethod
    def atualizar_perfil(cls, usuario: User,
                         novo_nome: str,
                         nova_foto=None,
                         remover_foto: bool = False,
                         session=None,
                         auto_commit: bool = True) -> UserServiceResult:
        """Atualiza o perfil do usuário (nome e foto).

        Args:
            usuario (User): Instância do usuário
            novo_nome (str): Novo nome do usuário
            nova_foto: Arquivo de foto (FileStorage) ou None
            remover_foto (bool): Se True, remove a foto atual
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            UserServiceResult: Resultado da operação
        """
        if session is None:
            session = cls._default_session

        try:
            # Valida que o nome não está vazio
            if not novo_nome or not novo_nome.strip():
                return UserServiceResult(
                        status=UserOperationStatus.UNKNOWN,
                        error_message="Nome não pode ser vazio"
                )

            # Atualiza o nome
            nome_anterior = usuario.nome
            nome_mudou = novo_nome.strip() != nome_anterior
            usuario.nome = novo_nome.strip()

            if nome_mudou:
                current_app.logger.info(
                        "Nome alterado para usuário %s: '%s' -> '%s'" %
                        (usuario.email, nome_anterior, usuario.nome))

            # Processa foto com sistema de priorização:
            # 1. remover_foto: Se True, remove a foto atual
            # 2. nova_foto: Upload de arquivo (pode ser cropada ou original)
            # Este sistema evita conflitos quando múltiplas ações são enviadas
            if remover_foto:
                usuario.foto = None
                current_app.logger.info("Foto removida para usuário %s" % (usuario.email,))
            elif nova_foto and nova_foto.filename:
                from app.services.imageprocessing_service import ImageProcessingError
                try:
                    usuario.foto = nova_foto
                    current_app.logger.info("Foto atualizada para usuário %s" % (usuario.email,))
                except ImageProcessingError as e:
                    if auto_commit:
                        session.rollback()
                    return UserServiceResult(
                            status=UserOperationStatus.UNKNOWN,
                            error_message=f"Erro ao processar imagem: {str(e)}"
                    )
                except ValueError as e:
                    if auto_commit:
                        session.rollback()
                    return UserServiceResult(
                            status=UserOperationStatus.UNKNOWN,
                            error_message=str(e)
                    )

            if auto_commit:
                session.commit()
                current_app.logger.info("Perfil salvo para usuário %s" % (usuario.email,))
            else:
                current_app.logger.debug(
                        "Perfil marcado para atualização (sem commit) para usuário %s" %
                        (usuario.email,))

            return UserServiceResult(
                    status=UserOperationStatus.SUCCESS,
                    user=usuario
            )

        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error(
                    "Erro ao atualizar perfil do usuário %s: %s" % (usuario.email, str(e)))
            return UserServiceResult(
                    status=UserOperationStatus.DATABASE_ERROR,
                    error_message=str(e)
            )

    @staticmethod
    def solicitar_reset_senha(email: str, email_service) -> UserServiceResult:
        """Envia email com token para alteração de senha.

        Args:
            email (str): Email do usuário (será normalizado)
            email_service (EmailService): Instância do serviço de email

        Returns:
            UserServiceResult: Resultado da operação
        """
        try:
            email_normalizado = EmailValidationService.normalize(email)
        except ValueError:
            current_app.logger.warning("Email inválido fornecido: %s" % (email,))
            # Por segurança, retorna SUCCESS mesmo com email inválido
            return UserServiceResult(status=UserOperationStatus.SUCCESS)

        usuario = User.get_by_email(email_normalizado)
        if usuario is None:
            current_app.logger.warning(
                    "Pedido de reset de senha para usuário inexistente (%s)" % (email_normalizado,))
            # Por segurança, retorna SUCCESS mesmo se usuário não existir
            return UserServiceResult(status=UserOperationStatus.SUCCESS)

        # Gera token e envia email
        token = JWTService.create(JWT_action.RESET_PASSWORD, sub=usuario.email)
        body = render_template('auth/email/email_new_password.jinja2',
                               nome=usuario.nome,
                               url=url_for('auth.reset_password', token=token, _external=True))
        result = email_service.send_email(to=usuario.email,
                                          subject="Altere a sua senha",
                                          text_body=body)

        if not result.success:
            current_app.logger.error("Erro ao enviar email de reset para %s" % (usuario.email,))
            return UserServiceResult(
                    status=UserOperationStatus.SEND_EMAIL_ERROR,
                    user=usuario,
                    error_message="Erro no envio do email"
            )

        current_app.logger.info("Email de reset de senha enviado para %s" % (usuario.email,))
        return UserServiceResult(
                status=UserOperationStatus.SUCCESS,
                user=usuario
        )

    @classmethod
    def redefinir_senha_por_token(cls,
                                  token: str,
                                  nova_senha: str,
                                  session=None,
                                  auto_commit: bool = True) -> UserServiceResult:
        """Redefine a senha de um usuário através de um token JWT.

        Args:
            token (str): Token JWT de redefinição de senha
            nova_senha (str): Nova senha em texto plano (será hasheada)
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            UserServiceResult: Resultado da redefinição
        """
        if session is None:
            session = cls._default_session

        # Valida o token
        resultado_token = JWTService.verify(token)

        if not resultado_token.valid:
            current_app.logger.error("Token inválido: %s" % (resultado_token.reason,))
            if resultado_token.reason == "expired":
                return UserServiceResult(
                        status=UserOperationStatus.TOKEN_EXPIRED,
                        error_message="Token expirado"
                )
            return UserServiceResult(
                    status=UserOperationStatus.INVALID_TOKEN,
                    error_message=f"Token inválido: {resultado_token.reason}"
            )

        if resultado_token.action != JWT_action.RESET_PASSWORD:
            current_app.logger.error("Ação de token inválida: %s" % (resultado_token.action,))
            return UserServiceResult(
                    status=UserOperationStatus.INVALID_TOKEN,
                    error_message="Token inválido"
            )

        if resultado_token.sub is None:
            current_app.logger.error("Token sem subject")
            return UserServiceResult(
                    status=UserOperationStatus.INVALID_TOKEN,
                    error_message="Token inválido"
            )

        # Busca o usuário
        usuario = User.get_by_email(resultado_token.sub)
        if usuario is None:
            current_app.logger.warning("Tentativa de reset de senha para usuário inexistente")
            return UserServiceResult(
                    status=UserOperationStatus.USER_NOT_FOUND,
                    error_message="Usuário não encontrado"
            )

        # Redefine a senha
        try:
            usuario.password = nova_senha  # Será hasheada pelo setter

            if auto_commit:
                session.commit()
                current_app.logger.info("Senha redefinida com sucesso para %s" % (usuario.email,))
            else:
                current_app.logger.debug(
                        "Senha marcada para redefinição (sem commit): %s" % (usuario.email,))

            return UserServiceResult(
                    status=UserOperationStatus.SUCCESS,
                    user=usuario
            )

        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error(
                    "Erro ao redefinir senha do usuário %s: %s" % (usuario.email, str(e)))
            return UserServiceResult(
                    status=UserOperationStatus.DATABASE_ERROR,
                    error_message=str(e)
            )

    @classmethod
    def listar_avaliacoes(cls,
                         usuario: User,
                         order_by: str = 'titulo',
                         ascending: bool = True,
                         session=None) -> list:
        """Lista todas as avaliações de um usuário com ordenação configurável.

        Args:
            usuario (User): Instância do usuário
            order_by (str): Campo para ordenação. Opções: 'titulo', 'titulo_original', 'data'. Default: 'titulo'
            ascending (bool): Se True, ordena ascendente. Se False, ordena descendente. Default: True
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.

        Returns:
            list: Lista de objetos Avaliacao ordenados conforme especificado

        Raises:
            ValueError: Se order_by contiver um valor inválido

        Examples:
            >>> # Ordenar por título do filme (A-Z)
            >>> avaliacoes = UserService.listar_avaliacoes(current_user, order_by='titulo')

            >>> # Ordenar por data mais recente primeiro
            >>> avaliacoes = UserService.listar_avaliacoes(current_user,
            ...                                            order_by='data',
            ...                                            ascending=False)

            >>> # Ordenar por título descendente (Z-A)
            >>> avaliacoes = UserService.listar_avaliacoes(current_user,
            ...                                            order_by='titulo',
            ...                                            ascending=False)
        """
        from app.models.juncoes import Avaliacao
        from app.models.filme import Filme
        from sqlalchemy import select, desc

        if session is None:
            session = cls._default_session

        # Valida o campo de ordenação
        valid_order_fields = ['titulo', 'data']
        if order_by not in valid_order_fields:
            raise ValueError(f"Campo de ordenação inválido: '{order_by}'. "
                           f"Valores permitidos: {', '.join(valid_order_fields)}")

        # Constrói statement base com JOIN
        stmt = (
            select(Avaliacao)
            .join(Filme)
            .where(Avaliacao.usuario_id == usuario.id)
        )

        # Define o campo de ordenação
        if order_by == 'titulo':
            order_field = Filme.titulo_portugues
        elif order_by == 'titulo_original':
            order_field = Filme.titulo_original
        else:  # order_by == 'data'
            order_field = Avaliacao.updated_at

        # Aplica ordenação (ascendente ou descendente)
        if ascending:
            stmt = stmt.order_by(order_field)
        else:
            stmt = stmt.order_by(desc(order_field))

        return session.execute(stmt).scalars().all()

    @staticmethod
    def _enviar_email_ativacao(usuario: User, email_service) -> tuple[str, bool]:
        """Metodo auxiliar privado para enviar email de ativação/confirmação.

        Args:
            usuario (user): Instância do usuário
            email_service (EmailService): Instância do serviço de email

        Returns:
            tuple[str, bool]: (token gerado, sucesso no envio)
        """
        token = JWTService.create(action=JWT_action.VALIDAR_EMAIL,
                                  sub=usuario.email)
        current_app.logger.debug("Token de ativação por email: %s" % (token,))

        body = render_template('auth/email/account_activation.jinja2',
                               nome=usuario.nome,
                               url=url_for('auth.ativar_usuario', token=token, _external=True))
        result = email_service.send_email(to=usuario.email,
                                          subject="Ative sua conta e confirme o seu email",
                                          text_body=body)

        email_sent = result.success
        if not email_sent:
            current_app.logger.error(
                    "Erro no envio do email de ativação para %s" % (usuario.email,))

        return token, email_sent
