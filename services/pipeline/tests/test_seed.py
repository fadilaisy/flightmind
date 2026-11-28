"""fixtures/seed.sql matches contracts/schema.sql, is safe to load twice, and is reproducible (SCRUM-22).

No database: the file is parsed as text, and the generator is re-run in memory.
"""

import importlib.util
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SEED = REPO / "fixtures" / "seed.sql"
SCHEMA = REPO / "contracts" / "schema.sql"
GENERATOR = REPO / "services" / "pipeline" / "scripts" / "make_seed.py"

INSERT = re.compile(
    r"^INSERT INTO (\w+) \(([^)]*)\)\nVALUES \(.*\)\nON CONFLICT DO NOTHING;$", re.MULTILINE
)


def _schema_columns() -> dict[str, set[str]]:
    tables: dict[str, set[str]] = {}
    for name, body in re.findall(r"CREATE TABLE (\w+) \((.*?)\n\);", SCHEMA.read_text(), re.S):
        cols = set()
        for line in body.splitlines():
            line = line.split("--")[0].strip()
            match = re.match(r"(\w+)\s+\w", line)
            if match and match.group(1).upper() not in {"PRIMARY", "UNIQUE", "CHECK"}:
                cols.add(match.group(1))
        tables[name] = cols
    return tables


def _generator():
    spec = importlib.util.spec_from_file_location("make_seed", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_seed_is_one_transaction_with_a_header_comment() -> None:
    text = SEED.read_text(encoding="utf-8")
    assert text.startswith("-- FlightMind fixture seed.")
    lines = [ln for ln in text.splitlines() if ln and not ln.startswith("--")]
    assert lines[0] == "BEGIN;"
    assert lines[-1] == "COMMIT;"


def test_every_statement_is_an_insert_on_conflict_do_nothing_into_a_schema_table() -> None:
    text = SEED.read_text(encoding="utf-8")
    schema = _schema_columns()
    statements = INSERT.findall(text)
    assert statements
    # Nothing else is in the file besides comments, blank lines, BEGIN and COMMIT.
    rest = INSERT.sub("", text)
    other = [ln for ln in rest.splitlines() if ln and not ln.startswith("--")]
    assert other == ["BEGIN;", "COMMIT;"]
    tables = set()
    for table, columns in statements:
        assert table in schema, table
        cols = {c.strip() for c in columns.split(",")}
        assert cols <= schema[table], (table, cols - schema[table])
        tables.add(table)
    assert {"recording_files", "telemetry"} <= tables
    assert tables <= {"recording_files", "telemetry", "events", "quarantine"}


def test_event_records_are_in_telemetry() -> None:
    text = SEED.read_text(encoding="utf-8")
    telemetry_refs = set(re.findall(r"'(adsb_sample_500:\d+)', \d+, ", text))
    events = re.findall(r"^INSERT INTO events .*?\nVALUES \((.*)\)\nON CONFLICT", text, re.M)
    for values in events:
        refs = re.findall(r"'(adsb_sample_500:\d+)'", values)
        assert refs and set(refs) <= telemetry_refs
    if not events:
        assert "no events" in text


def test_seed_is_what_the_generator_writes() -> None:
    assert SEED.read_text(encoding="utf-8") == _generator().build_seed()
