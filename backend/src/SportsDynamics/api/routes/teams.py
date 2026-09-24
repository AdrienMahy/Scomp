"""Teams routes - team data retrieval"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from sqlalchemy import distinct, union

from src.config.database import get_db
from src.SportsDynamics.models import Team, Game

router = APIRouter(prefix="/sportsdynamics/teams", tags=["sportsdynamics-teams"])


@router.get("", response_model=list)
def list_teams(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    competition_id: Optional[str] = Query(None),
    season_id: Optional[str] = Query(None),
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

    if competition_id or season_id:
        query = query.filter(
            Team.id.in_(
                db.query(Game.home_team_id).filter(
                    *([Game.competition_id == competition_id] if competition_id else []),
                    *([Game.season_id == season_id] if season_id else []),
                ).union(
                    db.query(Game.away_team_id).filter(
                        *([Game.competition_id == competition_id] if competition_id else []),
                        *([Game.season_id == season_id] if season_id else []),
                    )
                )
            )
        )
    
    teams = query.offset(skip).limit(limit).all()
    
    # Convert ORM objects to dictionaries
    result = []
    for team in teams:
        # Extract items from providers if it's a nested object
        providers = []
        if team.providers:
            if isinstance(team.providers, dict) and "items" in team.providers:
                providers = team.providers.get("items", [])
            elif isinstance(team.providers, list):
                providers = team.providers
        
        team_dict = {
            'id': team.id,
            'name': team.name,
            'brand': team.brand,
            'logo_url': team.logo_url,
            'providers': providers
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


@router.get("/stats")
def get_teams_stats(db: Session = Depends(get_db)):
    """
    🎯 GET TEAMS STATISTICS
    
    Returns comprehensive statistics about teams in the database:
    - Total teams
    - Teams with home games
    - Teams with away games
    - Teams with any games
    - Teams without games (unused)
    
    **Example:**
    ```bash
    curl -X GET http://localhost:8001/teams/stats
    ```
    
    **Response:**
    ```json
    {
        "total": 24,
        "home_teams": 21,
        "away_teams": 21,
        "with_games": 24,
        "without_games": 0,
        "message": "All 24 teams are being used in games"
    }
    ```
    """
    import logging
    from sqlalchemy import func
    
    logger = logging.getLogger(__name__)
    
    try:
        # Total teams
        total = db.query(func.count(Team.id)).scalar()
        
        # Teams with home games
        home_count = db.query(func.count(func.distinct(Game.home_team_id))).filter(
            Game.home_team_id.isnot(None)
        ).scalar()
        
        # Teams with away games
        away_count = db.query(func.count(func.distinct(Game.away_team_id))).filter(
            Game.away_team_id.isnot(None)
        ).scalar()
        
        # Teams with any games (union)
        from sqlalchemy import union
        home_team_ids = db.query(func.distinct(Game.home_team_id)).filter(Game.home_team_id.isnot(None))
        away_team_ids = db.query(func.distinct(Game.away_team_id)).filter(Game.away_team_id.isnot(None))
        all_game_team_ids = db.query(func.distinct(Game.home_team_id)).union(
            db.query(func.distinct(Game.away_team_id)).filter(Game.away_team_id.isnot(None))
        ).filter(Game.home_team_id.isnot(None) | Game.away_team_id.isnot(None)).count()
        
        with_games = len(db.query(func.distinct(Game.home_team_id)).union(
            db.query(func.distinct(Game.away_team_id))
        ).all())
        
        without_games = total - with_games
        
        logger.info(f"📊 Teams stats: total={total}, with_games={with_games}, without_games={without_games}")
        
        return {
            "status": "success",
            "total": total,
            "home_teams": home_count or 0,
            "away_teams": away_count or 0,
            "with_games": with_games,
            "without_games": without_games,
            "message": f"✅ Database contains {total} teams, {with_games} in active games"
        }
    
    except Exception as e:
        logger.error(f"❌ Error getting teams stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")


@router.get("/verify")
def verify_teams_integrity(db: Session = Depends(get_db)):
    """
    ✅ VERIFY TEAMS DATA INTEGRITY
    
    Performs 3 consistency checks:
    1. Check if all home_team_ids exist in teams table
    2. Check if all lineup team_ids exist in teams table
    3. Check if all teams are referenced in games or lineups
    
    **Example:**
    ```bash
    curl -X GET http://localhost:8001/teams/verify
    ```
    
    **Response (Success):**
    ```json
    {
        "status": "success",
        "integrity_ok": true,
        "orphaned_home_teams": [],
        "orphaned_lineup_teams": [],
        "unused_teams": [],
        "message": "✅ ALL CHECKS PASSED - Teams data is consistent"
    }
    ```
    
    **Response (Issues Found):**
    ```json
    {
        "status": "warning",
        "integrity_ok": false,
        "orphaned_home_teams": ["team-id-1", "team-id-2"],
        "orphaned_lineup_teams": [],
        "unused_teams": ["Team Name 1"],
        "message": "❌ Found 2 orphaned home_team_ids"
    }
    ```
    """
    import logging
    from sqlalchemy import text
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 Starting teams integrity verification...")
        
        # Check 1: Orphaned home_team_ids
        logger.info("  [1/3] Checking home_team_ids...")
        orphaned_home = db.execute(text("""
            SELECT DISTINCT home_team_id FROM games 
            WHERE home_team_id IS NOT NULL 
            AND home_team_id NOT IN (SELECT id FROM teams)
        """)).fetchall()
        orphaned_home_ids = [row[0] for row in orphaned_home]
        
        if orphaned_home_ids:
            logger.warning(f"  ⚠️  Found {len(orphaned_home_ids)} orphaned home_team_ids")
        else:
            logger.info("  ✅ All home_team_ids exist in teams table")
        
        # Check 2: Orphaned lineup team_ids
        logger.info("  [2/3] Checking lineup_team_ids...")
        orphaned_lineups = db.execute(text("""
            SELECT DISTINCT team_id FROM lineup_teams
            WHERE team_id NOT IN (SELECT id FROM teams)
        """)).fetchall()
        orphaned_lineup_ids = [row[0] for row in orphaned_lineups]
        
        if orphaned_lineup_ids:
            logger.warning(f"  ⚠️  Found {len(orphaned_lineup_ids)} orphaned lineup team_ids")
        else:
            logger.info("  ✅ All lineup team_ids exist in teams table")
        
        # Check 3: Unused teams
        logger.info("  [3/3] Checking for unused teams...")
        unused = db.execute(text("""
            SELECT id, name FROM teams
            WHERE id NOT IN (
                SELECT DISTINCT home_team_id FROM games WHERE home_team_id IS NOT NULL
                UNION
                SELECT DISTINCT away_team_id FROM games WHERE away_team_id IS NOT NULL
            )
        """)).fetchall()
        unused_teams = [{"id": row[0], "name": row[1]} for row in unused]
        
        if unused_teams:
            logger.warning(f"  ⚠️  Found {len(unused_teams)} unused teams")
        else:
            logger.info("  ✅ All teams are referenced")
        
        # Overall status
        integrity_ok = len(orphaned_home_ids) == 0 and len(orphaned_lineup_ids) == 0
        
        logger.info(f"\n{'='*60}")
        if integrity_ok:
            logger.info("✅ ALL CHECKS PASSED - Teams data is consistent")
        else:
            logger.warning("⚠️  ISSUES FOUND - Some teams data may need cleanup")
        logger.info(f"{'='*60}")
        
        return {
            "status": "success" if integrity_ok else "warning",
            "integrity_ok": integrity_ok,
            "orphaned_home_teams": orphaned_home_ids[:10],  # Limit to first 10
            "orphaned_lineup_teams": orphaned_lineup_ids[:10],
            "unused_teams": unused_teams[:10],
            "message": "✅ ALL CHECKS PASSED - Teams data is consistent" if integrity_ok else "❌ Found data inconsistencies"
        }
    
    except Exception as e:
        logger.error(f"❌ Error verifying teams: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error verifying teams: {str(e)}")


@router.get("/export")
def export_teams(db: Session = Depends(get_db)):
    """
    📤 EXPORT ALL TEAMS TO JSON
    
    Exports all teams from the database as a JSON array.
    Useful for backup, analysis, or frontend display.
    
    **Example:**
    ```bash
    curl -X GET http://localhost:8001/teams/export > teams_backup.json
    ```
    
    **Response:**
    ```json
    {
        "status": "success",
        "count": 24,
        "teams": [
            {
                "id": "b53059d3-8827-450b-9d8c-48cab41224de",
                "name": "Grenoble",
                "brand": "Grenoble Foot 38"
            },
            ...
        ],
        "timestamp": "2026-09-10T14:15:30.123456"
    }
    ```
    """
    import logging
    from datetime import datetime
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("📤 Exporting teams to JSON...")
        
        teams = db.query(Team).order_by(Team.name).all()
        
        teams_data = [
            {
                "id": team.id,
                "name": team.name,
                "brand": team.brand
            }
            for team in teams
        ]
        
        logger.info(f"✅ Exported {len(teams_data)} teams")
        
        return {
            "status": "success",
            "count": len(teams_data),
            "teams": teams_data,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Error exporting teams: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error exporting teams: {str(e)}")


@router.get("/{team_id}")
def get_team(team_id: str, db: Session = Depends(get_db)):
    """Get single team by ID with all provider information"""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return {"error": "Team not found"}, 404
    
    # Extract items from providers if it's a nested object
    providers = []
    if team.providers:
        if isinstance(team.providers, dict) and "items" in team.providers:
            providers = team.providers.get("items", [])
        elif isinstance(team.providers, list):
            providers = team.providers
    
    return {
        'id': team.id,
        'name': team.name,
        'brand': team.brand,
        'providers': providers,
        'created_at': team.created_at.isoformat() if team.created_at else None,
        'updated_at': team.updated_at.isoformat() if team.updated_at else None
    }


# Internal helper retained for coordination; not exposed publicly.
async def get_teams_from_api(
    competition_id: str = Query(None, description="Filter by competition ID"),
    limit: int = Query(100, ge=1, le=500),
    page: int = Query(1, ge=1)
):
    """
    Get all teams from SportsDynamics API (remote) - Single page
    
    **Query Parameters:**
    - `competition_id` (optional): Filter teams by competition ID
    - `limit` (default: 100): Number of teams per page
    - `page` (default: 1): Page number
    
    **Example:**
    ```bash
    curl -X GET "http://localhost:8001/teams/remote/all?limit=50&page=1"
    ```
    """
    from fastapi import HTTPException
    
    try:
        from src.SportsDynamics.api.client import SportsDynamicsClient
        
        client = SportsDynamicsClient()
        teams = client.get_clubs(
            limit=limit,
            page=page
        )
        
        return {
            "status": "success",
            "count": len(teams),
            "teams": teams,
            "pagination": {
                "page": page,
                "limit": limit
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching teams: {str(e)}")


# Internal helper retained for coordination; not exposed publicly.
async def enrich_teams_from_api(
    db: Session = Depends(get_db),
    competition_id: Optional[str] = None,
    season_id: Optional[str] = None,
):
    """
    🎯 ENRICH TEAMS FROM SPORTSDYNAMICS API
    
    **SMART STRATEGY:**
    1. Get UNIQUE team_ids from games (home_team_id + away_team_id)
    2. Call API to get COMPLETE team data (name, brand, logo, country, etc.)
    3. Enrich or create Team records in DB with full API data
    4. Maintain data consistency with games table
    
    **Why this approach:**
    - Source = SportsDynamics API for enrichment (logos, details, etc.)
    - Base = teams that are actually in games
    - Result = Complete team profiles enriched with API data
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8001/teams/remote/scrape-all"
    ```
    
    **Response:**
    ```json
    {
        "status": "success",
        "total_teams_in_games": 24,
        "enriched_from_api": 24,
        "created": 0,
        "updated": 24,
        "api_errors": 0,
        "message": "✅ Enriched 24/24 teams from API"
    }
    ```
    """
    import logging
    from datetime import datetime
    from sqlalchemy import distinct, union
    
    logger = logging.getLogger(__name__)
    
    try:
        from src.SportsDynamics.api.client import SportsDynamicsClient
        
        logger.info("=" * 90)
        logger.info("🎯 STARTING TEAM ENRICHMENT FROM SPORTSDYNAMICS API")
        logger.info("=" * 90)
        
        # ========================================================================
        # STEP 1: Collect team_ids from games
        # ========================================================================
        logger.info("📋 STEP 1: Fetching unique team_ids from games...")
        
        games_query = db.query(Game)
        if competition_id:
            games_query = games_query.filter(Game.competition_id == competition_id)
        if season_id:
            games_query = games_query.filter(Game.season_id == season_id)

        scoped_games = games_query.all()
        team_ids = {
            team_id
            for game in scoped_games
            for team_id in (game.home_team_id, game.away_team_id)
            if team_id
        }
        
        # Combine and deduplicate
        team_ids = list(team_ids)
        logger.info(f"✅ Found {len(team_ids)} unique teams in games")
        
        if not team_ids:
            logger.warning("⚠️  No teams found in games table")
            return {
                "status": "warning",
                "message": "No teams found in games table",
                "total_teams_in_games": 0
            }
        
        # ========================================================================
        # STEP 2: Call SportsDynamics API to get team data
        # ========================================================================
        logger.info(f"\n📡 STEP 2: Calling SportsDynamics API for {len(team_ids)} teams...")
        client = SportsDynamicsClient()
        
        teams_from_api = {}
        api_errors = 0
        
        try:
            # Try batch call first
            all_teams = client.get_clubs(limit=500, page=1)
            
            # Create map: team_id → team_data
            for team in all_teams:
                team_id = team.get("id")
                if team_id:
                    teams_from_api[team_id] = team
            
            found_count = len([t for t in team_ids if t in teams_from_api])
            logger.info(f"✅ API returned {found_count}/{len(team_ids)} teams found")
            
        except Exception as e:
            logger.error(f"⚠️  Partial API call issue: {str(e)}", exc_info=True)
            api_errors += 1
        
        # ========================================================================
        # STEP 3: Enrich or create Team records
        # ========================================================================
        logger.info("\n📝 STEP 3: Processing & enriching teams...")
        
        created_count = 0
        updated_count = 0
        
        for team_id in team_ids:
            try:
                # Get team data from API (or use default)
                team_data = teams_from_api.get(team_id, {})
                
                # Check if team exists in DB
                existing = db.query(Team).filter(Team.id == team_id).first()
                
                if existing:
                    # UPDATE: Merge API data with existing record
                    existing.name = team_data.get("name", existing.name)
                    existing.brand = team_data.get("brand", existing.brand)
                    existing.logo_url = team_data.get("logoUrl", existing.logo_url)
                    
                    # Add providers if available
                    if team_data.get("providers"):
                        existing.providers = team_data.get("providers")
                    
                    logger.debug(f"  ↻ Updated: {team_id} → {team_data.get('name', 'Unknown')}")
                    updated_count += 1
                else:
                    # CREATE: New team from API data
                    new_team = Team(
                        id=team_id,
                        name=team_data.get("name", "Unknown"),
                        brand=team_data.get("brand"),
                        logo_url=team_data.get("logoUrl"),
                        providers=team_data.get("providers")
                    )
                    db.add(new_team)
                    logger.debug(f"  ✓ Created: {team_id} → {team_data.get('name', 'Unknown')}")
                    created_count += 1
            
            except Exception as e:
                logger.error(f"  ❌ Error enriching team {team_id}: {str(e)}")
                api_errors += 1
                continue
        
        # Commit all changes
        db.commit()
        
        logger.info(f"\n✅ TEAM ENRICHMENT COMPLETED:")
        logger.info(f"  - Total teams in games: {len(team_ids)}")
        logger.info(f"  - Created: {created_count}")
        logger.info(f"  - Updated: {updated_count}")
        logger.info(f"  - API errors: {api_errors}")
        logger.info("=" * 90)
        
        return {
            "status": "success",
            "total_teams_in_games": len(team_ids),
            "enriched_from_api": len(teams_from_api),
            "created": created_count,
            "updated": updated_count,
            "api_errors": api_errors,
            "message": f"✅ Enriched {updated_count + created_count}/{len(team_ids)} teams from API"
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Team enrichment failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error enriching teams: {str(e)}")


# Internal helper retained for coordination; not exposed publicly.
async def scrape_teams_from_games(db: Session = Depends(get_db)):
    """
    🎯 SMART TEAM SCRAPING STRATEGY:
    
    1. Get UNIQUE teams from games table (home_team_id + away_team_id)
    2. Fetch their details from SportsDynamics API (batch query)
    3. Enrich teams table with complete data
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8001/teams/scrape-from-games
    ```
    
    **Response:**
    ```json
    {
        "status": "success",
        "teams_in_games": 45,
        "enriched_from_api": 42,
        "api_errors": 0,
        "created": 5,
        "updated": 37,
        "message": "✅ Enriched 42/45 teams from games data"
    }
    ```
    """
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        from src.SportsDynamics.api.client import SportsDynamicsClient
        
        logger.info("🎯 Starting team enrichment from games...")
        
        # Step 1: Get UNIQUE team IDs from games table
        logger.info("📊 Fetching unique teams from games...")
        
        # Query: SELECT DISTINCT home_team_id FROM games
        home_teams = db.query(distinct(Game.home_team_id)).all()
        away_teams = db.query(distinct(Game.away_team_id)).all()
        
        team_ids = set()
        for (tid,) in home_teams:
            if tid:
                team_ids.add(tid)
        for (tid,) in away_teams:
            if tid:
                team_ids.add(tid)
        
        team_ids = list(team_ids)
        logger.info(f"✅ Found {len(team_ids)} unique teams in games")
        
        if not team_ids:
            return {
                "status": "error",
                "message": "❌ No teams found in games table"
            }
        
        # Step 2: Fetch team details from API (batch query)
        logger.info(f"🚀 Fetching {len(team_ids)} teams in SINGLE batch API call...")
        client = SportsDynamicsClient()
        
        try:
            teams_from_api = client.get_clubs_by_ids(team_ids)
            logger.info(f"✅ Batch API call returned {len(teams_from_api)} teams")
        except Exception as e:
            logger.error(f"❌ Batch API call failed: {str(e)}", exc_info=True)
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error fetching teams from API: {str(e)}")
        
        # Step 3: Enrich database with API data
        created_count = 0
        updated_count = 0
        api_errors = 0
        
        # Map team IDs to API data for easier lookup
        teams_map = {t.get("id"): t for t in teams_from_api if t}
        
        for idx, team_id in enumerate(team_ids, 1):
            try:
                if idx % 10 == 0:
                    logger.info(f"  Processing {idx}/{len(team_ids)} teams...")
                
                # Get team data from API response
                team_data = teams_map.get(team_id)
                
                if not team_data:
                    logger.warning(f"  ⚠️ Team {team_id} not found in API response")
                    api_errors += 1
                    continue
                
                # Check if team exists in DB
                existing = db.query(Team).filter(Team.id == team_id).first()
                
                if existing:
                    # ✏️ UPDATE: Merge all API data into existing team
                    existing.name = team_data.get("name", existing.name)
                    existing.brand = team_data.get("brand", existing.brand)
                    existing.providers = team_data.get("providers", existing.providers)
                    
                    logger.debug(f"  ↻ Updated: {team_id} → {team_data.get('name', 'Unknown')}")
                    updated_count += 1
                else:
                    # ✅ CREATE: New team from API data
                    new_team = Team(
                        id=team_id,
                        name=team_data.get("name", "Unknown"),
                        brand=team_data.get("brand"),
                        providers=team_data.get("providers")
                    )
                    db.add(new_team)
                    logger.debug(f"  ✓ Created: {team_id} → {team_data.get('name', 'Unknown')}")
                    created_count += 1
            
            except Exception as e:
                logger.error(f"  ❌ Error enriching team {team_id}: {str(e)}")
                api_errors += 1
                continue
        
        # Step 4: Commit all changes
        db.commit()
        
        logger.info(f"✅ Team enrichment completed:")
        logger.info(f"  - Total teams in games: {len(team_ids)}")
        logger.info(f"  - Enriched from API: {len(teams_from_api)}")
        logger.info(f"  - Created: {created_count}")
        logger.info(f"  - Updated: {updated_count}")
        logger.info(f"  - API errors: {api_errors}")
        
        return {
            "status": "success",
            "teams_in_games": len(team_ids),
            "enriched_from_api": len(teams_from_api),
            "created": created_count,
            "updated": updated_count,
            "api_errors": api_errors,
            "message": f"✅ Enriched {len(teams_from_api)}/{len(team_ids)} teams from games data"
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Team enrichment failed: {str(e)}", exc_info=True)
