# Requirements: SCRUM-38 deploy the public live URL in replay mode

Source: SCRUM-38 and the spec description. Owner: Role 3 (Zahran). Folders: `services/intel/`, `infra/`, a root `Dockerfile` and root `.dockerignore`, `.kiro/specs/api-deploy/`. Nothing under `web/`, `contracts/` or `services/pipeline/` is edited.

## Introduction

Judges must open one public URL, with no account and no credentials, and see FlightMind working in replay mode. The deadline is 2026-12-04 14:00 PT. The team target is 2026-12-03. The URL must stay up through judging.

The work has two phases.

- **Phase 1 (this ticket, built now).** One container on Railway serves the built web UI and the mock API (`mock_api.app:app`, synthetic data, no database) on one origin. Paths that start with `/api/` go to the API. Every other path is the static web build.
- **Phase 2 (written as open tasks, not built now).** A second Railway service runs Postgres with TimescaleDB and pgvector, loaded with `contracts/schema.sql` and the recorded CAT021 data. The web service switches to the real API. Phase 2 is blocked on SCRUM-37 (the real API) and on pipeline PR #11.

The API app is chosen by an environment variable, so the real API replaces the mock with no code change.

## Requirements

### 1. One public URL serves the UI and the API

**User story:** As a judge, I want to open one URL and use FlightMind, so that I need no account, no setup and no second address.

Acceptance criteria:
1. One container serves both the built web UI and the API on one origin and one port.
2. A request whose path starts with `/api/` goes to the API app. Every other path goes to the static web build, and `/` returns `index.html`.
3. The public URL needs no login, no token and no header. Phase 1 holds no credentials, so nothing goes in the private Devpost field yet.
4. The container listens on the port in the `PORT` environment variable (Railway sets it) and on `0.0.0.0`. When `PORT` is unset it uses 8000.
5. The public page works with the mock API's synthetic data: the event list loads, an event opens, its track draws, and a `raw_ref` opens through `/api/raw/{raw_ref}`.
6. The deployed server runs in replay mode: `GET /api/meta` returns `mode` = `replay`.

### 2. Routing module that leaves the API untouched

**User story:** As the Role 3 developer, I want a small entry module that does the routing, so that the mock API (and later the real API) is not changed to be deployed.

Acceptance criteria:
1. A new module `services/intel/serve.py` exposes an ASGI app named `app`. It is the only entry point the container starts.
2. `serve.py` does not mutate the imported API app. It does not call `app.mount`, add routes or add middleware on it. It does not edit anything under `services/intel/mock_api/`.
3. The API app is chosen by `FLIGHTMIND_API_APP`, in the form `module:attribute`. When it is unset or empty, the default is `mock_api.app:app`.
4. When `FLIGHTMIND_API_APP` names a module or attribute that cannot be imported, the server fails at start with a message that includes the value. It does not start with only the web UI.
5. The web build folder comes from `FLIGHTMIND_WEB_DIST`. When it is unset, empty, or the folder has no `index.html`, only the API is served and every non-API path answers 404.
6. A request for an unknown path under `/api/` is answered by the API app, so the 404 is the API's JSON error. A request for an unknown non-API path answers 404 from the static side.
7. FastAPI's `/docs`, `/redoc` and `/openapi.json` are not exposed publicly, because they do not start with `/api/`.
8. The API app's own startup and shutdown (lifespan) events still run, so the real API can open its database connection later.
9. `serve.py` does not read system time and does not touch the database.

### 3. One image that builds from a clean checkout

**User story:** As the Role 3 developer, I want one multi-stage image, so that Railway builds the same thing I run on my laptop.

Acceptance criteria:
1. A root `Dockerfile` builds the image. Railway detects it automatically. There is no `railway.json` and no `railway.toml`, because Railway's Config as Code is deprecated and stops being read on 2026-12-01.
2. Stage 1 uses `node:22-slim`, copies `web/` and `contracts/`, and runs `npm ci` and `npm run build` in `web/`. `contracts/` is copied because the web build needs `contracts/types.ts` at `../contracts` relative to `web/`.
3. Stage 2 uses `python:3.12-slim` and installs only runtime dependencies from `services/intel/requirements-serve.txt` (`fastapi`, `uvicorn`). Test and development packages (`pytest`, `mcp`, `httpx` and others in `requirements.txt`) are not in the image.
4. Stage 2 copies `services/intel/mock_api`, `services/intel/serve.py` and the built `dist` folder, and sets `FLIGHTMIND_WEB_DIST` to where `dist` is copied. It does not copy `data/`, `fixtures/`, tests, `.git`, `node_modules` or `.env` files.
5. The image runs as a non-root user.
6. The image starts with `uvicorn serve:app --host 0.0.0.0 --port ${PORT:-8000}`.
7. A root `.dockerignore` keeps `.git`, `data/`, `node_modules`, `.venv`, `__pycache__`, `.env*` and `.claude/` out of the build context.
8. The web build gets the build argument `VITE_API_BASE`, set to `/.` in the Dockerfile (see requirement 4).
9. A change in `requirements-serve.txt` or in `web/package-lock.json` is the only reason the dependency layers rebuild: dependency files are copied before source files.

