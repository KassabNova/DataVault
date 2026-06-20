from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)  # inventory_item, product, sale
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)  # create, update, delete, void
    changes: Mapped[str | None] = mapped_column(String)  # JSON of changed fields
    user: Mapped[str] = mapped_column(String, default="staff")  # who made the change
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
