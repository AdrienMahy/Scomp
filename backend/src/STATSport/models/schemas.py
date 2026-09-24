"""Typed view of the observed STATSports V7 full-session response."""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StatsportPlayerDetails(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    display_name: str | None = Field(default=None, alias="displayName")
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    primary_position: str | None = Field(default=None, alias="primaryPosition")
    secondary_position: str | None = Field(default=None, alias="secondaryPosition")
    active_squad_name: str | None = Field(default=None, alias="activeSquadName")
    custom_player_id: str | None = Field(default=None, alias="customPlayerId")
    date_of_birth: datetime | None = Field(default=None, alias="dateOfBirth")
    gender: int | str | None = None
    height: float | None = None
    weight: float | None = None
    max_accel: float | None = Field(default=None, alias="maxAccel")
    max_decel: float | None = Field(default=None, alias="maxDecel")
    max_heart_rate: float | None = Field(default=None, alias="maxHeartRate")
    max_speed: float | None = Field(default=None, alias="maxSpeed")
    resting_heart_rate: float | None = Field(default=None, alias="restingHeartRate")
    running_symmetry: float | None = Field(default=None, alias="runningSymmetry")
    short_name: str | None = Field(default=None, alias="shortName")


class StatsportDrill(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: UUID
    session_player_data_id: UUID | None = Field(default=None, alias="sessionPlayerDataId")
    primary_label: str | None = Field(default=None, alias="primaryLabel")
    secondary_label: str | None = Field(default=None, alias="secondaryLabel")
    tertiary_label: str | None = Field(default=None, alias="tertiaryLabel")
    free_text: str | None = Field(default=None, alias="freeText")
    drill_name: str | None = Field(default=None, alias="drillName")
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    session_type: str | None = Field(default=None, alias="sessionType")
    drill_kpi: dict[str, Any] | None = Field(default=None, alias="drillKpi")


class StatsportSessionPlayer(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: UUID
    raw_data_id: UUID | None = Field(default=None, alias="rawDataId")
    player_details: StatsportPlayerDetails = Field(alias="playerDetails")
    drills: list[StatsportDrill] = Field(default_factory=list)


class StatsportSessionDetails(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    squad_id: UUID | None = Field(default=None, alias="squadId")
    session_date: datetime = Field(alias="sessionDate")
    start_time: datetime = Field(alias="startTime")
    end_time: datetime = Field(alias="endTime")
    session_type: str | None = Field(default=None, alias="sessionType")


class StatsportActivity(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    session_details: StatsportSessionDetails = Field(alias="sessionDetails")
    session_players: list[StatsportSessionPlayer] = Field(
        default_factory=list,
        alias="sessionPlayers",
    )