### 4. The web client calls the API on the same origin

**User story:** As the Role 3 developer, I want the built UI to call the API on its own origin without editing `web/`, so that Role 1's folder stays untouched.

Acceptance criteria:
1. The web client builds URLs as `${VITE_API_BASE}${path}` and uses an in-browser fixture when `VITE_API_BASE` is empty. The image therefore builds with `VITE_API_BASE=/.`, so `/./api/meta` resolves in the browser to `/api/meta` on whatever host serves the page.
2. This is a workaround, and the Dockerfile and `infra/README.md` say so. The proper fix is in `web/` (Role 1) and is listed in Open items.
3. With the workaround, the page makes its calls to the API and does not show the in-browser fixture. This is checked against the running image in task 8.

### 5. Smoke check

**User story:** As the Role 3 developer, I want one command that says whether a deployment works, so that I can check the local image and the public URL the same way.

Acceptance criteria:
1. `infra/smoke.py` uses only the Python standard library and takes a base URL as its one argument.
2. It checks, in this order: `/` returns HTML; `/api/meta` returns JSON with `mode` = `replay`; `/api/events` returns a non-empty list; the first event's detail (`/api/events/{id}`) opens; the first `raw_ref` of that event opens (`/api/raw/{raw_ref}`, URL-encoded); and `/api/tracks/{icao24}` for that event's aircraft returns points.
3. It prints one line per passed check.
4. On the first failure it prints the failing URL and the reason, and exits with a non-zero code. It does not continue past the first failure.
5. When all checks pass it exits with code 0.
6. It sends no credentials, follows no redirect to another host, and has a 10 second timeout per request.
7. A trailing `/` on the base URL is accepted.

### 6. Deploy by `railway up`, written down

**User story:** As a teammate, I want the deploy steps in the repo, so that anyone on Role 3's side can redeploy or roll back during judging.

Acceptance criteria:
1. Deploy is by `railway up` from a clean checkout of `main`. No GitHub app on the repo is needed.
2. `infra/README.md` gets a new section "Deploy (SCRUM-38)" with these steps in order: login, create or link the project, deploy, generate the public domain, set the healthcheck path, smoke-check, redeploy, roll back.
3. The healthcheck path is `/api/meta`. It and the public domain are set once in the Railway service settings, and `infra/README.md` says where.
4. The section lists every setting that lives in Railway and not in the repo, so the repo plus that list is enough to rebuild the service.
5. The section records the public URL after task 9, with the date it was checked.
6. `services/intel/README.md` gets a short note that points to `serve.py`, the two environment variables, and the deploy section.
7. No secret appears in the repo. Phase 1 has none. Phase 2 secrets are named only by variable name.

### 7. Tests

**User story:** As the Role 3 developer, I want automated tests for the routing, so that a change to `serve.py` cannot break the public URL unnoticed.

Acceptance criteria:
1. Tests are in `services/intel/tests/test_serve.py`, use FastAPI's `TestClient`, and run with `python -m pytest -q` from `services/intel`. They use no network beyond localhost.
2. With a temporary dist folder: `/` returns its `index.html`, and a file under `/assets/` is served.
3. `/api/meta` through `serve.py` still validates against `contracts/openapi.yaml`.
4. An unknown `/api/...` path gives the API's 404 as JSON.
5. An unknown non-API path gives 404.
6. Without `FLIGHTMIND_WEB_DIST`, the API still works and `/` gives 404.
7. `FLIGHTMIND_API_APP` selects another app, and an invalid value fails with a message that includes it.
8. `/docs` and `/openapi.json` give 404 through `serve.py`.
9. Tests do not edit anything under `contracts/` or `mock_api/`, and existing tests still pass.

### 8. Stays up through judging

**User story:** As the PM, I want the URL to stay up until judging ends, so that no judge meets an error page.

