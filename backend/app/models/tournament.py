from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Tournament(Base):
    __tablename__ = "tournament"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    game_id: Mapped[str] = mapped_column(ForeignKey("game.id"), nullable=False)
    format: Mapped[str | None] = mapped_column(String)  # standard, modern, draft, etc.
    status: Mapped[str] = mapped_column(String, default="registration")  # registration, in_progress, completed
    max_players: Mapped[int | None] = mapped_column(Integer)
    entry_fee: Mapped[float] = mapped_column(Float, default=0)
    current_round: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    players: Mapped[list["TournamentPlayer"]] = relationship(back_populates="tournament")
    rounds: Mapped[list["TournamentRound"]] = relationship(back_populates="tournament")


class TournamentPlayer(Base):
    __tablename__ = "tournament_player"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournament.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    draws: Mapped[int] = mapped_column(Integer, default=0)
    dropped: Mapped[bool] = mapped_column(Integer, default=False)

    tournament: Mapped["Tournament"] = relationship(back_populates="players")


class TournamentRound(Base):
    __tablename__ = "tournament_round"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournament.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pairings: Mapped[str] = mapped_column(String)  # JSON: [{"p1_id":1,"p2_id":2,"p1_wins":0,"p2_wins":0}]

    tournament: Mapped["Tournament"] = relationship(back_populates="rounds")
