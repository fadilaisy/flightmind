-- SCRUM-31: ensure the extensions exist before contracts/schema.sql runs.
-- schema.sql already does CREATE EXTENSION IF NOT EXISTS for both, but running
-- them here first keeps the stack working even if the schema file is swapped
-- for one that assumes the extensions are already present.
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS vector;