Acceptance criteria:
1. The service stays deployed from the first public deploy until judging ends (deadline 2026-12-04 14:00 PT). The team target for the URL is 2026-12-03.
2. The Railway healthcheck is on, and the service restarts on failure.
3. The smoke check passes against the public URL on the day it is deployed, again on 2026-12-03, and again before 2026-12-04 14:00 PT. Each run is noted with its date in `infra/README.md`.
4. A rollback to the previous deployment is documented in `infra/README.md` and tried once before the 2026-12-03 target.
5. Railway plan and cost: see Open items.

### 9. Phase 2: real API and recorded data (not built now)

**User story:** As an analyst, I want the public URL to show the recorded CAT021 data, so that the live demo matches the product and not only the mock.

Acceptance criteria (each is a task marked "blocked on SCRUM-37" in `tasks.md`):
1. A second Railway service runs the `timescale/timescaledb-ha:pg16` image with a volume, loaded with `contracts/schema.sql` and the recorded CAT021 data.
2. The database service has no public domain. The web service reaches it over Railway's private network.
3. The web service sets `FLIGHTMIND_API_APP` to the real API's `module:attribute`. No code change in `serve.py`.
4. `DATABASE_URL`, `COARENA_API_KEY` and `GEMINI_API_KEY` live only in Railway variables, never in the repo, the image, the logs or the README.
5. CORS on the real API is restricted to the public origin. (The mock allows any origin; it is mock only.)
6. The raw recording file is available to `/api/raw/{raw_ref}` in the deployed service.
7. The smoke check passes against the public URL with real data, and the three demo questions of SCRUM-36 answer with citations in under 30 seconds each on the public URL.
8. A fallback is decided: if phase 2 is not working by 2026-12-02, the URL stays on phase 1 and the README says the public demo uses sample data.

## Rules this spec follows

- `tech.md`: Python 3.12 and type hints in `services/intel/`; `pytest` for tests; every service calls `clock.now()` and never reads system time (`serve.py` reads no time); `raw_ref` is never dropped (the dispatcher passes responses through unchanged); disclose third-party libraries and services in the README.
- `structure.md`: Role 3 owns `services/intel/` and `infra/`. This ticket also names a root `Dockerfile` and root `.dockerignore`. Those are files, not new top-level folders. Nothing under `web/`, `contracts/` or `services/pipeline/` is edited.
- `data-contracts.md`: C5 is the API. The deployed API serves the contract paths unchanged.

## Not in scope

- Any change to `web/`, `contracts/`, `services/pipeline/` or `mock_api/`.
- Building the real API (SCRUM-37), the pipeline load (PR #11) or the citation agent (SCRUM-36).
- Phase 2 work in this turn. It is listed as open tasks only.
- A custom domain, HTTPS setup beyond Railway's generated domain, login, rate limiting, caching, a CDN and monitoring beyond the healthcheck.
- A SPA fallback (serving `index.html` for unknown non-API paths). The UI is a single page at `/`. If task 8 finds the UI uses client-side routes, add the fallback then and update this spec.
- `railway.json` and `railway.toml`.

## Open items

1. **Label for the deployed mock data (Role 1 decides).** The public page shows the mock's synthetic data, but the UI's "Sample data" label only appears for the in-browser fixture. With `VITE_API_BASE=/.` the label will not show, so a judge could take synthetic data for a recording. Role 1 decides how the deployed mock is labelled (for example, a label driven by `/api/meta`). Until then the Devpost text and the README say the public demo uses sample data.
2. **Same-origin base in the client (Role 1).** The `VITE_API_BASE=/.` workaround exists because the client has no way to say "same origin". Role 1 should let `createApi` accept a same-origin base (for example `VITE_API_BASE=same-origin`, or an empty base meaning relative URLs plus a separate switch for the fixture). When that lands, remove the workaround from the Dockerfile.
3. **Railway plan and cost (Zahran).** Which plan keeps the service up through 2026-12-04 and what it costs is Zahran's account decision. A plan that sleeps or stops the service on a trial or credit limit is not acceptable. Phase 2 adds a database service and a volume, so the cost is checked again before phase 2.
4. **Test credentials.** Not needed in phase 1: there is no login. Nothing goes in the private Devpost field yet. Revisit if phase 2 adds any access control.
5. **Phase 2 data size and raw file.** How the recorded CAT021 file gets onto the Railway volume, and its size against the plan's volume limit, is decided when SCRUM-37 and PR #11 land.
