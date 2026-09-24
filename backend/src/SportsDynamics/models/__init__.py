"""SQLAlchemy ORM models"""
from .base import Base, TimestampMixin
from .competition import Competition, Season
from .game import Game, Period
from .game_status import GameStatus
from .output_file import OutputFile
from .team import Team, Club
from .player import Player
from .lineup_team import LineupTeam
from .lineup_player import LineupPlayer
from .game_substitution import GameSubstitution
from .game_score_evolution import GameScoreEvolution
from .distance_covered import TeamDistanceCovered
from .player_distance_covered import PlayerDistanceCovered
from .fitness_entities import PlayerFitnessRun, PlayerFitnessSummary, TeamFitnessSummary
from .task import ScrapingTask, TaskStatus
from .scraping_log import ScrapingLog
from .automation_config import AutomationConfiguration
# Hybrid schema event tables (replacing individual models)
from .events_hybrid_schema import (
    Events, BallInPlay, Card, Foul, GoalKick, Goals,
    IndividualPossession, Kickoff, Offside, PhaseOfPlay,
    PossessionCollective, Setpieces, TypeOfPlay
)

__all__ = [
    "Base",
    "TimestampMixin",
    "Competition",
    "Season",
    "Game",
    "GameStatus",
    "OutputFile",
    "Period",
    "Team",
    "Club",
    "Player",
    "LineupTeam",
    "LineupPlayer",
    "GameSubstitution",
    "GameScoreEvolution",
    "TeamDistanceCovered",
    "PlayerDistanceCovered",
    "PlayerFitnessRun",
    "PlayerFitnessSummary",
    "TeamFitnessSummary",
    "ScrapingTask",
    "TaskStatus",
    "ScrapingLog",
    "AutomationConfiguration",
    # Hybrid schema event tables
    "Events",
    "BallInPlay",
    "Card",
    "Foul",
    "GoalKick",
    "Goals",
    "IndividualPossession",
    "Kickoff",
    "Offside",
    "PhaseOfPlay",
    "PossessionCollective",
    "Setpieces",
    "TypeOfPlay",
]
