from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NdviObservationInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    plot_id: str
    scene_id: str = Field(min_length=1, max_length=255)
    observed_on: date
    ndvi_plot: float = Field(ge=-1, le=1)
    ndvi_control: float = Field(ge=-1, le=1)
    valid_px_plot: int = Field(ge=0)
    valid_px_control: int = Field(ge=0)
    source: Literal["sentinel-2", "synthetic_demo", "manual"] = "sentinel-2"
    metadata: dict = Field(default_factory=dict)
