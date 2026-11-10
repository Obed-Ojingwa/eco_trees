import argparse
import logging
import os
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

import httpx
import numpy as np
import planetary_computer
import stackstac
from pystac_client import Client
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.transform import from_origin
from rasterio.warp import transform_geom
from shapely.geometry import shape
from shapely.ops import unary_union


STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
logger = logging.getLogger("ndvi_ingest")


def _projected_crs(longitude: float, latitude: float) -> int:
    zone = min(60, max(1, int((longitude + 180) // 6) + 1))
    return (32600 if latitude >= 0 else 32700) + zone


def _scale_offset(asset: Any) -> tuple[float, float]:
    bands = asset.extra_fields.get("raster:bands", [])
    if not bands:
        raise ValueError(f"STAC asset {asset.href!r} is missing raster:bands scale metadata.")
    band = bands[0]
    return float(band.get("scale", 1.0)), float(band.get("offset", 0.0))


def _mask(geometry: Any, x: np.ndarray, y: np.ndarray, resolution: float) -> np.ndarray:
    height, width = len(y), len(x)
    transform_grid = from_origin(x[0] - resolution / 2, y[0] + resolution / 2, resolution, resolution)
    return geometry_mask(
        [geometry.__geo_interface__],
        out_shape=(height, width),
        transform=transform_grid,
        invert=True,
        all_touched=False,
    )


def _scene_items(
    geometry: dict,
    planted_on: date,
    today: date,
    cloud_limit: float,
) -> list[Any]:
    plot = shape(geometry)
    catalog = Client.open(STAC_URL)
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=plot.bounds,
        datetime=f"{planted_on - timedelta(days=365)}/{today}",
        query={"eo:cloud_cover": {"lt": cloud_limit}},
    )
    by_day: dict[date, list[Any]] = defaultdict(list)
    for item in search.items():
        if not item.datetime:
            continue
        by_day[item.datetime.date()].append(item)
    selected = [
        min(
            scenes,
            key=lambda item: float(item.properties.get("eo:cloud_cover", 100)),
        )
        for _, scenes in sorted(by_day.items())
    ]
    return [planetary_computer.sign_inplace(item) for item in selected]


def _process_plot(
    plot: dict,
    all_geometries: list[dict],
    api: httpx.Client,
    ingest_token: str,
    cloud_limit: float,
    min_valid_pixels: int,
    dry_run: bool,
) -> int:
    geometry = plot["geometry"]
    plot_shape = shape(geometry)
    longitude, latitude = plot_shape.centroid.x, plot_shape.centroid.y
    epsg = _projected_crs(longitude, latitude)
    plot_projected = shape(transform_geom("EPSG:4326", f"EPSG:{epsg}", geometry))
    plot_zone = plot_projected.buffer(-10)
    if plot_zone.is_empty:
        logger.info("Skipping %s: plot is too small for an inward buffer", plot["id"])
        return 0

    other_plots = [
        shape(transform_geom("EPSG:4326", f"EPSG:{epsg}", item))
        for item in all_geometries
        if item != geometry
    ]
    control = plot_projected.buffer(100).difference(plot_projected.buffer(20))
    if other_plots:
        control = control.difference(unary_union(other_plots))
    if control.is_empty:
        logger.info("Skipping %s: no registered-plot-free control ring", plot["id"])
        return 0
    bounds = plot_projected.buffer(100).bounds

    items = _scene_items(
        geometry,
        date.fromisoformat(plot["planted_on"]),
        date.today(),
        cloud_limit,
    )
    ingested = 0
    for item in items:
        stack = stackstac.stack(
            [item],
            assets=["B04", "B08", "SCL"],
            epsg=epsg,
            resolution=10,
            bounds=bounds,
            resampling=Resampling.nearest,
            dtype="float32",
            fill_value=np.nan,
            chunksize=1024,
        ).compute()
        red = np.asarray(stack.sel(band="B04").values[0], dtype=np.float32)
        nir = np.asarray(stack.sel(band="B08").values[0], dtype=np.float32)
        scl = np.asarray(stack.sel(band="SCL").values[0])
        red_scale, red_offset = _scale_offset(item.assets["B04"])
        nir_scale, nir_offset = _scale_offset(item.assets["B08"])
        red = red * red_scale + red_offset
        nir = nir * nir_scale + nir_offset
        valid = np.isin(scl, [4, 5]) & np.isfinite(red) & np.isfinite(nir)
        denominator = nir + red
        valid &= denominator != 0
        ndvi = np.full(red.shape, np.nan, dtype=np.float32)
        ndvi[valid] = (nir[valid] - red[valid]) / denominator[valid]
        x = np.asarray(stack.coords["x"].values)
        y = np.asarray(stack.coords["y"].values)
        resolution = float(abs(x[1] - x[0])) if len(x) > 1 else 10.0
        plot_mask = _mask(plot_zone, x, y, resolution)
        control_mask = _mask(control, x, y, resolution)
        valid_plot = plot_mask & np.isfinite(ndvi)
        valid_control = control_mask & np.isfinite(ndvi)
        plot_count = int(valid_plot.sum())
        control_count = int(valid_control.sum())
        if plot_count < min_valid_pixels or control_count < min_valid_pixels:
            continue

        payload = {
            "plot_id": plot["id"],
            "scene_id": item.id,
            "observed_on": item.datetime.date().isoformat(),
            "ndvi_plot": float(ndvi[valid_plot].mean()),
            "ndvi_control": float(ndvi[valid_control].mean()),
            "valid_px_plot": plot_count,
            "valid_px_control": control_count,
            "source": "sentinel-2",
            "metadata": {
                "collection": "sentinel-2-l2a",
                "eo_cloud_cover": item.properties.get("eo:cloud_cover"),
                "plot_pixel_resolution_m": resolution,
            },
        }
        if dry_run:
            logger.info(
                "Dry run %s %s: plot NDVI %.4f, control NDVI %.4f, valid pixels %d/%d",
                plot["id"],
                item.id,
                payload["ndvi_plot"],
                payload["ndvi_control"],
                plot_count,
                control_count,
            )
        else:
            response = api.post(
                "/api/internal/ndvi",
                headers={"X-Ingest-Token": ingest_token, "X-EcoTrees": "1"},
                json=payload,
            )
            response.raise_for_status()
        ingested += 1
    return ingested


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Sentinel-2 NDVI observations and send them to EcoTrees.")
    parser.add_argument("--api-base", default=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--cloud-limit", type=float, default=30)
    parser.add_argument("--min-valid-pixels", type=int, default=5)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calculate and report NDVI without uploading observations.",
    )
    args = parser.parse_args()
    api_token = os.getenv("INGEST_TOKEN")
    if not api_token:
        parser.error("Set INGEST_TOKEN in the environment.")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    with httpx.Client(base_url=args.api_base.rstrip("/"), timeout=60) as api:
        response = api.get(
            "/api/internal/plots",
            headers={"X-Ingest-Token": api_token},
        )
        response.raise_for_status()
        plots = response.json()["items"]
        geometries = [item["geometry"] for item in plots]
        total = 0
        for plot in plots:
            ingested = _process_plot(
                plot,
                geometries,
                api,
                api_token,
                args.cloud_limit,
                args.min_valid_pixels,
                args.dry_run,
            )
            logger.info("Plot %s: imported %d observation(s)", plot["id"], ingested)
            total += ingested
    logger.info("Imported %d observation(s) across %d plot(s)", total, len(plots))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
