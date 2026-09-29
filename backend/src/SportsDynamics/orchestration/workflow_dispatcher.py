"""HTTP-facing dispatch helpers for SportsDynamics workflows."""
from typing import Optional

from sqlalchemy.orm import Session

from .task_tracker import TaskTracker
from src.tasks.scrape_tasks import (
    initialize_season_task,
    scrape_autonomous_task,
    scrape_game_task,
    scrape_round_task,
)


def _create_tracker(
    db: Session,
    workflow: str,
    competition_id: str,
    season_id: str,
    round_name: Optional[str] = None,
) -> TaskTracker:
    return TaskTracker(
        db,
        "SportsDynamics",
        workflow,
        competition_id,
        season_id,
        round_name=round_name,
    )


def enqueue_season_initialization(
    db: Session,
    competition_id: str,
    season_id: str,
) -> TaskTracker:
    tracker = _create_tracker(db, "season_initialization", competition_id, season_id)
    initialize_season_task.delay(tracker.id, competition_id, season_id)
    return tracker


def enqueue_round_scrape(
    db: Session,
    competition_id: str,
    season_id: str,
    round_name: str,
) -> TaskTracker:
    tracker = _create_tracker(
        db,
        "round_scrape",
        competition_id,
        season_id,
        round_name,
    )
    scrape_round_task.delay(tracker.id, competition_id, season_id, round_name)
    return tracker


def enqueue_autonomous_scrape(
    db: Session,
    competition_id: str,
    season_id: str,
) -> TaskTracker:
    tracker = _create_tracker(db, "autonomous_scrape", competition_id, season_id)
    scrape_autonomous_task.delay(tracker.id, competition_id, season_id)
    return tracker


def enqueue_game_scrape(
    db: Session,
    game_id: str,
    competition_id: str,
    season_id: str,
    round_name: Optional[str] = None,
) -> TaskTracker:
    tracker = _create_tracker(
        db,
        "game_scrape",
        competition_id,
        season_id,
        round_name,
    )
    scrape_game_task.delay(tracker.id, game_id)
    return tracker