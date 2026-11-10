import math
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PlantingInput(BaseModel):
    species_code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Z0-9_-]+$")
    trees_planted: int = Field(gt=0, le=1_000_000)
    planted_on: date

    @field_validator("planted_on")
    @classmethod
    def planted_not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Planting date cannot be in the future.")
        return value


class PlotGeometry(BaseModel):
    type: Literal["Polygon", "MultiPolygon"]
    coordinates: list[Any]

    @model_validator(mode="after")
    def validate_positions(self) -> "PlotGeometry":
        def ring_is_valid(ring: Any) -> bool:
            if not isinstance(ring, list) or len(ring) < 4:
                return False
            positions: list[tuple[float, float]] = []
            for position in ring:
                if (
                    not isinstance(position, list)
                    or len(position) < 2
                    or not isinstance(position[0], (float, int))
                    or not isinstance(position[1], (float, int))
                    or not math.isfinite(position[0])
                    or not math.isfinite(position[1])
                    or not -180 <= position[0] <= 180
                    or not -90 <= position[1] <= 90
                ):
                    return False
                positions.append((float(position[0]), float(position[1])))
            return positions[0] == positions[-1]

        polygons = [self.coordinates] if self.type == "Polygon" else self.coordinates
        if not isinstance(polygons, list) or not polygons:
            raise ValueError("Geometry must contain at least one polygon ring.")
        for polygon in polygons:
            if (
                not isinstance(polygon, list)
                or not polygon
                or not all(ring_is_valid(ring) for ring in polygon)
            ):
                raise ValueError("Polygon rings must be closed and contain valid longitude/latitude positions.")
        return self

    def as_geojson(self) -> dict[str, Any]:
        return {"type": self.type, "coordinates": self.coordinates}


class PlotCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    geometry: PlotGeometry
    plantings: list[PlantingInput] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def prevent_duplicate_plantings(self) -> "PlotCreate":
        unique = {(item.species_code, item.planted_on) for item in self.plantings}
        if len(unique) != len(self.plantings):
            raise ValueError("Each species and planting date combination may appear only once.")
        return self


class PlotPreflight(BaseModel):
    geometry: PlotGeometry


class PlotSubmitResponse(BaseModel):
    plot_id: str
    status: str
    submitted_at: str
