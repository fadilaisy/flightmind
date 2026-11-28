-- FlightMind contracts v1.1 (2026-11-12): recorded CAT021 pivot.
-- v1.2 (2026-11-27, SCRUM-62): uploads and quarantine tables, additive only.
-- Change only through a PR that also edits .kiro/steering/data-contracts.md.
-- raw_ref format: '<recording_file_id>:<record_index>'. For an upload, recording_file_id is uploads.id.

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

-- C4: one embedding per event story.
-- Model: Google gemini-embedding-001 at output_dimensionality=1024, L2-normalized.
CREATE TABLE event_embeddings (
  event_id    uuid PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
  story       text NOT NULL,
  model       text NOT NULL,
  embedding   vector(1024) NOT NULL        -- gemini-embedding-001 @ 1024
);

-- C7 (v1.2, Role 3): one row per uploaded recording, from POST /api/recordings to ready.
-- Mirrors the Recording schema in openapi.yaml. Events stay keyed by raw_ref prefix
-- ('<id>:'), so the events table does not change.
CREATE TABLE uploads (
  id              text PRIMARY KEY,          -- 'r' + 10 random hex digits
  filename        text NOT NULL,
  sha256          text,                      -- set at complete; see uploads_sha256_ok below
  size_bytes      bigint NOT NULL,
  bytes_received  bigint NOT NULL DEFAULT 0,
  format          text NOT NULL,             -- pcap | pcapng | asterix_raw
  recording_date  date,                      -- only for raw .atx/.ast/.bin files
  path            text NOT NULL,             -- where the bytes are kept on disk
  status          text NOT NULL DEFAULT 'uploading',
                  -- uploading | scanning | scanned | queued | decoding | filtering | detecting | storing | ready | failed
  streams         jsonb,                     -- RecordingStream[], set when scanned
  stream_id       text,                      -- the stream chosen in POST .../process
  records_done    integer,
  records_total   integer,
  error           text,                      -- one plain sentence when failed
  report          jsonb,                     -- recipe and counts when ready
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

-- The same file twice returns the first upload, unless that one failed (then it can be retried).
CREATE UNIQUE INDEX uploads_sha256_ok ON uploads (sha256) WHERE status <> 'failed';
CREATE INDEX uploads_created_idx ON uploads (created_at);

-- C8 (v1.2, Role 2): records the cleaning set aside, with the step and reason.
CREATE TABLE quarantine (
  recording_id  text NOT NULL,
  raw_ref       text NOT NULL,
  step_code     text NOT NULL,             -- duplicates | position_jumps | altitude_spikes | fragments
  reason        text NOT NULL,
  PRIMARY KEY (recording_id, raw_ref)
);
