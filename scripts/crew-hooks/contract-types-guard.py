#!/usr/bin/env python3
"""Kiro Crew Stop hook: keep contracts/types.ts in step with contracts/openapi.yaml.

Crew runs this after every Kiro Agent turn (event "Stop"). If the agent changed
contracts/openapi.yaml but did not regenerate contracts/types.ts, the hook prints
{"decision": "block", "reason": ...} so the agent takes one more turn and runs the
generator. Otherwise it prints nothing and the turn ends normally.

Setup (Crew dashboard, Agent Capabilities -> Hooks -> New Hook):
  Event:   Stop
  Command: python <absolute path to repo>/scripts/crew-hooks/contract-types-guard.py <absolute path to repo>

The repo path is passed as an argument because Crew's docs do not say which folder a
hook runs in. Crew has no documented loop guard for Stop hooks, so this script blocks
at most once for the same contract state (see STATE_FILE).

Exit code is always 0: per the Crew docs, a Stop hook must exit 0 for its JSON to count,
and any problem here must never stop the agent from finishing.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

OPENAPI = "contracts/openapi.yaml"
TYPES = "contracts/types.ts"
GENERATE = "npx --yes openapi-typescript@7 contracts/openapi.yaml -o contracts/types.ts"
STATE_FILE = os.path.join(tempfile.gettempdir(), "flightmind-contract-types-guard.json")


def changed_since_head(repo, path):
    """True if the file differs from HEAD (staged or not)."""
    r = subprocess.run(
        ["git", "-C", repo, "diff", "--quiet", "HEAD", "--", path],
        capture_output=True,
    )
    return r.returncode == 1


def file_hash(repo, path):
    try:
        with open(os.path.join(repo, path), "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return "missing"


def needs_regeneration(repo):
    if not changed_since_head(repo, OPENAPI):
        return False
    if not changed_since_head(repo, TYPES):
        return True
    # Both changed: types.ts must be newer than openapi.yaml.
    spec_mtime = os.path.getmtime(os.path.join(repo, OPENAPI))
    types_mtime = os.path.getmtime(os.path.join(repo, TYPES))
    return types_mtime < spec_mtime


def already_blocked(state_key):
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f).get("last_blocked") == state_key
    except (OSError, ValueError):
        return False


def remember_block(state_key):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_blocked": state_key}, f)
    except OSError:
        pass


def main():
    repo = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.getcwd())
    if not os.path.isfile(os.path.join(repo, OPENAPI)):
        return  # wrong folder or not this repo: stay silent
    if not needs_regeneration(repo):
        return
    state_key = file_hash(repo, OPENAPI) + ":" + file_hash(repo, TYPES)
    if already_blocked(state_key):
        return  # asked once for this exact state; do not loop
    remember_block(state_key)
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"{OPENAPI} changed but {TYPES} was not regenerated. "
            f"From the repo root run: {GENERATE} . Never edit {TYPES} by hand. "
            "Then finish your answer."
        ),
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # never break the agent's turn
        pass
    sys.exit(0)
