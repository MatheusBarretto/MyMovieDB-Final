from typing import Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.modulos import db
from app.models.mixins import AuditMixin


class ReencryptJob(db.Model, AuditMixin):
    """Controle de jobs de recriptografia com checkpoint/resume."""
    __tablename__ = "reencrypt_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model_path: Mapped[str] = mapped_column(String(255), nullable=False)
    column_name: Mapped[str] = mapped_column(String(128), nullable=False)
    pk_name: Mapped[str] = mapped_column(String(64), nullable=False)
    last_pk: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    target_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    total_records: Mapped[int] = mapped_column(default=0)
    processed: Mapped[int] = mapped_column(default=0)
    skipped: Mapped[int] = mapped_column(default=0)
    errors: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
