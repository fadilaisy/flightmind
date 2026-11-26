# Tasks: SCRUM-38 deploy the public live URL in replay mode

Implements `requirements.md` and `design.md` in this folder. All paths are relative to the repo root. Run Python commands from `services/intel` with the `.venv` there. Do not edit anything under `web/`, `contracts/`, `services/pipeline/` or `services/intel/mock_api/`. Do not add `railway.json` or `railway.toml`.

Tasks 1 to 10 are phase 1 and are built now (task 9, the Railway deploy, is superseded by tasks 17 to 20). Tasks 11 to 16 are phase 2: they are open and are not built now. Tasks 17 to 20 are phase 1 on Vercel.

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

- [x] 8. Check the UI in a browser against the local image
  - Open `http://localhost:8080` in a browser. Confirm the event list loads, an event opens, its track draws, a `raw_ref` opens, and the network tab shows requests to `/api/...` with no in-browser fixture in use. Reload on every view the UI can reach and confirm none returns 404 (open question 1 in design.md).
  - If the `/.` base fails in the browser, stop and tell the user before changing anything, because the fix is in `web/` (Role 1). If a view needs a path fallback, add it to `serve.py` with a test and update requirement 2.
  - Record in `infra/README.md` that the workaround was checked, with the browser name and date.
  - Done when the browser check passes and the note is written.
  - **Result (2026-11-26):** Checked by hand outside Kiro in a Chromium 156 browser against the local image on port 8080. The event list loaded with the mock's 4 events, the first event opened, record `rec01:68` opened, and the network log showed `/api/meta`, `/api/events`, `/api/events/<id>` and `/api/raw/rec01%3A68` on the same origin, all 200, with no console error. Reloading on `/?tab=records` and `/?tab=events` returned 200: the tabs are query parameters, so no path fallback is needed. Not checked: the track drawing, because the map and charts are still empty boxes in the UI.
  - _Requirements: 1.5, 4.1, 4.3_

- [ ] 9. Deploy to Railway and run the smoke check on the public URL
  - **Superseded on 2026-11-26 by tasks 17 to 20 (host changed to Vercel).** Left unticked on purpose; the text below is the original Railway task.
  - Confirm the plan first (Open item 3 in `requirements.md`): the service must not sleep or stop on a credit limit. This is Zahran's account decision. Do not deploy until it is answered.
  - From a clean checkout of `main`, follow the README section: `railway login`, create or link the project, `railway up`, generate the domain, set the healthcheck `/api/meta` and restart on failure. Fix any README step that did not work as written.
  - Run `python infra/smoke.py https://<name>.up.railway.app`, then open the URL in a browser from a device with no Railway login and repeat the check from task 8.
  - Try the rollback once and write down the command that worked.
  - Record the public URL, the date and the smoke-check result in `infra/README.md`. Tell the user the URL so it can go in the Devpost "Try it out" field. Nothing goes in the private test-credentials field.
  - Done when the smoke check exits 0 against the public URL and the URL, date and rollback command are in `infra/README.md`.
  - **Result (2026-11-26):** Not done. Creating the Railway project was refused: "Your trial has expired. Please select a plan to continue using Railway." Zahran has to pick a plan on the Railway account first (Open item 3). The branch is pushed and the image is checked locally, so the deploy can run as soon as the plan is set.
  - _Requirements: 1.1, 1.3, 1.5, 6.1, 6.2, 6.3, 6.5, 8.1, 8.2, 8.4_

- [ ] 10. Hand-offs and log (phase 1)
  - Open an issue for Role 1 for Open item 1 (label for the deployed mock data) and Open item 2 (same-origin base in the client), and one for the root `README.md` third-party line for Railway.
  - Add the SCRUM-38 phase 1 line to `KIRO.md` in the existing row format, with the date and Role 3.
  - Commit with the `Kiro:` trailer from `.gitmessage`. Stage files by name, not `git add .`.
  - Done when the issues exist and the commit is made.
  - _Requirements: 6.6_

## Phase 1 on Vercel

