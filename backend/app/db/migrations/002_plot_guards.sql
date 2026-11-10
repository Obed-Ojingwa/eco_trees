CREATE INDEX plots_geom_gix ON plots USING gist (geom);
CREATE INDEX plots_farmer_created_idx ON plots (farmer_id, created_at DESC);
CREATE INDEX plantings_plot_idx ON plantings (plot_id);
CREATE INDEX photos_plot_created_idx ON plot_photos (plot_id, created_at DESC);
CREATE INDEX ndvi_plot_date_idx ON ndvi_observations (plot_id, observed_on);
CREATE INDEX notifications_farmer_created_idx ON notifications (farmer_id, created_at DESC);
CREATE INDEX xp_events_farmer_created_idx ON xp_events (farmer_id, created_at DESC);

CREATE OR REPLACE FUNCTION guard_plot_geometry() RETURNS trigger AS $$
DECLARE
    calculated_area_ha double precision;
    overlap_area_m2 double precision;
BEGIN
    PERFORM pg_advisory_xact_lock(71024019);

    IF ST_SRID(NEW.geom) <> 4326
       OR GeometryType(NEW.geom) NOT IN ('POLYGON', 'MULTIPOLYGON')
       OR NOT ST_IsValid(NEW.geom)
       OR ST_IsEmpty(NEW.geom) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'INVALID_GEOMETRY';
    END IF;

    calculated_area_ha := ST_Area(NEW.geom::geography) / 10000.0;
    IF calculated_area_ha < COALESCE(
           NULLIF(current_setting('ecotrees.min_plot_area_ha', true), '')::double precision,
           0.01
       )
       OR calculated_area_ha > COALESCE(
           NULLIF(current_setting('ecotrees.max_plot_area_ha', true), '')::double precision,
           1000
       ) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'AREA_OUT_OF_RANGE';
    END IF;
    NEW.area_ha := calculated_area_ha;

    SELECT ST_Area(ST_Intersection(existing.geom::geography, NEW.geom::geography))
      INTO overlap_area_m2
      FROM plots AS existing
     WHERE existing.id <> NEW.id
       AND existing.status <> 'rejected'
       AND existing.geom && NEW.geom
       AND ST_Intersects(existing.geom, NEW.geom)
       AND ST_Area(ST_Intersection(existing.geom::geography, NEW.geom::geography)) > 0.01
     LIMIT 1;

    IF overlap_area_m2 IS NOT NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'PLOT_OVERLAP';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER plots_geometry_guard
BEFORE INSERT OR UPDATE OF geom ON plots
FOR EACH ROW EXECUTE FUNCTION guard_plot_geometry();
