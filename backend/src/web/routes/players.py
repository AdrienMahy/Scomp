"""Players routes - player scraping and retrieval"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
import re
import json
from itertools import groupby

from ...config.database import get_db
from ...models import Player, LineupPlayer, Team
from ...models import ScrapingTask
from ...orchestration.task_tracker import TaskTracker
from ...tasks.scrape_tasks import enrich_players_task

router = APIRouter(prefix="/players", tags=["players"])


# ============================================================================
# HELPER FUNCTIONS FOR TEAMS HISTORY
# ============================================================================

def extract_round_number(round_str: str) -> int:
    """
    Extract round number from string like 'Round 1', 'Week 5', 'Match Day 10', etc.
    
    Args:
        round_str: String like "Round 1", "Round 10", "Week 5", etc.
        
    Returns:
        Integer round number, or 0 if parsing fails
        
    Examples:
        extract_round_number("Round 1")    → 1
        extract_round_number("Round 10")   → 10
        extract_round_number("Week 5")     → 5
        extract_round_number(None)         → 0
    """
    if not round_str or not isinstance(round_str, str):
        return 0
    
    # Use regex to find first integer sequence
    match = re.search(r'(\d+)', round_str)
    return int(match.group(1)) if match else 0


def build_team_history(player_games: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Build team history from list of games where player appeared.
    
    Groups consecutive games by team, calculates round_start/round_end per team period.
    
    Args:
        player_games: List of dicts with keys:
            - round: "Round 1", "Round 10", etc.
            - team_id: UUID of team
            - team_name: Team name
            - team_brand: Team brand
            
    Returns:
        {
            "current_team": {"id": "...", "brand": "..."},
            "history": [
                {
                    "team_id": "...",
                    "team_name": "...",
                    "team_brand": "...",
                    "round_start": 1,
                    "round_end": 5,
                    "games_count": 5
                },
                ...
            ]
        }
        or None if player_games is empty
    """
    if not player_games:
        return None
    
    # STEP 1: Sort by round NUMBER (not string!)
    player_games_sorted = sorted(
        player_games,
        key=lambda x: extract_round_number(x.get('round', '0'))
    )
    
    # STEP 2: Group consecutive periods for same team
    team_periods = []
    for team_id, games_group in groupby(player_games_sorted, key=lambda x: x.get('team_id')):
        games_list = list(games_group)
        round_numbers = [extract_round_number(g.get('round', '0')) for g in games_list]
        
        team_periods.append({
            "team_id": team_id,
            "team_name": games_list[0].get('team_name', 'Unknown'),
            "team_brand": games_list[0].get('team_brand', 'Unknown'),
            "round_start": min(round_numbers),
            "round_end": max(round_numbers),
            "games_count": len(games_list)
        })
    
    # STEP 3: Identify current team (last period)
    current_team_period = team_periods[-1] if team_periods else None
    
    return {
        "current_team": {
            "id": current_team_period['team_id'],
            "brand": current_team_period['team_brand']
        } if current_team_period else None,
        "history": team_periods
    }


@router.get("/teams", response_model=list)
def get_player_teams(db: Session = Depends(get_db)):
    """
    Get unique teams from players with their team_id and brand
    
    **Returns:**
    List of unique teams with id and name
    
    **Example:**
    ```bash
    curl -X GET http://localhost:8001/players/teams
    ```
    """
    # Get distinct teams from players where current_team_id is not null
    from sqlalchemy import distinct, func
    
    teams = db.query(
        distinct(Player.current_team_id).label('id'),
        Player.current_team_brand.label('name')
    ).filter(
        Player.current_team_id != None,
        Player.current_team_brand != None
    ).order_by(Player.current_team_brand).all()
    
    result = []
    for team in teams:
        if team.id and team.name:
            result.append({
                'id': team.id,
                'name': team.name
            })
    
    return result


