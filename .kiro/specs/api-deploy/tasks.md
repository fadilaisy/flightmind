# Tasks: SCRUM-38 deploy the public live URL in replay mode

Implements `requirements.md` and `design.md` in this folder. All paths are relative to the repo root. Run Python commands from `services/intel` with the `.venv` there. Do not edit anything under `web/`, `contracts/`, `services/pipeline/` or `services/intel/mock_api/`. Do not add `railway.json` or `railway.toml`.

Tasks 1 to 9 are phase 1 and are built now. Tasks 10 to 16 are phase 2: they are open and are not built now.

## Phase 1

- [x] 1. Write the dispatcher in `services/intel/serve.py`
  - Implement `DEFAULT_API_APP`, `load_api_app(spec)`, `build_app(api_app=None, web_dist=None)` and `app = build_app()` as in design.md.
  - Route `/api/` to the API app, everything else to `StaticFiles(html=True)` when the dist folder has `index.html`, otherwise 404. Pass lifespan events to the API app. Do not mutate the API app. Use type hints and Python 3.10-compatible syntax (the local Python is 3.10; the image is 3.12).
  - A bad `FLIGHTMIND_API_APP` raises `RuntimeError` with the value in the message.
  - Done when `uvicorn serve:app --port 8000` from `services/intel` answers `/api/meta` with `mode` = `replay`, and, with `FLIGHTMIND_WEB_DIST` pointing at a folder holding an `index.html`, answers `/` with that file.
  - **Result (2026-11-26):** `uvicorn serve:app --port 8000` from `services/intel` (Python 3.10.11) answered `/api/meta` with `mode` = `replay` and `/` with the `index.html` from a temp `FLIGHTMIND_WEB_DIST`; `/docs` gave 404. Starlette `StaticFiles` raises `HTTPException` when called as a bare ASGI app, so the dispatcher catches it and answers with a plain-text response.
  - _Requirements: 1.1, 1.2, 1.4, 1.6, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9_

- [x] 2. Write the tests in `services/intel/tests/test_serve.py`
  - Cover every row of the testing table in design.md, using `TestClient`, `tmp_path` and `monkeypatch`. Copy the few schema-check lines needed from `test_mock_api.py`; do not edit that file.
  - Run `python -m pytest -q` from `services/intel`. The new file and all existing tests must pass.
  - Done when the run is green and `git status` shows no change under `contracts/` or `services/intel/mock_api/`.
  - **Result (2026-11-26):** `python -m pytest -q` from `services/intel`: 54 passed (the existing mock API and MCP tests plus the new `test_serve.py`), no change under `contracts/` or `mock_api/`. The lifespan test uses a `lifespan=` context manager, not `on_event`, to avoid a deprecation warning.
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 2.2, 2.8_

- [x] 3. Add `services/intel/requirements-serve.txt`
  - List `fastapi` and `uvicorn` only, with the same version floors as `services/intel/requirements.txt`. Leave `requirements.txt` unchanged.
  - Done when a fresh virtual environment with only `requirements-serve.txt` installed can run `uvicorn serve:app` and answer `/api/meta` (this proves `mock_api` needs nothing else).
  - **Result (2026-11-26):** Fresh venv in the system temp folder (Python 3.10.11) with only `requirements-serve.txt` (`fastapi>=0.110`, `uvicorn>=0.29`, same floors as `requirements.txt`; resolved to fastapi 0.162.5, uvicorn 0.54.0, starlette 1.7.0, pydantic 2.14.4) ran `uvicorn serve:app` and `/api/meta` returned 200 with `mode` = `replay`. Venv deleted afterwards.
  - _Requirements: 3.3_

- [x] 4. Write the root `Dockerfile` and `.dockerignore`
  - Files: `Dockerfile`, `.dockerignore`.
  - Two stages as in design.md: `node:22-slim` runs `npm ci` and `npm run build` in `web/` with `contracts/` copied and build argument `VITE_API_BASE=/.`; `python:3.12-slim` installs `requirements-serve.txt`, copies `mock_api`, `serve.py` and the built `dist`, sets `FLIGHTMIND_WEB_DIST`, runs as a non-root user and starts `uvicorn serve:app --host 0.0.0.0 --port ${PORT:-8000}`. Dependency files are copied before sources.
  - Put a comment above `VITE_API_BASE` saying it is a workaround and pointing to Open item 2 in `requirements.md`.
  - If the web build needs more files from outside `web/` and `contracts/`, add them to the copy and note it in design.md.
  - Done when `docker build -t flightmind-web .` from the repo root succeeds, and `docker run --rm flightmind-web id -u` prints a non-zero number.
  - **Result (2026-11-26):** `docker build -t flightmind-web .` succeeded on the first try (`tsc --noEmit && vite build` passed, so the web build needs nothing outside `web/` and `contracts/`); `docker run --rm flightmind-web id -u` printed `10001`. Image size 216 MB.
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 4.1, 4.2_

