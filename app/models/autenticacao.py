"""Módulo de modelos de autenticação.

Define o modelo User e funcionalidades relacionadas à autenticação de usuários,
incluindo gerenciamento de senhas, validação de email, e upload de fotos de perfil.

Classes principais:
    - User: Modelo principal de usuário com autenticação e perfil
"""
import uuid
from base64 import b64decode
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from flask import current_app
from flask_login import UserMixin
from sqlalchemy import DateTime, ForeignKey, select, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db
from app.services.email_service import EmailValidationService
from app.services.imageprocessing_service import ImageProcessingError, ImageProcessingService
from .custom_types import EncryptedString
from .mixins import AuditMixin, BasicRepositoryMixin

if TYPE_CHECKING:  # Para type checking e evitar importações circulares
    from app.models.juncoes import Avaliacao  # noqa: F401


class User(db.Model, BasicRepositoryMixin, AuditMixin, UserMixin):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(60))
    email_normalizado: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))

    ativo: Mapped[bool] = mapped_column(default=False, server_default='false')
    dta_validacao_email: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True),
                                                                    default=None)
    dta_ultima_alteracao_senha: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True),
                                                                           default=None)

    ultimo_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True),
                                                             default=None)

    com_foto: Mapped[bool] = mapped_column(default=False, server_default='false')
    foto_base64: Mapped[Optional[str]] = mapped_column(Text, default=None)
    avatar_base64: Mapped[Optional[str]] = mapped_column(Text, default=None)
    # https://datatracker.ietf.org/doc/html/rfc6838#section-4.2
    foto_mime: Mapped[Optional[str]] = mapped_column(String(129), default=None)

    usa_2fa: Mapped[bool] = mapped_column(default=False, server_default='false')
    _otp_secret: Mapped[Optional[str]] = mapped_column(EncryptedString(length=500,
                                                                       nullable=False,
                                                                       default=None))
    ultimo_otp: Mapped[Optional[str]] = mapped_column(String(6), default=None)

    # Relação ORM para acessar os códigos de backup 2FA associados a este usuário.
    codigos_otp: Mapped[list['Backup2FA']] = relationship(
            'Backup2FA',
            foreign_keys='Backup2FA.usuario_id',
            back_populates='usuario',
            lazy='dynamic'  # Permite usar como query, não carrega tudo de uma vez
    )

    # Relacionamento: um usuário pode avaliar vários filmes
    avaliacoes: Mapped[list['Avaliacao']] = relationship(back_populates='usuario',
                                                         cascade='all, delete-orphan')

    @property
    def email(self):
        """Retorna o e-mail normalizado do usuário.

        Returns:
            str: E-mail normalizado do usuário.
        """
        return self.email_normalizado

    @email.setter
    def email(self, value):
        """Define e normaliza o e-mail do usuário.

        Args:
            value (str): E-mail a ser normalizado e armazenado.

        Raises:
            ValueError: Se o e-mail fornecido for inválido.
        """
        try:
            normalizado = EmailValidationService.normalize(value)
        except ValueError:
            raise ValueError(f"E-mail inválido: {value}")
        self.email_normalizado = normalizado

    @property
    def password(self):
        """Retorna o hash da senha do usuário.

        Returns:
            str: Hash da senha do usuário.
        """
        return self.password_hash

    @password.setter
    def password(self, value):
        """Armazena o hash da senha do usuário e registra a data de alteração.

        Args:
            value (str): Senha em texto plano a ser hashada e armazenada.
        """
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(value)
        self.dta_ultima_alteracao_senha = datetime.now()

    @property
    def otp_secret(self):
        return self._otp_secret

    @otp_secret.setter
    def otp_secret(self, value: Optional[str] = None):
        self._otp_secret = value

    @classmethod
    def get_by_email(cls, email: str) -> Optional['User']:
        """Retorna o usuário com o e-mail especificado, ou None se não encontrado.

        Args:
            email (str): E-mail previamente normalizado que será buscado.

        Returns:
            typing.Optional[User]: O usuário encontrado, ou None.
        """
        return db.session.scalar(select(cls).where(User.email_normalizado == email))

    @property
    def is_active(self):
        """Indica se o usuário está ativo.

        Returns:
            bool: True se o usuário está ativo, False caso contrário.
        """
        return self.ativo

    def get_id(self):
        """Retorna identificador único para o Flask-Login com invalidação automática de sessão.

        Implementa token alternativo combinando ID do usuário com parte do hash da senha.
        Quando a senha é alterada, o hash muda e todas as sessões anteriores são invalidadas
        automaticamente.

        Returns:
            str: String no formato "{user_id}|{últimos_15_chars_do_hash}".

        References:
            https://flask-login.readthedocs.io/en/latest/#alternative-tokens
        """
        return f"{str(self.id)}|{self.password[-15:]}"

    def check_password(self, password) -> bool:
        """Verifica se a senha fornecida corresponde ao hash armazenado.

        Args:
            password (str): Senha em texto plano a ser verificada.

        Returns:
            bool: True se a senha estiver correta, False caso contrário.
        """
        from werkzeug.security import check_password_hash
        return check_password_hash(str(self.password_hash), password)

    @property
    def foto(self) -> tuple[bytes, str]:
        """Retorna a foto original do usuário em bytes e o tipo MIME.

        Se o usuário não possui foto, retorna o identicon gerado.

        Returns:
            tuple[bytes, str]: Tupla contendo os bytes da foto e o tipo MIME.
                Sempre retorna uma imagem (foto do usuário ou identicon).
        """
        if self.com_foto:
            data = b64decode(str(self.foto_base64))
            mime_type = self.foto_mime
        else:
            # Gera identicon quando não há foto
            identicon_base64, mime_type = ImageProcessingService. \
                generate_identicon_base64(data=self.email)
            data = b64decode(identicon_base64)
        return data, mime_type

    @property
    def avatar(self) -> tuple[bytes, str]:
        """Retorna o avatar do usuário em bytes e o tipo MIME.

        Se o usuário não possui foto, retorna o identicon gerado.

        Returns:
            tuple[bytes, str]: Tupla contendo os bytes do avatar e o tipo MIME.
                Sempre retorna uma imagem (avatar do usuário ou identicon).
        """
        if self.com_foto:
            data = b64decode(str(self.avatar_base64))
            mime_type = self.foto_mime
        else:
            # Gera identicon quando não há foto
            image_size = current_app.config.get("AVATAR_SIZE",
                                                ImageProcessingService.DEFAULT_AVATAR_SIZE)
            identicon_base64, mime_type = ImageProcessingService. \
                generate_identicon_base64(data=self.email,
                                          image_size=image_size)
            data = b64decode(identicon_base64)
        return data, mime_type

    @foto.setter
    def foto(self, value):
        """Setter para a foto/avatar.

        Atualiza os campos relacionados à foto. Se o valor for None, remove a
        foto e limpa os campos associados. Caso contrário, tenta armazenar
        a foto em base64 e o tipo MIME.

        IMPORTANTE: Este setter NÃO realiza commit. O chamador é responsável por
        gerenciar a transação (commit/rollback).

        Args:
            value: Um objeto com métodos `read()` e atributo `mimetype`, ou None.

        Raises:
            ImageProcessingError: Se houver erro ao processar a imagem.
            ValueError: Se o valor fornecido for inválido.
        """
        if value is None:
            self._clear_foto_fields()
        else:
            try:
                resultado = ImageProcessingService.processar_pessoa_foto(value)
            except (ImageProcessingError, ValueError):
                self._clear_foto_fields()
                raise
            else:
                self.foto_base64 = resultado.imagem_base64
                self.avatar_base64 = resultado.avatar_base64
                self.foto_mime = resultado.mime_type
                self.com_foto = True

    def _clear_foto_fields(self):
        """Limpa os campos relacionados à foto.

        Útil para operações internas onde a foto precisa ser removida
        sem passar pelo setter público.
        """
        self.com_foto = False
        self.foto_base64 = None
        self.avatar_base64 = None
        self.foto_mime = None


class Backup2FA(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = 'backup2fa'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    hash_codigo: Mapped[str] = mapped_column(String(256))
    usuario_id: Mapped[uuid.UUID] = mapped_column(
            Uuid(as_uuid=True),
            ForeignKey('usuarios.id', ondelete='CASCADE'),  # Explicit CASCADE
            index=True
    )
    utilizado: Mapped[bool] = mapped_column(default=False, server_default='false')
    dta_uso: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    dta_para_remocao: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True),
                                                                 nullable=True)

    # Relação ORM para acessar o usuário associado a este código de backup 2FA.
    usuario: Mapped['User'] = relationship('User', back_populates='codigos_otp')