@router.get("", response_model=list)
def list_players(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    team_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List players from database
    
    **Parameters:**
    - `skip` (default: 0): Number of players to skip
    - `limit` (default: 100): Maximum number of players to return
    - `search` (optional): Search by player name
    - `team_id` (optional): Filter by current team ID
    
    **Example:**
    ```bash
    curl -X GET http://localhost:8001/players?limit=50&search=Mbappe&team_id=96da961d-a2c6-4309-bda0-fa6f8ff902fa
    ```
    """
    query = db.query(Player)
    
    # Filter out players without a name
    query = query.filter(Player.name != None).filter(Player.name != '')
    
    # Team filter
    if team_id:
        query = query.filter(Player.current_team_id == team_id)
    
    # Search filter
    if search:
        query = query.filter(Player.name.ilike(f"%{search}%"))
    
    players = query.offset(skip).limit(limit).all()
    
    # Convert ORM objects to dictionaries
    result = []
    for player in players:
        player_dict = {
            'id': player.id,
            'name': player.name,
            'first_name': player.first_name,
            'last_name': player.last_name,
            'usage_name': player.usage_name,
            'photo': player.photo,
            'age': player.age,
            'birthdate': player.birthdate.isoformat() if player.birthdate else None,
            'current_team_id': player.current_team_id,
            'current_team_brand': player.current_team_brand,
            'current_national_team_id': player.current_national_team_id,
            'current_national_team_brand': player.current_national_team_brand,
            'nationalities': player.nationalities if player.nationalities else [],
            'positions': player.positions if player.positions else [],
            'teams': player.teams if player.teams else None
        }
        result.append(player_dict)
    
    return result


@router.get("/count")
def get_players_count(db: Session = Depends(get_db)):
    """Get total number of players in database"""
    count = db.query(Player).count()
    return {
        "total": count,
        "message": f"Database contains {count} players"
    }


@router.get("/{player_id}")
def get_player(player_id: str, db: Session = Depends(get_db)):
    """Get single player by ID with all information"""
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    return {
        'id': player.id,
        'name': player.name,
        'first_name': player.first_name,
        'last_name': player.last_name,
        'usage_name': player.usage_name,
        'photo': player.photo,
        'age': player.age,
        'birthdate': player.birthdate.isoformat() if player.birthdate else None,
        'current_team_id': player.current_team_id,
        'current_team_brand': player.current_team_brand,
        'current_national_team_id': player.current_national_team_id,
        'current_national_team_brand': player.current_national_team_brand,
        'nationalities': player.nationalities if player.nationalities else [],
        'positions': player.positions if player.positions else [],
        'teams': player.teams if player.teams else None,
        'created_at': player.created_at.isoformat() if player.created_at else None,
        'updated_at': player.updated_at.isoformat() if player.updated_at else None
    }


# Internal helper retained for coordination; not exposed publicly.
async def get_players_from_api(
    limit: int = 100,
    page: int = 1
):
    """
    Get all players from SportsDynamics API (remote) - Single page
    
    **Query Parameters:**
    - `limit` (default: 100): Number of players per page
    - `page` (default: 1): Page number
    
    **Example:**
    ```bash
    curl -X GET "http://localhost:8001/players/remote/all?limit=50&page=1"
    ```
    """
    try:
        from ...api.sportsdynamics import SportsDynamicsClient
        
        client = SportsDynamicsClient()
        players = client.get_players(
            limit=limit,
            page=page
        )
        
        return {
            "status": "success",
            "count": len(players),
            "players": players,
            "pagination": {
                "page": page,
                "limit": limit
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching players: {str(e)}")


# Internal helper retained for coordination; not exposed publicly.
async def scrape_all_players_from_api(db: Session = Depends(get_db)):
    """
    🎯 SYNC PLAYERS DATA FROM v_players_teams_full VIEW
    
    **STRATEGY:**
    1. Extract player data from v_players_teams_full (enriched view with complete data)
    2. Update/create players in players table with: photo, age, birthdate, positions, nationalities
    3. Assign correct team_id from view
    4. Result: Complete enriched player database
    
    **Why this works:**
    - Data source: Events-based enriched view (always up-to-date)
    - No API ID matching needed (view data is internal IDs only)
    - FK safe: team_ids come directly from view
    - Complete data: photo, age, positions, nationalities already present
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8001/players/remote/scrape-all"
    ```
    """
    import logging
    from datetime import datetime
    from sqlalchemy import text
    
    logger = logging.getLogger(__name__)
    
    try:
        from ...models import Player
        
        logger.info("=" * 90)
        logger.info("🎯 STARTING PLAYER ENRICHMENT FROM v_players_teams_full")
        logger.info("=" * 90)
        
        # ========================================================================
        # STEP 1: Fetch all players from enriched view
        # ========================================================================
        logger.info("📋 STEP 1: Fetching player data from enriched view...")
        
        enriched_players = db.execute(text("""
            SELECT DISTINCT
                player_id,
                player_name,
                first_name,
                last_name,
                usage_name,
                photo,
                age,
                birthdate,
                team_id,
                team_brand,
                positions_json,
                nationalities_json,
                current_national_team_id,
                current_national_team_brand,
                player_updated_at
            FROM v_players_teams_full 
            WHERE player_id IS NOT NULL AND team_id IS NOT NULL
        """)).fetchall()
        
        logger.info(f"✅ Fetched {len(enriched_players)} unique player records from view")
        
        if not enriched_players:
            logger.error("❌ No players found in view")
            return {"status": "error", "message": "No players found in database"}
        
        # ========================================================================
        # STEP 2: Process and sync players to DB
        # ========================================================================
        logger.info("\n📝 STEP 2: Processing & syncing players to database...")
        
        created_count = 0
        updated_count = 0
        
        for idx, row in enumerate(enriched_players, 1):
            try:
                if idx % 50 == 0 or idx == 1:
                    logger.info(f"   Processing player {idx}/{len(enriched_players)}...")
                
                (player_id, player_name, first_name, last_name, usage_name, 
                 photo, age, birthdate, team_id, team_brand, 
                 positions_json, nationalities_json, nat_team_id, nat_team_brand, updated_at) = row
                
                # Check if player exists
                existing = db.query(Player).filter(Player.id == player_id).first()
                
                if existing:
                    # ✏️ UPDATE existing player
                    existing.first_name = first_name or existing.first_name
                    existing.last_name = last_name or existing.last_name
                    existing.name = player_name or existing.name
                    existing.usage_name = usage_name or existing.usage_name
                    existing.photo = photo or existing.photo
                    existing.age = age or existing.age
                    existing.birthdate = birthdate or existing.birthdate
                    existing.current_team_id = team_id
                    existing.current_team_brand = team_brand or existing.current_team_brand
                    existing.current_national_team_id = nat_team_id or existing.current_national_team_id
                    existing.current_national_team_brand = nat_team_brand or existing.current_national_team_brand
                    existing.positions = positions_json or existing.positions
                    existing.nationalities = nationalities_json or existing.nationalities
                    existing.updated_at = datetime.utcnow()
                    
                    updated_count += 1
                else:
                    # ✅ CREATE new player
                    new_player = Player(
                        id=player_id,
                        first_name=first_name,
                        last_name=last_name,
                        name=player_name or "Unknown",
                        usage_name=usage_name,
                        photo=photo,
                        age=age,
                        birthdate=birthdate,
                        current_team_id=team_id,
                        current_team_brand=team_brand,
                        current_national_team_id=nat_team_id,
                        current_national_team_brand=nat_team_brand,
                        positions=positions_json,
                        nationalities=nationalities_json,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.add(new_player)
                    created_count += 1
                
                if (idx % 50 == 0 or idx == len(enriched_players)):
                    db.flush()  # Intermediate flush for large batches
                    
            except Exception as e:
                logger.error(f"   ❌ Error processing player {player_id}: {str(e)}", exc_info=True)
                continue
        
        # ========================================================================
        # STEP 3: Commit and return results
        # ========================================================================
        logger.info("\n💾 STEP 3: Committing changes to database...")
        
        try:
            db.commit()
            logger.info(f"✅ COMMIT SUCCESSFUL")
            
            # Get final count from DB
            total_players = db.query(Player).count()
            
            logger.info("\n" + "=" * 90)
            logger.info(f"✅ PLAYER ENRICHMENT COMPLETE")
            logger.info(f"   Total players in DB: {total_players}")
            logger.info(f"   Created: {created_count}")
            logger.info(f"   Updated: {updated_count}")
            logger.info(f"   Status: SUCCESS ✅")
            logger.info("=" * 90)
            
            return {
                "status": "success",
                "total_players_in_db": total_players,
                "created": created_count,
                "updated": updated_count,
                "message": f"✅ Enriched {created_count + updated_count}/{len(enriched_players)} players from view"
            }
            
        except Exception as e:
            logger.error(f"❌ Commit FAILED: {str(e)}", exc_info=True)
            db.rollback()
            return {"status": "error", "message": f"Database commit failed: {str(e)}"}
    
    except Exception as e:
        db.rollback()
        logger.error("=" * 90)
        logger.error("🔴 CRITICAL ERROR - ENRICHMENT FAILED")
        logger.error("=" * 90)
        logger.error(f"Error: {str(e)}", exc_info=True)
        logger.error("=" * 90 + "\n")
        raise HTTPException(status_code=500, detail=f"Error enriching players: {str(e)}")


async def enrich_players_for_games(
    db: Session,
    competition_id: Optional[str] = None,
    season_id: Optional[str] = None,
    game_ids: Optional[List[str]] = None,
):
    """
    🎯 ENRICH PLAYERS FROM GAMES + SPORTSDYNAMICS API
    
    **STRATEGY:**
    1. Fetch all games from database (optionally filtered by competition)
    2. Build player list + team history from LOCAL lineup data
       (lineup_players → lineup_teams → games → teams)
    3. Batch fetch player bio details from API using get_players_by_ids()
    4. Extract: positions, nationalities, photo, age, birthdate from API
    5. CREATE/UPDATE players in players table with fresh data
    
    **Why this works:**
    - Team name/brand/round come from OUR database (reliable, already scraped),
      not from the GraphQL API squads/round fields (which don't expose team name/brand
      and return round as a nested object, causing "Unknown" brands and round=0 bugs)
    - Bio data (photo, age, positions, nationalities) still comes from the API
    - Bulk operation: Batches multiple player fetches efficiently
    
    **Query Parameters:**
    - `competition_id` (optional): Filter games by competition ID
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8001/players/enrich-from-games-api"
    curl -X POST "http://localhost:8001/players/enrich-from-games-api?competition_id=b4bda75a-946f-4206-93e0-1545c319b04c"
    ```
    """
    import logging
    from datetime import datetime
    from sqlalchemy import text
    import json
    
    logger = logging.getLogger(__name__)
    
    try:
        from ...models import Player, Game, Team, LineupPlayer, LineupTeam
        from ...api.sportsdynamics import SportsDynamicsClient
        
        logger.info("=" * 90)
        logger.info("🎯 STARTING PLAYER ENRICHMENT FROM GAMES + SPORTSDYNAMICS API")
        logger.info("=" * 90)
        
        # ========================================================================
        # STEP 1: Fetch all games (optionally filtered by competition)
        # ========================================================================
        logger.info("📋 STEP 1: Fetching games from database...")
        
        query = db.query(Game)
        if competition_id:
            query = query.filter(Game.competition_id == competition_id)
        if season_id:
            query = query.filter(Game.season_id == season_id)
        if game_ids is not None:
            query = query.filter(Game.id.in_(game_ids))
        
        games = query.all()
        logger.info(f"✅ Found {len(games)} games")
        
        if not games:
            logger.warning("⚠️ No games found in database")
            return {"status": "warning", "message": "No games found in database"}
        
        # ========================================================================
        # STEP 2: Build player list + team history from LOCAL lineup data
        # ========================================================================
        # Team name/brand and round come from OUR database (lineup_players →
        # lineup_teams → games → teams), NOT from the GraphQL API. The API's squads
        # don't even expose team name/brand, and round is a nested object rather than
        # a string, which caused 100% "Unknown" brands and round=0 values previously.
        logger.info("\n🏆 STEP 2: Building player list + team history from local lineup data...")
        
        game_ids = [game.id for game in games]
        
        lineup_rows = (
            db.query(
                LineupPlayer.player_id,
                Game.round,
                Team.id.label("team_id"),
                Team.name.label("team_name"),
                Team.brand.label("team_brand"),
            )
            .join(LineupTeam, LineupPlayer.lineup_team_id == LineupTeam.id)
            .join(Game, LineupTeam.game_id == Game.id)
            .join(Team, LineupTeam.team_id == Team.id)
            .filter(LineupTeam.game_id.in_(game_ids))
            .all()
        )
        
        # Mapping: player_id -> list of games where they appeared
        player_games_map: Dict[str, List[Dict[str, Any]]] = {}
        for player_id, game_round, team_id, team_name, team_brand in lineup_rows:
            player_games_map.setdefault(player_id, []).append({
                "round": game_round,
                "team_id": team_id,
                "team_name": team_name,
                "team_brand": team_brand or team_name,
            })
        
        all_player_ids = set(player_games_map.keys())
        logger.info(f"✅ Built teams history for {len(all_player_ids)} players from {len(lineup_rows)} local lineup records")
        
        if not all_player_ids:
            logger.warning("⚠️ No players found in local lineup_players for these games")
            return {"status": "warning", "message": "No players found in lineup_players for these games"}
        
        # ========================================================================
        # STEP 3: Batch fetch player bio details from API (photo, age, positions...)
        # ========================================================================
        logger.info("\n🔄 STEP 3: Batch fetching player bio details from API...")
        logger.info(f"   Fetching {len(all_player_ids)} players...")
        
        client = SportsDynamicsClient()
        player_ids_list = list(all_player_ids)
        api_players = client.get_players_by_ids(player_ids_list)
        logger.info(f"✅ Fetched {len(api_players)} players from API")
        
        # Create lookup dict for quick access
        players_lookup = {p['id']: p for p in api_players if p}
        
        # ========================================================================
        # STEP 4: Process and sync players to DB
        # ========================================================================
        logger.info("\n📝 STEP 4: Processing & syncing players to database...")
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        for idx, player_id in enumerate(player_ids_list, 1):
            try:
                if idx % 100 == 0 or idx == 1:
                    logger.info(f"   Processing {idx}/{len(player_ids_list)}...")
                
                existing = db.query(Player).filter(Player.id == player_id).first()
                api_player = players_lookup.get(player_id) or {}
                if not api_player:
                    logger.warning(
                        f"   ⚠️ Player {player_id} not found in API response; "
                        "processing local team history only"
                    )
                
                # Extract fields from API response
                first_name = api_player.get('firstName')
                last_name = api_player.get('lastName')
                player_name = (
                    api_player.get('name')
                    or api_player.get('usageName')
                    or (existing.name if existing else None)
                    or f"Player {player_id[:8]}"
                )
                usage_name = api_player.get('usageName')
                photo = api_player.get('photo')
                age = api_player.get('age')
                birthdate = api_player.get('birthdate')
                
                # Extract positions (from API structure: positions.items or positions array)
                positions_data = api_player.get('positions', {})
                # Keep as dict for JSONB, don't convert to string
                positions_dict = positions_data if positions_data else None
                
                # Extract nationalities (from API structure: nationalities.items or nationalities array)
                nationalities_data = api_player.get('nationalities', {})
                # Keep as dict for JSONB, don't convert to string
                nationalities_dict = nationalities_data if nationalities_data else None
                
                # Extract national team if available
                nat_team = api_player.get('currentNationalTeam', {})
                nat_team_id = nat_team.get('id') if nat_team else None
                nat_team_brand = nat_team.get('brand') if nat_team else None
                
                # 🏆 BUILD TEAMS HISTORY from LOCAL lineup data (player_games_map)
                current_team_id = None
                current_team_brand = None
                teams_history_dict = None
                
                if player_id in player_games_map:
                    player_games = player_games_map[player_id]
                    teams_history = build_team_history(player_games)
                    
                    if teams_history:
                        current_team_obj = teams_history.get('current_team', {})
                        # Keep as dict for JSONB, don't convert to string
                        teams_history_dict = teams_history
                        
                        # Only set current_team_id if team exists in DB to avoid FK violation
                        # The teams_history JSON stores the current team info anyway
                        team_id = current_team_obj.get('id')
                        if team_id:
                            team_exists = db.query(Team).filter(Team.id == team_id).first()
                            if team_exists:
                                current_team_id = team_id
                                current_team_brand = current_team_obj.get('brand')
                        
                        logger.debug(f"   ✅ Player {player_id}: {len(teams_history.get('history', []))} team period(s), current: {current_team_obj.get('brand')}")
                
                if existing:
                    # ✏️ UPDATE existing player
                    existing.first_name = first_name or existing.first_name
                    existing.last_name = last_name or existing.last_name
                    existing.name = player_name or existing.name
                    existing.usage_name = usage_name or existing.usage_name
                    existing.photo = photo or existing.photo
                    existing.age = age or existing.age
                    existing.birthdate = birthdate or existing.birthdate
                    existing.current_national_team_id = nat_team_id or existing.current_national_team_id
                    existing.current_national_team_brand = nat_team_brand or existing.current_national_team_brand
                    existing.positions = positions_dict or existing.positions
                    existing.nationalities = nationalities_dict or existing.nationalities
                    # 🏆 Update teams history
                    existing.current_team_id = current_team_id or existing.current_team_id
                    existing.current_team_brand = current_team_brand or existing.current_team_brand
                    existing.teams = teams_history_dict or existing.teams
                    existing.updated_at = datetime.utcnow()
                    
                    updated_count += 1
                else:
                    # ✅ CREATE new player with team history
                    new_player = Player(
                        id=player_id,
                        first_name=first_name,
                        last_name=last_name,
                        name=player_name or "Unknown",
                        usage_name=usage_name,
                        photo=photo,
                        age=age,
                        birthdate=birthdate,
                        current_national_team_id=nat_team_id,
                        current_national_team_brand=nat_team_brand,
                        positions=positions_dict,
                        nationalities=nationalities_dict,
                        # 🏆 Set teams and current team from history
                        current_team_id=current_team_id,
                        current_team_brand=current_team_brand,
                        teams=teams_history_dict,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.add(new_player)
                    created_count += 1
                
                if (idx % 100 == 0 or idx == len(player_ids_list)):
                    db.flush()  # Intermediate flush for large batches
                    
            except Exception as e:
                logger.error(f"   ❌ Error processing player {player_id}: {str(e)}", exc_info=True)
                skipped_count += 1
                continue
        
        # ========================================================================
        # STEP 5: Commit and return results
        # ========================================================================
        logger.info("\n💾 STEP 5: Committing changes to database...")
        
        try:
            db.commit()
            logger.info(f"✅ COMMIT SUCCESSFUL")
            
            # Get final count from DB
            total_players = db.query(Player).count()
            
            logger.info("\n" + "=" * 90)
            logger.info(f"✅ PLAYER ENRICHMENT FROM GAMES + API COMPLETE")
            logger.info(f"   Total players in DB: {total_players}")
            logger.info(f"   Created: {created_count}")
            logger.info(f"   Updated: {updated_count}")
            logger.info(f"   Skipped: {skipped_count}")
            logger.info(f"   Status: SUCCESS ✅")
            logger.info("=" * 90)
            
            return {
                "status": "success",
                "total_players_in_db": total_players,
                "created": created_count,
                "updated": updated_count,
                "skipped": skipped_count,
                "message": f"✅ Enriched {created_count + updated_count}/{len(player_ids_list)} players from API"
            }
            
        except Exception as e:
            logger.error(f"❌ Commit FAILED: {str(e)}", exc_info=True)
            db.rollback()
            return {"status": "error", "message": f"Database commit failed: {str(e)}"}
    
    except Exception as e:
        db.rollback()
        logger.error("=" * 90)
        logger.error("🔴 CRITICAL ERROR - ENRICHMENT FROM GAMES + API FAILED")
        logger.error("=" * 90)
        logger.error(f"Error: {str(e)}", exc_info=True)
        logger.error("=" * 90 + "\n")
        raise HTTPException(status_code=500, detail=f"Error enriching players from games: {str(e)}")


@router.post("/scrape-players", tags=["players"])
async def scrape_players(
    competition_id: str = Query(None, description="Filter by competition_id"),
    season_id: str = Query(None, description="Filter by season_id"),
    db: Session = Depends(get_db)
):
    """Queue player enrichment for the selected competition and season."""
    if not competition_id or not season_id:
        raise HTTPException(status_code=400, detail="competition_id and season_id are required")
    tracker = TaskTracker(db, "SportsDynamics", "player_enrichment", competition_id, season_id)
    enrich_players_task.delay(tracker.id, competition_id, season_id)
    return {"status": "queued", "task_id": tracker.id, "workflow": "player_enrichment"}
