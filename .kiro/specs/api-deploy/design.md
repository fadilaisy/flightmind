# Design: SCRUM-38 deploy the public live URL in replay mode

Implements `requirements.md` in this folder. Decisions taken: one origin; routing in a small ASGI module that does not touch the API app; no `railway.json`. Host: Vercel since 2026-11-26 (first written for Railway; see the update below).

## Update after the host change (2026-11-26)

**Change.** The host for SCRUM-38 is now Vercel (free Hobby plan), not Railway. On 2026-11-26 Railway refused to create a project because the account trial had expired, Render refused a free service without a card on file (HTTP 402), and Azure for Students rejected the sign-up. Vercel runs a FastAPI app as one Vercel Function and serves static files from its CDN. Vercel does not run Dockerfiles, so the root `Dockerfile` and `.dockerignore` stay for local runs and container hosts, but the public URL is built by the Vercel Python runtime.

**Request flow.**

```
Judge's browser
      |  https://<name>.vercel.app
      v
Vercel
      |-- file exists in public/ (/, /assets/...)  --> CDN serves it (web build)
      '-- anything else                            --> one Vercel Function: infra/vercel_entry.py -> app
                                                         |-- path starts with /api/ --> mock_api.app:app
                                                         '-- any other path         --> 404 (/docs, /openapi.json stay private)
```

`infra/vercel_entry.py` calls `build_app(web_dist="")`. In `serve.py` only `None` reads `FLIGHTMIND_WEB_DIST`, so an explicit empty string means "API only" even if the variable is set. The CDN, not the function, serves the web UI.

**Build.** Vercel loads `app` from the module named by `tool.vercel.entrypoint` in the root `pyproject.toml` (`infra.vercel_entry:app`), installs `[project] dependencies` (`fastapi>=0.110`), then runs `[tool.vercel.scripts] build`, which is `python infra/vercel_build.py`. That script runs `npm ci` and `npm run build` in `web/` with `VITE_API_BASE=/.` (the same workaround as in the Dockerfile) and replaces the root `public/` folder with a copy of `web/dist`. It fails with a non-zero exit when `web/dist/index.html` is missing. `public/` is build output and is in `.gitignore`.

**New files.**

| Path | Purpose |
| --- | --- |
| `pyproject.toml` (repo root) | Exists only so Vercel can build the public URL. Entrypoint, `fastapi` dependency, build script. Not a package. |
| `vercel.json` (repo root) | `functions["infra/vercel_entry.py"].excludeFiles`: one brace glob that keeps the web sources, docs, fixtures, pipeline, tests, MCP server and caches out of the function bundle. |
| `.vercelignore` (repo root) | Keeps `.git`, `.claude`, `.kiro`, `data`, `docs`, `fixtures`, virtual environments, caches, `.env*`, `web/dist` and `services/pipeline` out of the upload. `web/`, `contracts/`, `infra/` and `services/intel/` stay, because the build needs them. |
| `infra/vercel_entry.py` | Puts `services/intel` on `sys.path`, exposes `app = build_app(web_dist="")`. |
| `infra/vercel_build.py` | Standard-library build step: web build, then copy `web/dist` to `public/`. |
| `services/intel/tests/test_vercel_entry.py` | Tests for the entry module and for `pyproject.toml` (entrypoint file exists; the `fastapi` floor equals the one in `requirements-serve.txt`). |

**Deploy.** `npx vercel@latest deploy --temporary` from a clean checkout builds and deploys without an account, and prints a claim link that must not be shared. After the claim: `vercel login`, then `vercel deploy --prod`. Hobby limits that matter here: function duration up to 300 s, Python bundle up to 500 MB.

**What no longer applies in the older sections below.** The "Railway setup" section (project, generated domain, healthcheck path, restart policy, plan), the `railway up` / `railway login` / `railway link` commands, the Railway healthcheck on `/api/meta`, `PORT` set by Railway, and the "Railway plan sleeps" risk. In the Overview, the single container and the Railway box are replaced by the flow above. The Dockerfile, `.dockerignore`, `serve.py` behaviour, `requirements-serve.txt`, `smoke.py`, the tests table and the `/.` workaround are unchanged. Phase 2 on Railway (second service, volume, private network) is replaced by the Vercel version in `requirements.md` requirement 9 and `tasks.md` tasks 11 to 16.

## Overview

Phase 1 puts the built web UI and the mock API behind one process and one origin.

