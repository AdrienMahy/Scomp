from unittest.mock import Mock, patch

import pytest

from src.SportsDynamics.orchestration.distance_covered_data import build_distance_data
from src.SportsDynamics.orchestration.scraper_coordinator import ScraperCoordinator
from src.SportsDynamics.orchestration.parser_selection import (
    normalize_parser_selection,
    required_file_types,
)


def test_build_distance_data_preserves_interval_and_zone_cross_breakdowns():
    breakdowns = [
        {"category": {"speed_zone": "walking"}, "distance_m": 900.0},
        {"category": {"game_state": "in_play"}, "distance_m": 1000.0},
        {"category": {"game_state": "out_of_play"}, "distance_m": 200.0},
        {
            "category": {"game_state": "in_play", "speed_zone": "walking"},
            "distance_m": 850.0,
        },
        {
            "category": {"game_state": "in_play", "speed_zone": "high_intensity"},
            "distance_m": 100.0,
        },
        {"category": {"time_interval_5min": "0_5"}, "distance_m": 100.0},
        {
            "category": {"speed_zone": "walking", "time_interval_5min": "0_5"},
            "distance_m": 80.0,
        },
        {
            "category": {
                "speed_zone": "high_intensity",
                "time_interval_5min": "0_5",
            },
            "distance_m": 20.0,
        },
        {"category": {"time_interval_5min": "45+"}, "distance_m": 50.0},
        {
            "category": {"speed_zone": "high_intensity", "time_interval_5min": "45+"},
            "distance_m": 40.0,
        },
        {
            "category": {"speed_zone": "sprint", "time_interval_5min": "45+"},
            "distance_m": 10.0,
        },
        {"category": {"time_interval_5min": "45_50"}, "distance_m": 80.0},
        {
            "category": {"speed_zone": "walking", "time_interval_5min": "45_50"},
            "distance_m": 75.0,
        },
        {
            "category": {"speed_zone": "sprint", "time_interval_5min": "45_50"},
            "distance_m": 5.0,
        },
        {"category": {"time_interval_5min": "90+"}, "distance_m": 20.0},
        {
            "category": {"speed_zone": "walking", "time_interval_5min": "90+"},
            "distance_m": 10.0,
        },
        {
            "category": {"speed_zone": "sprint", "time_interval_5min": "90+"},
            "distance_m": 10.0,
        },
    ]

    result = build_distance_data(250.0, breakdowns)

    assert result["match_data"]["total_distance_m"] == 250.0
    assert result["match_data"]["speed_zones_m"] == {"walking": 900.0}
    assert result["match_data"]["game_state_m"] == {
        "in_play": 1000.0,
        "out_of_play": 200.0,
    }
    assert result["match_data"]["game_state_by_speed_zone_m"] == {
        "in_play": {"walking": 850.0, "high_intensity": 100.0}
    }

    assert result["intervals"]["0_5"] == {
        "total_distance_m": 100.0,
        "speed_zones_m": {"walking": 80.0, "high_intensity": 20.0},
    }
    assert result["match_data"]["periods"] == {
        "MT1": {
            "total_distance_m": 150.0,
            "speed_zones_m": {"high_intensity": 60.0, "sprint": 10.0, "walking": 80.0},
        },
        "MT2": {
            "total_distance_m": 100.0,
            "speed_zones_m": {"sprint": 15.0, "walking": 85.0},
        },
    }


def test_build_distance_data_keeps_player_metrics_at_match_level():
    result = build_distance_data(
        7645.6,
        [{"category": {"time_interval_5min": "0_5"}, "distance_m": 500.0}],
        match_metrics={
            "minutes_played": 67.2,
            "distance_per_min_played_m": 113.8,
        },
    )

    assert result["match_data"]["total_distance_m"] == 7645.6
    assert result["match_data"]["minutes_played"] == 67.2
    assert result["match_data"]["distance_per_min_played_m"] == 113.8
    assert result["match_data"]["periods"]["MT1"]["total_distance_m"] == 500.0
    assert result["match_data"]["periods"]["MT2"]["total_distance_m"] is None


def test_parser_selection_orders_parsers_and_deduplicates():
    assert normalize_parser_selection(["fitness", "lineups", "fitness"]) == [
        "lineups",
        "fitness",
    ]
    assert normalize_parser_selection(["goals"]) == ["goals"]


def test_parser_selection_downloads_only_required_json_types():
    assert required_file_types(["player_distance"]) == {"distance_covered"}
    assert required_file_types(["goals"]) == {"rgd"}
    assert required_file_types(
        ["periods", "player_distance", "fitness"]
    ) == {"metadata", "distance_covered", "fitness_entities"}


def test_parser_selection_rejects_empty_and_unknown_ids():
    with pytest.raises(ValueError, match="at least one parser"):
        normalize_parser_selection([])

    with pytest.raises(ValueError, match="Unknown parser"):
        normalize_parser_selection(["not_a_parser"])

    with pytest.raises(ValueError, match="cannot be combined"):
        normalize_parser_selection(["goals", "rgd"])


def test_downloader_fetches_only_requested_json_types():
    coordinator = ScraperCoordinator.__new__(ScraperCoordinator)
    output_files = {
        "items": [
            {
                "fileType": "JSON",
                "fileName": "metadata_123.json",
                "file": {"url": "https://example.invalid/metadata"},
            },
            {
                "fileType": "JSON",
                "fileName": "distance_covered_123.json",
                "file": {"url": "https://example.invalid/distance"},
            },
        ]
    }
    response = Mock()
    response.read.return_value = b'{"payload": "distance"}'

    with patch(
        "src.SportsDynamics.orchestration.scraper_coordinator.urllib.request.urlopen",
        return_value=response,
    ) as urlopen:
        result = coordinator._download_json_output_files(
            "game-id",
            "Game",
            output_files,
            requested_types={"distance_covered"},
        )

    assert result == {"distance_covered": {"payload": "distance"}}
    urlopen.assert_called_once_with("https://example.invalid/distance")
