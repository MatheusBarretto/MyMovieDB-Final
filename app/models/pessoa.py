import uuid
from base64 import b64decode
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db
from app.models.mixins import AuditMixin, BasicRepositoryMixin
from app.services.imageprocessing_service import ImageProcessingError, ImageProcessingService

if TYPE_CHECKING:  # Para type checking e evitar importações circulares
    from app.models.juncoes import Atuacao, EquipeTecnica  # noqa: F401
    from app.models.filme import FuncaoTecnica  # noqa: F401


class Pessoa(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = 'pessoas'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(100))
    data_nascimento: Mapped[Optional[datetime]] = mapped_column(Date, default=None)
    data_falecimento: Mapped[Optional[datetime]] = mapped_column(Date, default=None)
    local_nascimento: Mapped[Optional[str]] = mapped_column(String(100))
    biografia: Mapped[Optional[str]] = mapped_column(Text)
    foto_base64: Mapped[Optional[str]] = mapped_column(Text)
    foto_mime: Mapped[Optional[str]] = mapped_column(String(129))
    com_foto: Mapped[bool] = mapped_column(default=False, server_default='false')

    ator: Mapped[Optional["Ator"]] = relationship(back_populates="pessoa",
                                                  cascade="all, delete-orphan")

    funcoes_tecnicas: Mapped[list["EquipeTecnica"]] = relationship(
            back_populates="pessoa",
            cascade="all, delete-orphan",
            overlaps="funcoes_tecnicas_executadas,pessoas_executando,pessoas")

    funcoes_tecnicas_executadas: Mapped[list["FuncaoTecnica"]] = relationship(
            secondary="equipes_tecnicas",
            back_populates="pessoas",
            overlaps="funcoes_tecnicas,pessoas_executando")

    @property
    def foto(self) -> tuple[bytes, str]:
        """Retorna a foto da pessoa em bytes e o tipo MIME.

        Se a pessoa não possuir uma poster, retorna um placeholder.

        Returns:
            tuple[bytes, str]: Tupla contendo os bytes da foto e o tipo MIME.
                Sempre retorna uma imagem (poster ou placeholder).
        """
        if self.com_foto:
            data = b64decode(str(self.foto_base64))
            mime_type = self.foto_mime
        else:
            data = ImageProcessingService.gerar_placeholder(200, 300)
            mime_type = 'image/png'
        return data, mime_type

    @foto.setter
    def foto(self, value):
        """Setter para foto.

        Atualiza os campos relacionados à foto. Se o valor for None, remove
        a foto e limpa os campos associados. Caso contrário, tenta armazenar
        a foto em base64 e o tipo MIME com crop automático para aspect ratio 2:3.

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
                # Usa o novo método que aplica crop automático para aspect ratio 2:3
                resultado = ImageProcessingService.processar_pessoa_foto(value)
            except (ImageProcessingError, ValueError):
                self._clear_foto_fields()
                raise
            else:
                self.foto_base64 = resultado.imagem_base64
                self.foto_mime = resultado.mime_type
                self.com_foto = True

    @property
    def idade(self):
        """Calcula a idade em anos completos com base em `data_nascimento`.

        Retorna None se `data_nascimento` não estiver definida.
        Se `data_falecimento` estiver definida, calcula a idade na data de falecimento,
        caso contrário utiliza a data atual.
        """
        if not self.data_nascimento:
            return None
        ref = self.data_falecimento or datetime.now()
        return (
            ref.year - self.data_nascimento.year -
            ((ref.month, ref.day) < (self.data_nascimento.month, self.data_nascimento.day))
        )

    def _clear_foto_fields(self):
        """Limpa os campos relacionados à foto.

        Útil para operações internas onde o poster precisa ser removido
        sem passar pelo setter público.
        """
        self.foto_base64 = None
        self.foto_mime = None
        self.com_foto = False


class Ator(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = 'atores'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pessoa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('pessoas.id',
                                                            ondelete="CASCADE"),
                                                 unique=True)
    nome_artistico: Mapped[Optional[str]] = mapped_column(String(100))

    pessoa: Mapped["Pessoa"] = relationship(back_populates="ator")
    filmes: Mapped[list["Atuacao"]] = relationship(back_populates="ator",
                                                   cascade="all, delete-orphan")