- [x] 17. Add the Vercel files
  - Files: `pyproject.toml`, `vercel.json`, `.vercelignore`, `infra/vercel_entry.py`, `infra/vercel_build.py`, `.gitignore` (add `/public/` and `.vercel/`).
  - `pyproject.toml` names `infra.vercel_entry:app` as `tool.vercel.entrypoint`, depends on `fastapi>=0.110` only, and runs `python infra/vercel_build.py` as the build script. `infra/vercel_entry.py` builds the app with `web_dist=""` (API only). `infra/vercel_build.py` builds `web/` with `VITE_API_BASE=/.` and copies `web/dist` to `public/`. `vercel.json` excludes everything the API does not need from the function bundle.
  - Do not edit `web/`, `contracts/`, `services/pipeline/` or `services/intel/mock_api/`. Do not run any `vercel` or `railway` command in this task.
  - Done when `python infra/vercel_build.py` from the repo root exits 0, `public/index.html` exists and `git status` does not list `public/`.
  - **Result (2026-11-26):** `python infra/vercel_build.py` exited 0 (13 files copied: `public/index.html` and `public/assets/`), and `git status` did not list `public/`. `serve.build_app` already treated `""` as "API only" (only `None` reads `FLIGHTMIND_WEB_DIST`), so `serve.py` needed no change.
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 18. Test the Vercel entry point
  - File: `services/intel/tests/test_vercel_entry.py`, plus one test in `test_serve.py` that an explicit empty `web_dist` ignores `FLIGHTMIND_WEB_DIST`.
  - With `TestClient` on `infra/vercel_entry.py` loaded by path: `/api/meta` is 200 with `mode` = `replay`; `/`, `/docs` and `/openapi.json` are 404, also when `FLIGHTMIND_WEB_DIST` points at a folder with an `index.html`. The entrypoint in `pyproject.toml` names a module file that exists, and its `fastapi` floor equals the one in `requirements-serve.txt`.
  - Done when `python -m pytest -q` from `services/intel` passes.
  - **Result (2026-11-26):** `python -m pytest -q` from `services/intel`: 61 passed (54 before, plus 1 in `test_serve.py` and 6 in `test_vercel_entry.py`).
  - _Requirements: 1.2, 1.6, 2.5, 2.7, 3.1, 3.2_

- [x] 19. Deploy with `vercel deploy --temporary` and check the public URL
  - From a clean checkout of the repo root, run `npx vercel@latest deploy --temporary`. It needs no account. Keep the claim link private: do not paste it in chat, an issue or the repo.
  - Run `python infra/smoke.py <public url>`. Open the URL in a browser with no Vercel session and repeat the check from task 8 (event list, event, `raw_ref`, `/api/...` requests, no fixture, no login page).
  - Zahran opens the claim link so the project moves into his Vercel account. Later deploys use `npx vercel@latest login` and `npx vercel@latest deploy --prod`. Try the rollback once and write down the command that worked.
  - Record the public URL, the date and the smoke-check result in `infra/README.md`.
  - Done when the smoke check exits 0 against the public URL, the claim is done, and the URL, date and rollback command are in `infra/README.md`.
  - **Result (2026-11-26):** Partly done, by hand outside Kiro. `vercel deploy --temporary` succeeded on the third try: the CLI first could not find `@vercel/python` (fixed by installing `vercel` and `@vercel/python` in a folder outside the repo and setting `NODE_PATH`), then the bundle traced `services/intel/.pytest_cache`, which `.vercelignore` excludes (fixed by adding `**/.pytest_cache/**` to `excludeFiles` in `vercel.json`). The temporary URL served the page and the API correctly from an outside network. From Zahran's network Vercel's firewall answered 403 on every path (`x-vercel-mitigated: deny`), so `infra/smoke.py` has not passed against the public URL. Still open: Zahran claims the deployment, the smoke check from a network that is not refused, the browser check, the rollback, and the final URL in `infra/README.md`.
  - **Result (2026-11-26, after the claim):** Zahran approved the access and the deployment was claimed into his Vercel account through the Vercel connector, by hand outside Kiro. The project is `flightmind` with the domain `https://flightmind.vercel.app`. `infra/smoke.py` passed 6 of 6 against it from Zahran's network, the browser check passed, and `/api/meta` also read correctly from an outside network. The 403 stopped once the deployment was claimed. Not done: the rollback, because there is only one deployment; it stays written in `infra/README.md` as not tried.
  - _Requirements: 1.1, 1.3, 1.5, 6.1, 6.3, 6.5, 8.1, 8.3, 8.4, 8.5_