- [x] 5. Write the smoke check `infra/smoke.py`
  - Standard library only. One argument: the base URL. Run the six checks in the order of requirement 5.2, print `ok <url>` for each pass, print `FAIL <url>: <reason>` and exit 1 on the first failure, exit 2 on bad usage, exit 0 when all pass. 10 second timeout per request. Strip a trailing `/`. Do not follow a redirect to another host.
  - Done when it exits 0 against a local `uvicorn serve:app` with a dist folder, and exits non-zero and names the URL when pointed at a port with nothing listening and when run against the API alone (no dist), where the `/` check must fail.
  - **Result (2026-11-26):** Against a local `uvicorn serve:app` with a dist folder: six `ok` lines, exit 0. Against the API alone: `FAIL http://localhost:8003/: status 404 Not Found`, exit 1. Nothing listening: `FAIL http://localhost:8004/: cannot connect: ...`, exit 1. No argument: usage, exit 2.
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

- [x] 6. Write the docs in `infra/README.md` and `services/intel/README.md`
  - `infra/README.md`: add the section "Deploy (SCRUM-38)" with the steps in order: login, create or link the project, deploy with `railway up` from a clean checkout of `main`, generate the domain, set the healthcheck `/api/meta`, smoke-check, redeploy, roll back. List every setting that lives in Railway and not in the repo. State that there is no `railway.json` because Config as Code stops being read on 2026-12-01. State the `VITE_API_BASE=/.` workaround and that the public page uses sample data. Leave the public URL line as "to be filled in task 9".
  - `services/intel/README.md`: add a short note: what `serve.py` does, `FLIGHTMIND_API_APP` and `FLIGHTMIND_WEB_DIST`, how to run it locally, and a pointer to the deploy section. Add Railway to the third-party list for the README disclosure.
  - Done when a teammate who has never seen the repo can follow the section from login to a passing smoke check, with no step that needs a secret.
  - **Result (2026-11-26):** `infra/README.md` has the section "Deploy (SCRUM-38)" (steps, Railway-only settings table, local run, the `/.` workaround); `services/intel/README.md` has the `serve.py` note and the Railway disclosure line. The `railway` flags are written as not yet run; task 9 confirms them. Public URL left as "to be filled in task 9".
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.6, 6.7_

- [x] 7. Check the container locally
  - Run the image: `docker run --rm -p 8080:8080 -e PORT=8080 flightmind-web`. Run `python infra/smoke.py http://localhost:8080` and keep the output.
  - Check by hand: `/docs` and `/openapi.json` give 404; an unknown `/api/x` gives the API's JSON 404; an unknown non-API path gives 404; `docker run` with no `PORT` listens on 8000.
  - Done when the smoke check exits 0 and each hand check gives the stated result.
  - **Result (2026-11-26):** `docker run -d --name flightmind-web-check -p 8080:8080 -e PORT=8080 flightmind-web`: `infra/smoke.py http://localhost:8080` passed all six checks, exit 0. `/docs`, `/openapi.json`, `/redoc` gave 404; `/api/x` gave `{"detail":"Not Found"}` 404; `/nope` and `/apiary` gave 404; the container user id is 10001; with no `PORT` it logged `Uvicorn running on http://0.0.0.0:8000` and `/api/meta` answered 200. Container removed afterwards.
  - _Requirements: 1.4, 1.6, 2.6, 2.7, 3.6, 5.5_

- [ ] 8. Check the UI in a browser against the local image
  - Open `http://localhost:8080` in a browser. Confirm the event list loads, an event opens, its track draws, a `raw_ref` opens, and the network tab shows requests to `/api/...` with no in-browser fixture in use. Reload on every view the UI can reach and confirm none returns 404 (open question 1 in design.md).
  - If the `/.` base fails in the browser, stop and tell the user before changing anything, because the fix is in `web/` (Role 1). If a view needs a path fallback, add it to `serve.py` with a test and update requirement 2.
  - Record in `infra/README.md` that the workaround was checked, with the browser name and date.
  - Done when the browser check passes and the note is written.
  - _Requirements: 1.5, 4.1, 4.3_

