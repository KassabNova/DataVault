import json
import random

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.tournament import Tournament, TournamentPlayer, TournamentRound

router = APIRouter(prefix="/api/v1/tournaments", tags=["tournaments"])


class TournamentCreate(BaseModel):
    name: str
    game_id: str
    format: str | None = None
    max_players: int | None = None
    entry_fee: float = 0


class PlayerRegister(BaseModel):
    name: str


class MatchResult(BaseModel):
    p1_id: int
    p2_id: int
    p1_wins: int
    p2_wins: int
    draw: bool = False


@router.post("", status_code=201)
async def create_tournament(body: TournamentCreate, db: AsyncSession = Depends(get_db)):
    t = Tournament(**body.model_dump())
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return _t_dict(t)


@router.get("")
async def list_tournaments(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Tournament).order_by(Tournament.created_at.desc()))).scalars().all()
    return [_t_dict(t) for t in rows]


@router.get("/{tid}")
async def get_tournament(tid: int, db: AsyncSession = Depends(get_db)):
    t = await _get(tid, db)
    players = (await db.execute(select(TournamentPlayer).where(TournamentPlayer.tournament_id == tid))).scalars().all()
    rounds = (await db.execute(select(TournamentRound).where(TournamentRound.tournament_id == tid).order_by(TournamentRound.round_number))).scalars().all()
    return {
        **_t_dict(t),
        "players": [{"id": p.id, "name": p.name, "wins": p.wins, "losses": p.losses, "draws": p.draws, "dropped": p.dropped} for p in players],
        "rounds": [{"round": r.round_number, "pairings": json.loads(r.pairings) if r.pairings else []} for r in rounds],
    }


@router.post("/{tid}/players")
async def register_player(tid: int, body: PlayerRegister, db: AsyncSession = Depends(get_db)):
    t = await _get(tid, db)
    if t.status != "registration":
        raise HTTPException(400, "Registration is closed")
    count = (await db.execute(select(TournamentPlayer).where(TournamentPlayer.tournament_id == tid))).scalars().all()
    if t.max_players and len(count) >= t.max_players:
        raise HTTPException(400, "Tournament is full")
    p = TournamentPlayer(tournament_id=tid, name=body.name)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return {"id": p.id, "name": p.name}


@router.post("/{tid}/start")
async def start_tournament(tid: int, db: AsyncSession = Depends(get_db)):
    t = await _get(tid, db)
    if t.status != "registration":
        raise HTTPException(400, "Already started")
    t.status = "in_progress"
    t.current_round = 1
    await db.commit()
    return await _generate_pairings(tid, 1, db)


@router.post("/{tid}/next-round")
async def next_round(tid: int, db: AsyncSession = Depends(get_db)):
    t = await _get(tid, db)
    if t.status != "in_progress":
        raise HTTPException(400, "Tournament not in progress")
    t.current_round += 1
    await db.commit()
    return await _generate_pairings(tid, t.current_round, db)


@router.post("/{tid}/results")
async def submit_results(tid: int, body: MatchResult, db: AsyncSession = Depends(get_db)):
    """Submit match result for current round."""
    p1 = (await db.execute(select(TournamentPlayer).where(TournamentPlayer.id == body.p1_id))).scalar_one_or_none()
    p2 = (await db.execute(select(TournamentPlayer).where(TournamentPlayer.id == body.p2_id))).scalar_one_or_none()
    if not p1 or not p2:
        raise HTTPException(404, "Player not found")
    if body.draw:
        p1.draws += 1; p2.draws += 1
    elif body.p1_wins > body.p2_wins:
        p1.wins += 1; p2.losses += 1
    else:
        p2.wins += 1; p1.losses += 1
    await db.commit()
    return {"p1": {"id": p1.id, "wins": p1.wins}, "p2": {"id": p2.id, "wins": p2.wins}}


@router.post("/{tid}/complete")
async def complete_tournament(tid: int, db: AsyncSession = Depends(get_db)):
    t = await _get(tid, db)
    t.status = "completed"
    await db.commit()
    # Return standings
    players = (await db.execute(
        select(TournamentPlayer).where(TournamentPlayer.tournament_id == tid).order_by(TournamentPlayer.wins.desc(), TournamentPlayer.draws.desc())
    )).scalars().all()
    return {"status": "completed", "standings": [{"rank": i+1, "name": p.name, "wins": p.wins, "losses": p.losses, "draws": p.draws} for i, p in enumerate(players)]}


async def _generate_pairings(tid: int, round_num: int, db: AsyncSession):
    """Swiss-style pairing: match players with similar records."""
    players = (await db.execute(
        select(TournamentPlayer).where(TournamentPlayer.tournament_id == tid, TournamentPlayer.dropped == False)
        .order_by(TournamentPlayer.wins.desc(), TournamentPlayer.draws.desc())
    )).scalars().all()

    pairings = []
    paired = set()
    for i, p in enumerate(players):
        if p.id in paired:
            continue
        for j in range(i + 1, len(players)):
            if players[j].id not in paired:
                pairings.append({"p1_id": p.id, "p1_name": p.name, "p2_id": players[j].id, "p2_name": players[j].name})
                paired.add(p.id)
                paired.add(players[j].id)
                break
        else:
            # Odd player gets a bye
            pairings.append({"p1_id": p.id, "p1_name": p.name, "p2_id": None, "p2_name": "BYE"})
            p.wins += 1

    r = TournamentRound(tournament_id=tid, round_number=round_num, pairings=json.dumps(pairings))
    db.add(r)
    await db.commit()
    return {"round": round_num, "pairings": pairings}


async def _get(tid: int, db: AsyncSession) -> Tournament:
    t = (await db.execute(select(Tournament).where(Tournament.id == tid))).scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Tournament not found")
    return t


def _t_dict(t: Tournament) -> dict:
    return {"id": t.id, "name": t.name, "game_id": t.game_id, "format": t.format, "status": t.status, "max_players": t.max_players, "entry_fee": t.entry_fee, "current_round": t.current_round}
