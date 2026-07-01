-- Harvest Oak Vision Engine — Database Schema
-- TimescaleDB + PostgreSQL 15

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Raw piece crossing events
CREATE TABLE IF NOT EXISTS piece_events (
    timestamp       TIMESTAMPTZ NOT NULL,
    camera_id       TEXT        DEFAULT 'cam_01',
    direction       TEXT,           -- 'forward' | 'reverse'
    confidence      FLOAT,
    line_speed_fpm  FLOAT,
    shift_id        INT
);
SELECT create_hypertable('piece_events', 'timestamp', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_piece_events_shift ON piece_events (shift_id, timestamp DESC);

-- Downtime events
CREATE TABLE IF NOT EXISTS downtime_events (
    id               SERIAL PRIMARY KEY,
    start_ts         TIMESTAMPTZ NOT NULL,
    end_ts           TIMESTAMPTZ,
    duration_seconds INT,
    state            TEXT,           -- 'IDLE' | 'SLOW' | 'UNKNOWN'
    snapshot_path    TEXT,
    shift_id         INT
);
CREATE INDEX IF NOT EXISTS idx_downtime_shift ON downtime_events (shift_id);
CREATE INDEX IF NOT EXISTS idx_downtime_start  ON downtime_events (start_ts DESC);

-- 1-minute production rollup (hypertable for efficient time queries)
CREATE TABLE IF NOT EXISTS production_metrics (
    timestamp        TIMESTAMPTZ NOT NULL,
    pieces_count     INT         DEFAULT 0,
    avg_speed_fpm    FLOAT,
    downtime_seconds INT         DEFAULT 0,
    state            TEXT,
    shift_id         INT
);
SELECT create_hypertable('production_metrics', 'timestamp', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_metrics_shift ON production_metrics (shift_id, timestamp DESC);

-- Shifts
CREATE TABLE IF NOT EXISTS shifts (
    id                      SERIAL PRIMARY KEY,
    label                   TEXT,
    start_ts                TIMESTAMPTZ NOT NULL,
    end_ts                  TIMESTAMPTZ,
    total_pieces            INT     DEFAULT 0,
    total_downtime_seconds  INT     DEFAULT 0,
    avg_speed_fpm           FLOAT,
    peak_hour               INT,        -- hour of day with most pieces
    peak_hour_pieces        INT,
    oee_availability        FLOAT,      -- uptime / planned_time
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- Calibration log
CREATE TABLE IF NOT EXISTS calibration (
    id                    SERIAL PRIMARY KEY,
    conveyor_visible_feet FLOAT NOT NULL,
    pixels_per_foot       FLOAT,
    frame_width           INT,
    frame_height          INT,
    set_at                TIMESTAMPTZ DEFAULT NOW()
);

-- Settings key-value store (for runtime configuration via API)
CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed default settings
INSERT INTO settings (key, value) VALUES
    ('detection_line_y_percent',    '50'),
    ('min_contour_area',            '2000'),
    ('count_cooldown_ms',           '800'),
    ('conveyor_visible_feet',       '8.0'),
    ('downtime_threshold_seconds',  '45'),
    ('target_pieces_per_hour',      '450'),
    ('shift_day_start',             '06:00'),
    ('shift_aft_start',             '14:00'),
    ('shift_night_start',           '22:00'),
    ('debug_overlay',               'false')
ON CONFLICT (key) DO NOTHING;
