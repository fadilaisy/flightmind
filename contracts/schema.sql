-- FlightMind contracts v1.1 (2026-11-12): recorded CAT021 pivot.
-- Change only through a PR that also edits .kiro/steering/data-contracts.md.
-- raw_ref format: '<recording_file_id>:<record_index>'

CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS vector;

-- Recording files we ingested. Raw bytes stay in the file (data/ or object storage);
-- GET /api/raw/{raw_ref} reads them from here on demand.
CREATE TABLE recording_files (
  id            text PRIMARY KEY,          -- short stable id, used in raw_ref
  uri           text NOT NULL,             -- path or object-storage URI
  sha256        text NOT NULL,
  size_bytes    bigint NOT NULL,
  record_count  integer,
  first_ts      timestamptz,
  last_ts       timestamptz,
  ingested_at   timestamptz NOT NULL DEFAULT now()
);

-- C1: one clean CAT021 point per row (after compression, only the points we keep).
CREATE TABLE telemetry (
  ts            timestamptz NOT NULL,
  icao24        text NOT NULL,             -- 6 hex chars
  callsign      text,
  lat           double precision,
  lon           double precision,
  baro_alt_ft   integer,
  geo_alt_ft    integer,
  gs_kt         real,
  track_deg     real,
  vrate_fpm     integer,
  squawk        text,                      -- Mode 3/A, 4 octal digits
  on_ground     boolean,
  sac           smallint,                  -- new in v1.1
  sic           smallint,                  -- new in v1.1
  track_number  integer,                   -- new in v1.1
  raw_ref       text NOT NULL,             -- new in v1.1
  raw_offset    bigint,                    -- byte offset of the record in its file
  flags         text[] NOT NULL DEFAULT '{}',  -- e.g. {'kept_for_event'}
  PRIMARY KEY (icao24, ts, raw_ref)        -- must include ts for a hypertable
);
SELECT create_hypertable('telemetry', 'ts');
CREATE INDEX telemetry_raw_ref_idx ON telemetry (raw_ref);

-- C2: OPTIONAL (cut list). Unchanged from v1; build nothing that requires it.
CREATE TABLE weather_reports (
  id          bigserial PRIMARY KEY,
  station     text NOT NULL,
  kind        text NOT NULL,               -- METAR | TAF | SIGMET | PIREP
  issued_ts   timestamptz,
  valid_from  timestamptz,
  valid_to    timestamptz,
  raw_text    text NOT NULL,
  decoded     jsonb
);

-- C3: one row per detected event.
CREATE TABLE events (
  id          uuid PRIMARY KEY,
  type        text NOT NULL,               -- go_around | holding | squawk_7500 | squawk_7600 | squawk_7700
  icao24      text NOT NULL,
  callsign    text,
  start_ts    timestamptz NOT NULL,
  end_ts      timestamptz NOT NULL,
  airport     text,
  lat         double precision,
  lon         double precision,
  severity    smallint,
  details     jsonb NOT NULL DEFAULT '{}',
  raw_refs    text[] NOT NULL              -- every record the detector used (was telemetry_ids)
);
CREATE INDEX events_start_idx ON events (start_ts);

CREATE FUNCTION notify_events_new() RETURNS trigger AS $$
BEGIN
  PERFORM pg_notify('events_new', NEW.id::text);
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER events_new_trg AFTER INSERT ON events
  FOR EACH ROW EXECUTE FUNCTION notify_events_new();

-- C4: one embedding per event story. Dimension set when Role 3 picks the model.
CREATE TABLE event_embeddings (
  event_id    uuid PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
  story       text NOT NULL,
  model       text NOT NULL,
  embedding   vector(1024) NOT NULL        -- TODO(Role 3): match the chosen model
);
