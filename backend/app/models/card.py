from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Card(Base):
    __tablename__ = "card"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    game_id: Mapped[str] = mapped_column(ForeignKey("game.id"), nullable=False)
    set_id: Mapped[str] = mapped_column(ForeignKey("card_set.id"), nullable=False)
    collector_number: Mapped[str] = mapped_column(String, nullable=False)
    name_en: Mapped[str] = mapped_column(String, nullable=False)
    rarity: Mapped[str | None] = mapped_column(String)
    card_type: Mapped[str | None] = mapped_column(String)
    subtypes: Mapped[str | None] = mapped_column(String)  # JSON array
    colors: Mapped[str | None] = mapped_column(String)  # JSON array
    mana_cost: Mapped[str | None] = mapped_column(String)
    image_url_small: Mapped[str | None] = mapped_column(String)
    image_url_normal: Mapped[str | None] = mapped_column(String)
    image_url_large: Mapped[str | None] = mapped_column(String)
    external_ids: Mapped[str | None] = mapped_column(String)  # JSON
    metadata_: Mapped[str | None] = mapped_column("metadata", String)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    names: Mapped[list["CardName"]] = relationship(back_populates="card")

    __table_args__ = (UniqueConstraint("game_id", "set_id", "collector_number"),)


class CardName(Base):
    __tablename__ = "card_name"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[str] = mapped_column(ForeignKey("card.id"), nullable=False)
    locale: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    card: Mapped["Card"] = relationship(back_populates="names")

    __table_args__ = (UniqueConstraint("card_id", "locale"),)