```
Judge's browser
      |  https://<name>.up.railway.app
      v
Railway (healthcheck /api/meta, sets PORT)
      |
      v
uvicorn serve:app  (one container, non-root)
      |-- path starts with /api/  --> mock_api.app:app   (FLIGHTMIND_API_APP)
      '-- any other path          --> static files from FLIGHTMIND_WEB_DIST
```

Phase 2 changes two things and no code: `FLIGHTMIND_API_APP` points at the real API, and the real API reads a second Railway service running Postgres.

```
web service (serve.py + real API) --private network--> db service (timescaledb-ha:pg16 + volume)
```

## Files

| Path | Purpose |
| --- | --- |
| `services/intel/serve.py` | ASGI dispatcher `app`. Routes `/api/` to the API app and everything else to the static web build. |
| `services/intel/requirements-serve.txt` | Runtime dependencies only: `fastapi`, `uvicorn`. Version floors are copied from what `requirements.txt` already pins. |
| `services/intel/tests/test_serve.py` | The tests in requirement 7. |
| `Dockerfile` (repo root) | Two-stage build described below. |
| `.dockerignore` (repo root) | Keeps the build context small and free of secrets. |
| `infra/smoke.py` | Smoke check, standard library only. |
| `infra/README.md` | New section "Deploy (SCRUM-38)". |
| `services/intel/README.md` | Short note on `serve.py`, the two variables and the deploy section. |

Not edited: `web/`, `contracts/`, `services/pipeline/`, `services/intel/mock_api/`, `services/intel/requirements.txt`, `infra/docker-compose.yml`. No `railway.json` or `railway.toml`.

## Components

### `serve.py`

```python
DEFAULT_API_APP = "mock_api.app:app"

def load_api_app(spec: str) -> ASGIApp:
    """Import 'module:attribute'. Raise RuntimeError naming the value on any failure."""

def build_app(api_app: str | None = None, web_dist: str | None = None) -> ASGIApp:
    """api_app / web_dist default to FLIGHTMIND_API_APP / FLIGHTMIND_WEB_DIST."""

app = build_app()
```

`build_app` exists so tests can build an app with chosen values without reloading the module. `app = build_app()` at the bottom is what uvicorn loads.

Behaviour:

1. **API app.** Read `FLIGHTMIND_API_APP`; empty or unset means `mock_api.app:app`. Import the module with `importlib.import_module` and take the attribute. A missing module, a missing attribute or an import error raises `RuntimeError("Cannot load FLIGHTMIND_API_APP='...': <reason>")`, so uvicorn exits with that message at start.
2. **Static app.** Read `FLIGHTMIND_WEB_DIST`. If it is set, is a folder and holds `index.html`, create `starlette.staticfiles.StaticFiles(directory=..., html=True)`. Otherwise the static app is `None`. Starlette comes with FastAPI, so there is no new dependency.
3. **Dispatcher.** A plain ASGI callable `async def app(scope, receive, send)`:
   - `scope["type"] == "lifespan"`: pass to the API app, so its startup and shutdown run. (Starlette-based apps accept lifespan; if the API app does not, the dispatcher answers the lifespan messages itself with startup and shutdown complete.)
   - `scope["type"]` is `http` or `websocket` and `scope["path"]` starts with `/api/`: pass to the API app unchanged. The API app sees the original path, so its routes match with no `root_path` games.
   - Any other `http` request: pass to the static app, or, when it is `None`, answer 404 with the plain text `Not Found`.
   - Any other `websocket` request outside `/api/`: close it.
4. **No mutation.** The API app object is only called. `serve.py` does not call `mount`, `add_route`, `add_middleware` or set attributes on it.

What follows from this routing:

- `/docs`, `/redoc` and `/openapi.json` do not start with `/api/`, so they reach the static side and give 404. This is intended (requirement 2.7).
- `/api` without a trailing slash goes to the static side and gives 404. The client always calls `/api/<something>`, so this is fine.
- `StaticFiles` answers only `GET` and `HEAD`. A `POST` to a non-API path gives 405. `POST /api/ask` goes to the API.
- Unknown `/api/...` paths reach the API app, so the 404 is the API's JSON body.
- There is no SPA fallback. See Open question below.

### `requirements-serve.txt`

```
fastapi>=<floor from requirements.txt>
uvicorn>=<floor from requirements.txt>
```

