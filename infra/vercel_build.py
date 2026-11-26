"""Vercel build step (SCRUM-38): build the web UI and copy it next to the API code.

Runs `npm ci` and `npm run build` in web/, then replaces services/intel/web_dist with a copy
of web/dist. The Vercel function serves that folder itself (infra/vercel_entry.py). A root
public/ folder is not used: Vercel only publishes public/ files that exist before the build,
so a build on Vercel from Git left the site without its page (2026-11-26). Standard library only; works on Windows and Linux.

    python infra/vercel_build.py
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
DIST = WEB / "dist"
TARGET = ROOT / "services" / "intel" / "web_dist"


def main() -> int:
    npm = shutil.which("npm")
    if npm is None:
        print("vercel_build: npm was not found on PATH. Install Node.js 22 (with npm) and retry.", file=sys.stderr)
        return 1

    # WORKAROUND, not a design: the web client has no same-origin mode (an empty
    # VITE_API_BASE selects the in-browser fixture). "/." makes the browser turn
    # "/./api/meta" into "/api/meta" on whatever host serves the page. Remove when
    # Role 1 adds a same-origin base (requirements.md, Open item 2).
    env = dict(os.environ, VITE_API_BASE="/.")

    for args in (["ci"], ["run", "build"]):
        print(f"vercel_build: npm {' '.join(args)} (in {WEB})", flush=True)
        result = subprocess.run([npm, *args], cwd=WEB, env=env)
        if result.returncode != 0:
            print(f"vercel_build: 'npm {' '.join(args)}' failed with exit code {result.returncode}.", file=sys.stderr)
            return result.returncode or 1

    if not (DIST / "index.html").is_file():
        print(f"vercel_build: {DIST / 'index.html'} does not exist after the build.", file=sys.stderr)
        return 1

    if TARGET.exists():
        shutil.rmtree(TARGET)
    shutil.copytree(DIST, TARGET)
    count = sum(1 for p in TARGET.rglob("*") if p.is_file())
    print(f"vercel_build: copied {DIST} to {TARGET} ({count} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
