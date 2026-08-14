"""Competitions routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...config.database import get_db
from ...models import Competition
from ...web.schemas import CompetitionRead

router = APIRouter(prefix="/competitions", tags=["competitions"])


@router.get("", response_model=list[CompetitionRead])
def list_competitions(db: Session = Depends(get_db)):
    """List all competitions"""
    competitions = db.query(Competition).all()
    return competitions


@router.get("/{competition_id}", response_model=CompetitionRead)
def get_competition(competition_id: str, db: Session = Depends(get_db)):
    """Get competition by ID"""
    competition = db.query(Competition).filter(Competition.id == competition_id).first()
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")
    return competition