The implementation copies the floors from `requirements.txt` and does not invent new ones. `requirements.txt` stays as it is for development and tests. `mock_api` needs `pydantic`, which `fastapi` brings in. Task 8 confirms the image starts with nothing else installed.

### `Dockerfile`

```dockerfile
# Stage 1: build the web UI
FROM node:22-slim AS web
WORKDIR /src
COPY contracts/ contracts/
COPY web/package.json web/package-lock.json web/
WORKDIR /src/web
RUN npm ci
COPY web/ ./
# Workaround: the client has no same-origin mode. "/." makes
# "/./api/meta" resolve to "/api/meta" on the serving host.
# Remove when Role 1 adds a same-origin base (see requirements, Open item 2).
ARG VITE_API_BASE=/.
ENV VITE_API_BASE=${VITE_API_BASE}
RUN npm run build

# Stage 2: runtime
FROM python:3.12-slim
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY services/intel/requirements-serve.txt .
RUN pip install --no-cache-dir -r requirements-serve.txt
COPY services/intel/mock_api/ mock_api/
COPY services/intel/serve.py .
COPY --from=web /src/web/dist /app/web-dist
ENV FLIGHTMIND_WEB_DIST=/app/web-dist
USER app
CMD ["sh", "-c", "exec uvicorn serve:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

This is a sketch of the intent, not code to paste. The implementation task writes the file and checks it against the points below.

- `contracts/` is copied before `npm ci` because the web build reads `contracts/types.ts` from `../contracts` relative to `web/`. If the build imports other files from outside `web/`, task 4 finds that on the first build and adds them to the copy.
- The `package.json` and lock file are copied before the sources, so the `npm ci` layer is cached until dependencies change. The same idea applies to `requirements-serve.txt` in stage 2.
- `npm run build` runs `tsc --noEmit && vite build` (from `web/package.json`), so a type error in the web code fails the image build. That is acceptable: it is the same check Role 1 runs.
- `CMD` uses `sh -c` with `exec` so `${PORT:-8000}` expands and uvicorn receives the stop signal.
- The user has a fixed uid and no shell login need. Files under `/app` are readable by it; nothing is written at run time.
- Railway detects the root `Dockerfile` and builds it. Railway passes variables as build arguments only when a matching `ARG` exists. The Dockerfile declares only `VITE_API_BASE`, with a default, so a stray Railway variable cannot change the build by accident.

### `.dockerignore`

Entries: `.git`, `.claude`, `data`, `node_modules`, `web/node_modules`, `web/dist`, `.venv`, `services/intel/.venv`, `__pycache__`, `*.pyc`, `.env*`, `fixtures`, `docs`. The context stays small and cannot carry a key or a recording into the image. If `railway up` uploads from the same ignore rules, the same file keeps the upload small; the implementation confirms that in task 9.

### `infra/smoke.py`

Standard library only (`urllib.request`, `json`, `sys`, `urllib.parse`).

```
python infra/smoke.py https://<name>.up.railway.app
```

Steps, each printing `ok <url>` on success:

1. `GET /` returns status 200 and a `Content-Type` that contains `text/html`.
2. `GET /api/meta` returns JSON with `mode == "replay"`.
3. `GET /api/events` returns a non-empty list. The first item gives `id` and `icao24`.
4. `GET /api/events/{id}` opens (200, JSON). Its first `raw_refs` item is the `raw_ref` used next.
5. `GET /api/raw/{raw_ref}` with `raw_ref` URL-encoded (`quote(..., safe='')`) returns 200 JSON.
6. `GET /api/tracks/{icao24}` for the first event's aircraft returns JSON with a non-empty `points` list.

On the first failure it prints `FAIL <url>: <reason>` and exits with 1. A bad argument count prints usage and exits with 2. Each request has `timeout=10`. The base URL is stripped of a trailing `/`. Redirects are not followed to a different host (the opener refuses a redirect whose host differs). The script sends no headers beyond the default `User-Agent`.

### Environment variables

| Variable | Where it is set | Phase | Meaning |
| --- | --- | --- | --- |
| `PORT` | Railway sets it (phase 1 container hosts only) | 1 | Port to listen on. Default 8000 outside Railway. |
| `FLIGHTMIND_API_APP` | Dockerfile default unset; Vercel environment variable in phase 2 | 1, 2 | `module:attribute` of the API app. Default `mock_api.app:app`. |
| `FLIGHTMIND_WEB_DIST` | Dockerfile `ENV` | 1 | Folder with the built web UI. Unset or no `index.html` means API only. |
| `VITE_API_BASE` | Dockerfile build argument, `/.` | 1 | Build-time only. See below. |
| `DATABASE_URL` | Vercel environment variable only | 2 | Postgres connection for the real API. Never in the repo. |
| `ANTHROPIC_API_KEY` | Vercel environment variable only | 2 | Claude API key (agent). Never in the repo. |
| `GEMINI_API_KEY` | Vercel environment variable only | 2 | Embeddings key. Never in the repo. |

## The same-origin workaround

`web/src/api/client.ts` builds each URL as `${baseUrl}${path}` and uses the in-browser fixture when `VITE_API_BASE` is empty. There is no way to say "same origin" without editing `web/`, which Role 3 does not do.

With `VITE_API_BASE=/.` the browser requests `/./api/meta`. The URL parser removes the `.` segment before sending, so the server sees `/api/meta`, on whatever host serves the page. The same holds for `/./api/events/<id>`, and for `/./api/raw/<raw_ref>` (the client URL-encodes the `:` in `raw_ref`; the server decodes it as before).

Consequences:

- It depends on standard browser URL normalisation. Task 8 checks it in a real browser against the local image (network tab shows `/api/...` calls, no fixture), and task 9 checks it again on the public URL.
- The page cannot tell it is on the mock, so the "Sample data" label does not show. That is Open item 1, a Role 1 decision.
- When Role 1 adds a same-origin base, change the build argument and delete the comment in the Dockerfile.

## Railway setup (what lives outside the repo) — superseded on 2026-11-26 by Vercel, see the update at the top

Written in `infra/README.md`, because these settings are not in a config file (no `railway.json`):

- Project and service name; the service builds from the root `Dockerfile` (auto-detected).
- Public domain: generated in the service's Settings, Networking. Recorded in `infra/README.md`.
- Healthcheck path: `/api/meta`, set in Settings, Deploy. A deploy is switched live only when this answers 200.
- Restart policy: on failure.
- Variables: none in phase 1.
- Plan: see requirements Open item 3.

Deploy commands, in the order the README lists them: `railway login`; `railway init` or `railway link`; `railway up` from a clean checkout of `main`; `railway domain`; set the healthcheck in the service settings; `python infra/smoke.py <url>`; redeploy with `railway up`; roll back from the service's Deployments list (or `railway redeploy` of a previous deployment, whichever the CLI version supports; the README states the one that was tried). The exact flags are confirmed against the installed CLI during task 9 and written as run.

A clean checkout matters because `railway up` uploads the working directory. Uncommitted files would ship. `.dockerignore` limits what is sent, and the README says to deploy from a fresh `git clone` of `main` or a worktree with no local changes.

## Phase 2 design (not built now) — superseded on 2026-11-26 by Vercel, see requirement 9

All of this is blocked on SCRUM-37 (real API) and pipeline PR #11.

1. **Database service.** A second Railway service from the image `timescale/timescaledb-ha:pg16` with a volume mounted at the Postgres data path. It has no public domain. The web service connects over the private network address. The `POSTGRES_*` variables are set in Railway, not in the repo.
2. **Schema and data.** `contracts/schema.sql` is applied once to the empty database, then the recorded CAT021 data is loaded by the pipeline's loader (PR #11). The method (one-off `psql` from a laptop through a temporary TCP proxy, or a one-off job) is chosen when the loader exists. The temporary proxy is closed afterwards.
3. **Real API on the web service.** Set `FLIGHTMIND_API_APP` to the real API's `module:attribute`. If the real API needs more runtime packages, they are added to `requirements-serve.txt`. If it is not under `services/intel/mock_api/`, the Dockerfile copy line for the API package is extended. These are the only edits, and they are in files this spec names.
4. **Secrets.** `DATABASE_URL`, `ANTHROPIC_API_KEY` and `GEMINI_API_KEY` are Vercel environment variables on the project. Not in the repo, the image, logs or README. The real API must not log them.
5. **CORS.** The real API restricts origins to the public origin. Because the UI and API share an origin, it may allow none at all. This is a change in the real API (SCRUM-37), checked here.
6. **Raw file.** `/api/raw/{raw_ref}` reads bytes from the recording file on demand (`tech.md`). The file must be reachable by the web service: either on a volume mounted on the web service, or fetched into the image at build time from a private location. The choice depends on file size and the plan's volume limit (Open item 5).
7. **Fallback.** If phase 2 does not work by 2026-12-02, leave the service on phase 1 and say in the README and Devpost text that the public demo uses sample data.

## Testing strategy

File: `services/intel/tests/test_serve.py`. Uses `fastapi.testclient.TestClient` on `build_app(...)` with values passed in, and `tmp_path` for the dist folder, so nothing depends on the real web build. Reuse the schema helpers from `test_mock_api.py` by copying the few lines needed, because editing that file is outside this ticket.

| Requirement | Test |
| --- | --- |
| 7.2, 2.5 | Temp dist with `index.html` and `assets/app.js`. `GET /` returns the `index.html` text; `GET /assets/app.js` returns the file. |
| 7.3, 2.6 | `GET /api/meta` through `build_app` validates against the `Meta` schema in `contracts/openapi.yaml`. |
| 7.4, 2.6 | `GET /api/nope` returns 404 with a JSON body that has `detail`. |
| 7.5 | `GET /nope.txt` returns 404. |
| 7.6, 2.5 | With no dist: `GET /api/meta` is 200, `GET /` is 404. Also with a dist folder that has no `index.html`. |
| 7.7, 2.3, 2.4 | `FLIGHTMIND_API_APP` set to a small test app (defined in the test module) routes `/api/ping` to it. An invalid value (`no_such_module:app`, and a module with a missing attribute) raises `RuntimeError` whose message contains the value. |
| 7.8, 2.7 | `GET /docs` and `GET /openapi.json` are 404. |
| 2.2 | A request for `/api/events` is answered by the API, and `/apiary` (path that starts with `/api` but not `/api/`) is not. |
| 2.2 | `serve.build_app` does not change the API app: the route list and middleware list of the imported mock app are equal before and after. |
| 2.8 | A test app with a lifespan handler that sets a flag: using `TestClient` as a context manager sets the flag. |
| 2.1 | With the env vars unset, `build_app()` uses `mock_api.app:app`. Use `monkeypatch` for the environment. |

Smoke script checks (not part of pytest): task 8 runs `infra/smoke.py` against the local image; task 9 runs it against the public URL. A short self-test of `smoke.py` is optional: run it against `uvicorn serve:app` locally before building the image, so the script is known good before it judges the container.

Manual checks, once, in task 8: open the local image in a browser, confirm the event list loads, an event opens, the track draws, a `raw_ref` opens, and the network tab shows `/api/...` requests (no fixture). Also `docker run` as the non-root user: `docker run --rm <image> id -u` prints a non-zero id.

## Dependencies and disclosure

- `fastapi` and `uvicorn` (already used by the mock API) now run in production. `starlette` (via FastAPI) serves the static files.
- Railway (hosting) is a third-party service that does real work. Disclose it in the README third-party list. The root `README.md` is owned by Role 1, so the implementation opens an issue for that line and documents it in `services/intel/README.md` meanwhile.
- Docker base images `node:22-slim` and `python:3.12-slim` are named in the Dockerfile. Phase 2 adds `timescale/timescaledb-ha:pg16`, already used in `infra/docker-compose.yml`.

## Risks

1. **`/.` base breaks in some browser or fetch path.** Checked in tasks 8 and 9. Fallback: ask Role 1 for the same-origin option before the 2026-12-03 target.
2. **Web build needs files outside `web/` and `contracts/`.** Found on the first image build (task 4) and fixed in the copy lines.
3. **Railway plan sleeps or stops the service.** Open item 3. Check the plan before 2026-12-03.
4. **Public page shows synthetic data without saying so.** Open item 1. Stated in the README and Devpost text until Role 1 decides.
5. **Uncommitted files shipped by `railway up`.** Deploy from a clean checkout of `main`; `.dockerignore` limits the upload.

## Open questions

1. **SPA fallback.** If the UI uses client-side routes, a reload on such a route gives 404. The product description says the 4D trajectory view is the first screen at `/`, and the web client has no router dependency in `web/package.json`, so the design has no fallback. Task 8 checks this by reloading on every view the UI can reach. If any view has its own path, add a fallback to `serve.py` (serve `index.html` for non-API `GET` paths with no file extension) and update requirement 2.
2. **CLI flags.** The exact `railway` CLI commands for creating the project, generating the domain and rolling back are confirmed against the installed CLI version in task 9 and written down as run.