- [x] 20. Update the docs for Vercel
  - `infra/README.md`, section "Deploy (SCRUM-38)": Vercel steps (first deploy, claim, login, later deploys, smoke check, rollback), what lives in Vercel and not in the repo, why there is no Railway, the `/.` workaround and the local image check. `services/intel/README.md`: the `serve.py` note names `infra/vercel_entry.py` and lists Vercel in the third-party line.
  - Done when a teammate can follow the section from a clean checkout to a passing smoke check with no secret in the repo.
  - **Result (2026-11-26):** Both files updated. The Vercel commands and the rollback are written as not yet run; task 19 confirms them. The public URL stays "not deployed yet".
  - _Requirements: 6.2, 6.3, 6.4, 6.6, 6.7_

## Phase 2 (open, not built now)

All of phase 2 is blocked on SCRUM-37 (the real API) and, for the data, on pipeline PR #11. It runs on Vercel.

- [ ] 11. Host the database outside Vercel (blocked on SCRUM-37)
  - Choose a hosted Postgres with both TimescaleDB and pgvector (not checked yet which free one has both). Keep its credentials out of the repo.
  - Done when the function can connect over TLS and the two extensions exist.
  - _Requirements: 9.1, 9.2, 9.4_

- [ ] 12. Load the schema and recorded data (blocked on SCRUM-37 and pipeline PR #11)
  - Apply `contracts/schema.sql` to the empty database, then load the recorded CAT021 data with the pipeline loader.
  - Done when the row counts match the loader's report.
  - _Requirements: 9.1_

- [ ] 13. Make the raw recording file available to the function (blocked on SCRUM-37)
  - Either the file fits in the 500 MB Python bundle (and is not excluded by `vercel.json` or `.vercelignore`), or it lives in external storage that the function reads on demand. Check the file size first.
  - Done when `/api/raw/{raw_ref}` on the deployed URL returns the bytes for a `raw_ref` taken from a real event.
  - _Requirements: 9.6_

- [ ] 14. Switch the function to the real API (blocked on SCRUM-37)
  - Set `FLIGHTMIND_API_APP` to the real API's `module:attribute` as a Vercel environment variable. Add any runtime packages to `pyproject.toml` and `services/intel/requirements-serve.txt`, and check `vercel.json` does not exclude the real API's files. Set `DATABASE_URL`, `COARENA_API_KEY` and `GEMINI_API_KEY` as Vercel environment variables only.
  - Done when `python infra/smoke.py <public url>` exits 0 with real data and `git grep` finds no key value in the repo.
  - _Requirements: 9.1, 9.3, 9.4_

- [ ] 15. Restrict CORS on the real API (blocked on SCRUM-37)
  - Check that the real API allows only the public origin (or none, since the UI shares the origin). If it does not, raise it with SCRUM-37 and do not change `mock_api`.
  - Done when a request with `Origin: https://example.com` gets no `access-control-allow-origin` header.
  - _Requirements: 9.5_

- [ ] 16. Verify the demo on the public URL and decide the fallback (blocked on SCRUM-37)
  - Ask the three demo questions of SCRUM-36 on the public URL and time them: each must answer with citations in under 30 seconds. Run the smoke check on 2026-12-03 and again before 2026-12-04 14:00 PT, and note each run with its date in `infra/README.md`.
  - If phase 2 is not working by 2026-12-02, remove `FLIGHTMIND_API_APP` from the Vercel environment (back to `mock_api.app:app`), and make sure the README and Devpost text say the public demo uses sample data.
  - Done when the three answers and both smoke runs are recorded, or the fallback is applied and recorded.
  - _Requirements: 8.3, 9.7, 9.8_
