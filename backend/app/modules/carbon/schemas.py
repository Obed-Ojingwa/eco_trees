from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EstimateRunRequest(BaseModel):
    as_of: date | None = None
    plot_ids: list[UUID] | None = Field(default=None, max_length=500)

    @field_validator("plot_ids")
    @classmethod
    def unique_plot_ids(cls, value: list[UUID] | None) -> list[UUID] | None:
        if value is not None and len(set(value)) != len(value):
            raise ValueError("plot_ids cannot contain duplicates.")
        return value


class BatchCreateRequest(BaseModel):
    estimate_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=500)

    @field_validator("estimate_ids")
    @classmethod
    def unique_estimate_ids(cls, value: list[UUID] | None) -> list[UUID] | None:
        if value is not None and len(set(value)) != len(value):
            raise ValueError("estimate_ids cannot contain duplicates.")
        return value


class BatchDecisionOverride(BaseModel):
    plot_id: UUID
    flags: list[str] = Field(min_length=1, max_length=20)
    note: str = Field(min_length=3, max_length=2000)

    @field_validator("flags")
    @classmethod
    def unique_flags(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("An override cannot repeat the same flag.")
        return value


class AuditorDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str = Field(min_length=3, max_length=2000)
    overrides: list[BatchDecisionOverride] = Field(default_factory=list, max_length=100)

    @field_validator("overrides")
    @classmethod
    def unique_override_plots(
        cls,
        value: list[BatchDecisionOverride],
    ) -> list[BatchDecisionOverride]:
        plot_ids = [item.plot_id for item in value]
        if len(set(plot_ids)) != len(plot_ids):
            raise ValueError("A plot can have only one override entry per decision.")
        return value


class SurvivalOverrideRequest(BaseModel):
    survival: Decimal = Field(ge=0, le=1)
    note: str = Field(min_length=3, max_length=2000)


class PlotVerificationRequest(BaseModel):
    decision: Literal["verified", "rejected"]
    note: str = Field(min_length=3, max_length=2000)


class ListingPriceRequest(BaseModel):
    price_per_tonne_kobo: int = Field(gt=0, le=10**12)


class CarbonParametersResponse(BaseModel):
    version: str
    is_placeholder: bool
    buffer_pct: str
    satellite_multipliers: dict[str, str]
    source_citation: str | None
    notes: str
    species: list[dict]


class CarbonErrorDetails(BaseModel):
    message: str
