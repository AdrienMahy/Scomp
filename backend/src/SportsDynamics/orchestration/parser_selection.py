"""Parser identifiers and JSON file dependencies for manual round scraping."""

from typing import Literal, TypeAlias


ParserName: TypeAlias = Literal[
    "lineups",
    "periods_phase",
    "distances",
    "events",
    "fitness",
    # Retained for existing API clients; the frontend uses the grouped selectors above.
    "periods",
    "substitutions",
    "team_distance",
    "player_distance",
    "rgd",
    "goals",
]

PARSER_EXECUTION_ORDER = (
    "lineups",
    "periods_phase",
    "distances",
    "events",
    "periods",
    "substitutions",
    "team_distance",
    "player_distance",
    "rgd",
    "goals",
    "fitness",
)

PARSER_FILE_TYPES = {
    "lineups": ("metadata",),
    "periods_phase": ("metadata", "rgd"),
    "distances": ("distance_covered",),
    "events": ("metadata", "rgd"),
    "fitness": ("fitness_entities",),
    "periods": ("metadata",),
    "substitutions": ("metadata",),
    "team_distance": ("distance_covered",),
    "player_distance": ("distance_covered",),
    "rgd": ("rgd",),
    "goals": ("rgd",),
}

PARSER_CONFLICTS = (
    ("periods_phase", "periods"),
    ("periods_phase", "rgd"),
    ("distances", "team_distance"),
    ("distances", "player_distance"),
    ("events", "substitutions"),
    ("events", "rgd"),
)


def normalize_parser_selection(parser_names: list[str]) -> list[str]:
    if not parser_names:
        raise ValueError("Select at least one parser.")

    unknown = set(parser_names).difference(PARSER_EXECUTION_ORDER)
    if unknown:
        raise ValueError(f"Unknown parser selection: {', '.join(sorted(unknown))}")
    if "goals" in parser_names and len(set(parser_names)) > 1:
        raise ValueError(
            "The Goals-only parser cannot be combined with other parsers."
        )
    selected = set(parser_names)
    for left, right in PARSER_CONFLICTS:
        if left in selected and right in selected:
            raise ValueError(
                f"The {left} and {right} parsers overlap and cannot be combined."
            )

    return [
        parser_name
        for parser_name in PARSER_EXECUTION_ORDER
        if parser_name in parser_names
    ]


def required_file_types(parser_names: list[str]) -> set[str]:
    return {
        file_type
        for parser_name in parser_names
        for file_type in PARSER_FILE_TYPES[parser_name]
    }
