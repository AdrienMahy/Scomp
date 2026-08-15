"""Teams routes - team data retrieval"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from ...config.database import get_db
from ...models import Team

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list)
def list_teams(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List all teams with their provider information
    
    **Parameters:**
    - `skip` (default: 0): Number of teams to skip
    - `limit` (default: 100): Maximum number of teams to return
    - `search` (optional): Search by team name
    
    **Example:**
    ```bash
    curl -X GET http://localhost:8001/teams?limit=50&search=Paris
    ```
    
    **Response:**
    ```json
    [
        {
            "id": "0c1171fe-7d83-417e-98a2-f765c0ddc662",
            "name": "Paris Saint-Germain FC",
            "brand": "https://s3.eu-west-1.amazonaws.com/assets-public.../psg.png",
            "providers": [
                {
                    "externalId": "52747",
                    "provider": {"name": "UEFA"}
                },
                ...
            ]
        }
    ]
    ```
    """
    query = db.query(Team)
    
    # Search filter
    if search:
        query = query.filter(Team.name.ilike(f"%{search}%"))
    
    teams = query.offset(skip).limit(limit).all()
    
    # Convert ORM objects to dictionaries
    result = []
    for team in teams:
        team_dict = {
            'id': team.id,
            'name': team.name,
            'brand': team.brand,
            'providers': team.providers if team.providers else []
        }
        result.append(team_dict)
    
    return result


@router.get("/count")
def get_teams_count(db: Session = Depends(get_db)):
    """Get total number of teams in database"""
    count = db.query(Team).count()
    return {
        "total": count,
        "message": f"Database contains {count} teams"
    }


@router.get("/{team_id}")
def get_team(team_id: str, db: Session = Depends(get_db)):
    """Get single team by ID with all provider information"""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return {"error": "Team not found"}, 404
    
    return {
        'id': team.id,
        'name': team.name,
        'brand': team.brand,
        'providers': team.providers if team.providers else [],
        'created_at': team.created_at.isoformat() if team.created_at else None,
        'updated_at': team.updated_at.isoformat() if team.updated_at else None
    }
