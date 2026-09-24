"""Competitions routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.SportsDynamics.models import Competition, Season
from src.web.schemas import CompetitionRead, SeasonRead

router = APIRouter(prefix="/sportsdynamics/competitions", tags=["sportsdynamics-competitions"])


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


@router.get("/{competition_id}/seasons", response_model=list[SeasonRead])
def list_competition_seasons(competition_id: str, db: Session = Depends(get_db)):
    """List seasons available for a competition"""
    competition_exists = db.query(Competition.id).filter(
        Competition.id == competition_id
    ).first()
    if not competition_exists:
        raise HTTPException(status_code=404, detail="Competition not found")

    return db.query(Season).filter(
        Season.competition_id == competition_id
    ).order_by(Season.season_year.desc().nullslast(), Season.name.desc()).all()
