"""Parser identifiers and JSON file dependencies for manual round scraping."""

from typing import Literal, TypeAlias


ParserName: TypeAlias = Literal[
    "lineups",
    "periods",
    "substitutions",
    "team_distance",
    "player_distance",
    "rgd",
    "goals",
    "fitness",
]

PARSER_EXECUTION_ORDER = (
    "lineups",
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
    "periods": ("metadata",),
    "substitutions": ("metadata",),
    "team_distance": ("distance_covered",),
    "player_distance": ("distance_covered",),
    "rgd": ("rgd",),
    "goals": ("rgd",),
    "fitness": ("fitness_entities",),
}


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
