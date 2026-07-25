-- PostgreSQL target schema. The local pipeline writes CSVs first; load these into
-- the matching tables when a PostgreSQL connection is configured.
CREATE TABLE IF NOT EXISTS real_sector_observations (
    id BIGSERIAL PRIMARY KEY,
    sector TEXT NOT NULL,
    subsector TEXT NOT NULL,
    indicator_name TEXT NOT NULL,
    date DATE NOT NULL,
    region_state TEXT,
    value DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL,
    frequency TEXT NOT NULL,
    source TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (sector, subsector, indicator_name, date, region_state)
);
CREATE INDEX IF NOT EXISTS idx_real_sector_lookup
    ON real_sector_observations (sector, indicator_name, date DESC);
