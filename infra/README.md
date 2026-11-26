# infra — local stack (SCRUM-31)

One Postgres with **TimescaleDB** and **pgvector**, loaded with the schema and
the fixture seed, for every teammate's laptop.

## Run

From the repo root:

```bash
docker compose -f infra/docker-compose.yml up -d
```

First start loads, in order:

1. `infra/db/init/00_extensions.sql` — TimescaleDB + pgvector
2. `contracts/schema.sql` — tables, hypertable, trigger
3. `fixtures/seed.sql` — fixture rows (owned by Role 2, SCRUM-22)

Connect:

```
host=localhost port=5432 db=flightmind user=flightmind password=flightmind
```

## Reset (after a schema or seed change)

Init scripts run only on an empty data volume. To re-load them:

```bash
docker compose -f infra/docker-compose.yml down -v
docker compose -f infra/docker-compose.yml up -d
```

## Notes

- `docker compose down` (without `-v`) keeps the data volume.
- Dev-only password; the deployed stack (SCRUM-38) uses its own secrets.


## Deploy (SCRUM-38)

Phase 1: one Vercel project (Hobby plan, free) serves the built web UI and the **mock API**
(synthetic data, no database) on one origin. One Vercel Function (`infra/vercel_entry.py`)
serves everything through `serve.py`, as the container does: `/api/` goes to the API, every other
path is a file from the web build, and anything else is 404, so `/docs` and `/openapi.json` stay
private. **The public demo
uses sample data.**

Since 2026-11-26 the public site answers `/api/ask` with the cited agent of SCRUM-36: the Vercel project has `ANTHROPIC_API_KEY` as a sensitive Production variable, set by Zahran in the dashboard. Remove that variable and redeploy to go back to the canned answers.

Public URL: **https://flightmind.vercel.app** (Vercel project `flightmind` in Zahran's account,
Hobby plan). Deployed and claimed on 2026-11-26 from the branch `role3/scrum-38-api-deploy`.

Checks on 2026-11-26 against `https://flightmind.vercel.app`:

- `python infra/smoke.py https://flightmind.vercel.app`: 6 of 6 passed, exit 0.
- `/docs`, `/openapi.json` and an unknown path give 404; an unknown `/api/x` gives the API's JSON
  404; `POST /api/ask` answers.
- Browser (Chromium 156): the event list, the first event and its records loaded from
  `/api/meta`, `/api/events` and `/api/events/<id>` on the same origin, with no console error. So
  the `/.` workaround also works on Vercel.
- Read from a second, outside network: `/api/meta` returned the expected JSON.

How it got there: the first deploy was `vercel deploy --temporary` (no account), which gave
`https://brisk-zenith-i0v5z3t.tmp.now`. While it was unclaimed, Vercel's firewall answered
`403 This request was blocked` (`x-vercel-mitigated: deny`) on every path from Zahran's network,
though it loaded from an outside network. After the claim the 403 stopped. The project was then
renamed `flightmind` and given the domain `flightmind.vercel.app`.

Vercel Authentication is on for the per-deployment URLs (`...-anon-beta-lake.vercel.app` redirects
to a Vercel login). The production domain `flightmind.vercel.app` is public. Give judges only that
one.

Not done: the rollback has not been tried, because the project has only one deployment. Later
deploys need `vercel login` and `vercel link` to the `flightmind` project first; `--temporary` no
longer applies. Re-run the smoke check on 2026-12-03 and before 2026-12-04 14:00 PT.

Build note 2: with the ignore file fixed, the next build on Vercel from Git succeeded but the site
answered 404 on `/` while `/api/` worked. The build script wrote the web build to a root `public/`
folder, and Vercel only publishes `public/` files that exist before the build. The first deploy had
worked only because a local build had left `public/` on disk. The web build now goes to
`services/intel/web_dist/` and the function serves it. The bad deployment was live on
`flightmind.vercel.app` for about two minutes on 2026-11-26 before the domain was pointed back at
the previous deployment. Check a preview deployment's `/` before promoting one.