- [ ] 9. Deploy to Railway and run the smoke check on the public URL
  - Confirm the plan first (Open item 3 in `requirements.md`): the service must not sleep or stop on a credit limit. This is Zahran's account decision. Do not deploy until it is answered.
  - From a clean checkout of `main`, follow the README section: `railway login`, create or link the project, `railway up`, generate the domain, set the healthcheck `/api/meta` and restart on failure. Fix any README step that did not work as written.
  - Run `python infra/smoke.py https://<name>.up.railway.app`, then open the URL in a browser from a device with no Railway login and repeat the check from task 8.
  - Try the rollback once and write down the command that worked.
  - Record the public URL, the date and the smoke-check result in `infra/README.md`. Tell the user the URL so it can go in the Devpost "Try it out" field. Nothing goes in the private test-credentials field.
  - Done when the smoke check exits 0 against the public URL and the URL, date and rollback command are in `infra/README.md`.
  - _Requirements: 1.1, 1.3, 1.5, 6.1, 6.2, 6.3, 6.5, 8.1, 8.2, 8.4_

- [ ] 10. Hand-offs and log (phase 1)
  - Open an issue for Role 1 for Open item 1 (label for the deployed mock data) and Open item 2 (same-origin base in the client), and one for the root `README.md` third-party line for Railway.
  - Add the SCRUM-38 phase 1 line to `KIRO.md` in the existing row format, with the date and Role 3.
  - Commit with the `Kiro:` trailer from `.gitmessage`. Stage files by name, not `git add .`.
  - Done when the issues exist and the commit is made.
  - _Requirements: 6.6_

## Phase 2 (open, not built now)

- [ ] 11. Add the database service on Railway (blocked on SCRUM-37)
  - Create a second service from `timescale/timescaledb-ha:pg16` with a volume at the Postgres data path and no public domain. Set the `POSTGRES_*` variables in Railway only.
  - Done when the web service can reach it over the private network and `pg_isready` passes.
  - _Requirements: 9.1, 9.2, 9.4_

- [ ] 12. Load the schema and recorded data (blocked on SCRUM-37 and pipeline PR #11)
  - Apply `contracts/schema.sql` to the empty database, then load the recorded CAT021 data with the pipeline loader. Close any temporary TCP proxy afterwards.
  - Done when the row counts match the loader's report and `extensions` for TimescaleDB and pgvector exist.
  - _Requirements: 9.1_

- [ ] 13. Make the raw recording file available to the web service (blocked on SCRUM-37)
  - Choose and apply one method (volume on the web service, or a private fetch at build time) from design.md, after checking the file size against the plan's volume limit.
  - Done when `/api/raw/{raw_ref}` on the deployed service returns the bytes for a `raw_ref` taken from a real event.
  - _Requirements: 9.6_

- [ ] 14. Switch the web service to the real API (blocked on SCRUM-37)
  - Set `FLIGHTMIND_API_APP` to the real API's `module:attribute` in Railway. Add any runtime packages to `services/intel/requirements-serve.txt` and extend the Dockerfile copy lines if the API package is not `mock_api`. Set `DATABASE_URL`, `COARENA_API_KEY` and `GEMINI_API_KEY` as Railway variables only. Confirm they are not in the repo, the image layers or the logs.
  - Done when `python infra/smoke.py <public url>` exits 0 with real data and `git grep` finds no key value in the repo.
  - _Requirements: 9.3, 9.4_

- [ ] 15. Restrict CORS on the real API (blocked on SCRUM-37)
  - Check that the real API allows only the public origin (or none, since the UI shares the origin). If it does not, raise it with SCRUM-37 and do not change `mock_api`.
  - Done when a request with `Origin: https://example.com` gets no `access-control-allow-origin` header.
  - _Requirements: 9.5_

- [ ] 16. Verify the demo on the public URL and decide the fallback (blocked on SCRUM-37)
  - Ask the three demo questions of SCRUM-36 on the public URL and time them: each must answer with citations in under 30 seconds. Run the smoke check on 2026-12-03 and again before 2026-12-04 14:00 PT, and note each run with its date in `infra/README.md`.
  - If phase 2 is not working by 2026-12-02, set `FLIGHTMIND_API_APP` back to `mock_api.app:app`, and make sure the README and Devpost text say the public demo uses sample data.
  - Done when the three answers and both smoke runs are recorded, or the fallback is applied and recorded.
  - _Requirements: 8.3, 9.7, 9.8_
