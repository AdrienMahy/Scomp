"""Transform distance breakdowns into match-level and interval-level data."""
from collections.abc import Mapping
from typing import Any


MT1_INTERVALS = (
    "0_5",
    "5_10",
    "10_15",
    "15_20",
    "20_25",
    "25_30",
    "30_35",
    "35_40",
    "40_45",
    "45+",
)

MT2_INTERVALS = (
    "45_50",
    "50_55",
    "55_60",
    "60_65",
    "65_70",
    "70_75",
    "75_80",
    "80_85",
    "85_90",
    "90+",
)


def _is_distance(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _rounded_sum(values: list[Any]) -> float | None:
    numeric_values = [value for value in values if _is_distance(value)]
    if not numeric_values:
        return None
    return round(sum(numeric_values), 3)


def _period_summary(
    intervals: dict[str, dict[str, Any]],
    interval_names: tuple[str, ...],
) -> dict[str, Any]:
    period_intervals = [intervals[name] for name in interval_names if name in intervals]
    summary: dict[str, Any] = {
        "total_distance_m": _rounded_sum(
            [interval.get("total_distance_m") for interval in period_intervals]
        ),
        "speed_zones_m": None,
    }

    zone_names = {
        zone
        for interval in period_intervals
        for zone in interval.get("speed_zones_m", {})
    }
    if zone_names:
        summary["speed_zones_m"] = {
            zone: _rounded_sum([
                interval.get("speed_zones_m", {}).get(zone)
                for interval in period_intervals
            ])
            for zone in sorted(zone_names)
        }

    return summary


def build_distance_data(
    total_distance_m: int | float,
    breakdowns: Any,
    match_metrics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build match and interval JSON nodes from STATSports breakdowns."""
    match_data: dict[str, Any] = {
        "total_distance_m": total_distance_m,
        "speed_zones_m": {},
        "game_state_m": {},
        "game_state_by_speed_zone_m": {},
    }
    if match_metrics:
        match_data.update(match_metrics)

    intervals: dict[str, dict[str, Any]] = {}
    for breakdown in breakdowns or []:
        if not isinstance(breakdown, Mapping):
            continue

        category = breakdown.get("category")
        distance_m = breakdown.get("distance_m")
        if not isinstance(category, Mapping) or not _is_distance(distance_m):
            continue

        speed_zone = category.get("speed_zone")
        game_state = category.get("game_state")
        interval_name = category.get("time_interval_5min")

        if interval_name is None:
            if speed_zone is not None and game_state is not None:
                match_data["game_state_by_speed_zone_m"].setdefault(
                    game_state, {}
                )[speed_zone] = distance_m
            elif speed_zone is not None:
                match_data["speed_zones_m"][speed_zone] = distance_m
            elif game_state is not None:
                match_data["game_state_m"][game_state] = distance_m
            continue

        interval_data = intervals.setdefault(
            str(interval_name),
            {"total_distance_m": None, "speed_zones_m": {}},
        )
        if speed_zone is not None and game_state is not None:
            interval_data.setdefault("game_state_by_speed_zone_m", {}).setdefault(
                game_state, {}
            )[speed_zone] = distance_m
        elif speed_zone is not None:
            interval_data["speed_zones_m"][speed_zone] = distance_m
        elif game_state is not None:
            interval_data.setdefault("game_state_m", {})[game_state] = distance_m
        else:
            interval_data["total_distance_m"] = distance_m

    match_data["periods"] = {
        "MT1": _period_summary(intervals, MT1_INTERVALS),
        "MT2": _period_summary(intervals, MT2_INTERVALS),
    }
    return {"match_data": match_data, "intervals": intervals}
