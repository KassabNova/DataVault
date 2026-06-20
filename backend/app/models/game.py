from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Game(Base):
    __tablename__ = "game"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    sets: Mapped[list["CardSet"]] = relationship(back_populates="game")


class CardSet(Base):
    __tablename__ = "card_set"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    game_id: Mapped[str] = mapped_column(ForeignKey("game.id"), nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    released_at: Mapped[str | None] = mapped_column(String)
    card_count: Mapped[int | None] = mapped_column(Integer)
    icon_url: Mapped[str | None] = mapped_column(String)

    game: Mapped["Game"] = relationship(back_populates="sets")