Build note: a deploy built on Vercel from Git (2026-11-26, `main` at 8d015db) failed in `tsc` with
`Cannot find module '../tests/fixtures/mini.json'`. `.vercelignore` had a bare `fixtures` line,
which follows `.gitignore` rules and so also dropped `web/tests/fixtures`. The local build had
not shown it, because the ignore file only applies to what is uploaded. Root folders in
`.vercelignore` are now anchored with `/`.

CLI note: `npx vercel@latest deploy --temporary` failed on Windows with
`Cannot find module '@vercel/python/package.json'`. It worked after `npm install vercel @vercel/python`
in an empty folder outside the repo, running that folder's `node_modules/.bin/vercel` from the repo
root with `NODE_PATH` set to that `node_modules`. The build writes `uv.lock` (committed) and a
root `.python-version` (not committed: delete it after a local build).

Why not Railway: on 2026-11-26 Railway refused to create a project because the account trial had
expired and a plan had to be selected, Render refused a free service without a card on file
(HTTP 402), and Azure for Students rejected the sign-up. Vercel does not run Dockerfiles, so the
root `Dockerfile` is only for local runs and container hosts; the public URL is built by the
Vercel Python runtime from `pyproject.toml`, `vercel.json`, `.vercelignore`,
`infra/vercel_entry.py` and `infra/vercel_build.py`. `services/intel/web_dist/` is build output and is not committed.

### Steps

Deploy from a clean checkout of the repo root (a fresh `git clone`, or a worktree with no local
changes). `.vercelignore` limits what is uploaded. The `vercel` commands below have **not been run
yet** (the deploy is done by hand); task 19 confirms them against the installed CLI and corrects
this list.

1. **First deploy, no account needed:** `npx vercel@latest deploy --temporary`. It builds and
   prints the public URL and a **claim link. Do not share the claim link, paste it in a chat or an
   issue, or commit it.**
2. **Claim:** Zahran opens the claim link to move the project into his Vercel account. A temporary
   deployment expires if it is not claimed.
3. **Later deploys:** `npx vercel@latest login`, then `npx vercel@latest deploy --prod`.
4. **Smoke check:** `python infra/smoke.py https://<name>.vercel.app` (standard library only; exit 0
   means all six checks passed). Open the URL in a browser with no Vercel session as well.
5. **Roll back:** `npx vercel@latest rollback`, or promote the previous deployment in the Vercel
   dashboard (Deployments, the previous one, Promote to Production). **Not yet tried.** Repeat step 4.

### What lives in Vercel, not in the repo

| Setting | Value |
| --- | --- |
| Project | one project, created by the first deploy and moved to Zahran's account by the claim |
| Domain | the generated `*.vercel.app` domain |
| Environment variables | none in phase 1. Phase 2 adds `FLIGHTMIND_API_APP`, `DATABASE_URL`, `ANTHROPIC_API_KEY` and `GEMINI_API_KEY` as Vercel variables only |
| Plan | Hobby (free). Function duration up to 300 s and Python bundle up to 500 MB |

No secret belongs in the repo.

### Run the image locally

The Docker image is the local check of the same routing code (`serve.py`):

```bash
docker build -t flightmind-web .
docker run -d --name flightmind-web-check -p 8080:8080 -e PORT=8080 flightmind-web
python infra/smoke.py http://localhost:8080
docker rm -f flightmind-web-check
```

### Known workaround: `VITE_API_BASE=/.`

The web client builds URLs as `${VITE_API_BASE}${path}` and falls back to its in-browser fixture
when the base is empty, so it has no way to say "same origin". The Dockerfile and
`infra/vercel_build.py` build with `VITE_API_BASE=/.`: the browser turns `/./api/meta` into
`/api/meta` on whichever host serves the page. This is a workaround for a gap in `web/` (Role 1).
The page cannot tell it is on the mock, so its "Sample data" label does not show; that is why the
README and Devpost text say the public demo uses sample data. Remove the workaround when Role 1
adds a same-origin base.

Checked on 2026-11-26 in a Chromium 156 browser against the local image: the page called
`/api/meta`, `/api/events`, `/api/events/<id>` and `/api/raw/<raw_ref>` on its own origin, all 200,
and reloading on `/?tab=records` and `/?tab=events` worked. Not yet checked on the Vercel URL.
