import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.modulos import db
from app.models.mixins import AuditMixin, BasicRepositoryMixin

if TYPE_CHECKING:  # Para type checking e evitar importações circulares
    from app.models.filme import Filme, Genero, FuncaoTecnica  # noqa: F401
    from app.models.pessoa import Ator, Pessoa  # noqa: F401
    from app.models.autenticacao import User  # noqa: F401


class FilmeGenero(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = 'filmes_generos'
    __table_args__ = (UniqueConstraint('filme_id', 'genero_id', name='uq_filme_genero'),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('filmes.id', ondelete='CASCADE', name='fk_filme_genero_filme'))
    genero_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('generos.id', ondelete='CASCADE', name='fk_filme_genero_genero'))
    primario: Mapped[bool] = mapped_column(default=False, server_default='false')

    filme: Mapped["Filme"] = relationship(back_populates="filme_generos",
                                          overlaps="filmes,generos")
    genero: Mapped["Genero"] = relationship(back_populates="filme_generos",
                                            overlaps="filmes,generos")


class Atuacao(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = 'atuacoes'
    __table_args__ = (
        UniqueConstraint('filme_id', 'ator_id', 'personagem', name='uq_filme_ator_personagem'),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('filmes.id', ondelete='CASCADE', name='fk_atuacao_filme'))
    ator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('atores.id', ondelete='CASCADE', name='fk_atuacao_ator'))
    personagem: Mapped[str] = mapped_column(String(100))
    protagonista: Mapped[bool] = mapped_column(default=False, server_default='false')
    creditado: Mapped[bool] = mapped_column(default=True, server_default='true')
    tempo_de_tela_minutos: Mapped[Optional[int]] = mapped_column(default=0)

    filme: Mapped["Filme"] = relationship(back_populates="elenco")
    ator: Mapped["Ator"] = relationship(back_populates="filmes")


class EquipeTecnica(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = 'equipes_tecnicas'
    __table_args__ = (UniqueConstraint('filme_id', 'pessoa_id', 'funcao_tecnica_id',
                                       name='uq_filme_pessoa_funcao'),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('filmes.id', ondelete='CASCADE', name='fk_equipe_tecnica_filme'))
    pessoa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('pessoas.id', ondelete='CASCADE', name='fk_equipe_tecnica_pessoa'))
    funcao_tecnica_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('funcoes_tecnicas.id', ondelete='CASCADE', name='fk_equipe_tecnica_funcao'))
    creditado: Mapped[bool] = mapped_column(default=True, server_default='true')

    filme: Mapped["Filme"] = relationship(back_populates="equipe_tecnica")
    pessoa: Mapped["Pessoa"] = relationship(
            back_populates="funcoes_tecnicas",
            overlaps="funcoes_tecnicas_executadas,pessoas,pessoas_executando")
    funcao_tecnica: Mapped["FuncaoTecnica"] = relationship(
            back_populates="pessoas_executando",
            overlaps="funcoes_tecnicas_executadas,pessoas,funcoes_tecnicas")


class Avaliacao(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = 'avaliacoes'
    __table_args__ = (UniqueConstraint('filme_id', 'usuario_id', name='uq_filme_usuario'),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('filmes.id', ondelete='CASCADE', name='fk_avaliacao_filme'))
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('usuarios.id', ondelete='CASCADE', name='fk_avaliacao_usuario'))
    nota: Mapped[int] = mapped_column()
    comentario: Mapped[Optional[str]] = mapped_column(Text, default=None)
    recomendaria: Mapped[bool] = mapped_column(default=False, server_default='false')

    filme: Mapped["Filme"] = relationship(back_populates="avaliacoes")
    usuario: Mapped["User"] = relationship(back_populates="avaliacoes")
