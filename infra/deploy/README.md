# infra/deploy: one-command deploy on an always-on arm64 host (SCRUM-72)

Target: an Oracle Cloud **Always Free** Ampere A1 VM (arm64, Ubuntu). A person creates the
account and the VM (steps 1 to 4); after that, `infra/deploy/up.sh` does the rest.

| File | What it is |
| --- | --- |
| `docker-compose.prod.yml` | `db` (Postgres + TimescaleDB + pgvector, `contracts/schema.sql` loaded on first start), `app` (real API, upload worker, Linux ASTERIX decoder, built web UI; target `app` of `infra/Dockerfile.app`), `caddy` (HTTPS) |
| `Caddyfile` | Reverse proxy to the app for `${FLIGHTMIND_HOST}`, with automatic certificates |
| `.env.example` | The variables the stack reads. Copy to `.env`; `.env` is git-ignored |
| `up.sh` | Installs Docker if missing, writes `.env`, builds, starts, waits for health, prints the URL |

Volumes: `flightmind_pgdata` (database), `flightmind_uploads` (uploaded recordings and reports,
mounted at `/data` in the app), `caddy_data` and `caddy_config` (certificates). Only Caddy publishes
ports (80, 443); the database and the app are reachable only inside the compose network.

## What a person does in the Oracle console

Oracle's console and limits change; check each point against the current Oracle documentation
("Always Free Resources", "Security Lists") before relying on it. The numbers below were written
from memory and **have not been checked against the docs**.

1. **Account.** Sign up at cloud.oracle.com. A card is needed for identity checks. Pick the home
   region carefully: it cannot be changed, and A1 capacity differs by region ("Out of capacity" is
   common; retry later or in another availability domain).
2. **Budget alert at $1.** Billing and Cost Management, Budgets, create a budget of $1 per month
   with an alert at a low threshold (for example 1 percent of the budget) that emails you. Always Free
   resources should cost nothing, so any alert means something outside the free tier was created.
3. **Create the VM.** Compute, Instances, Create instance.
   - Image: Canonical Ubuntu 22.04 or 24.04 (aarch64).
   - Shape: Ampere, `VM.Standard.A1.Flex`. Always Free allows up to 4 OCPU and 24 GB RAM in total
     across A1 instances; **2 OCPU and 12 GB is enough** for this stack and leaves room.
   - Boot volume: 50 GB or more (Always Free allows up to 200 GB of block storage in total). The
     decoder build and recordings need space.
   - Networking: a public subnet with a **public IPv4 address**. Add your SSH public key.
4. **Open ports 80 and 443 in two places.**
   - Oracle side: Networking, Virtual cloud networks, your VCN, Security Lists, the subnet's list,
     Add Ingress Rules: source `0.0.0.0/0`, protocol TCP, destination port `80`, and another for `443`
     (UDP 443 as well if you want HTTP/3).
   - VM side: Oracle's Ubuntu images ship iptables rules that reject other ports. After `ssh ubuntu@<ip>`:

     ```bash
     sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
     sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
     sudo iptables -I INPUT 6 -m state --state NEW -p udp --dport 443 -j ACCEPT
     sudo netfilter-persistent save   # package iptables-persistent; keeps the rules after a reboot
     ```

     Run `sudo iptables -L INPUT -n --line-numbers` first: the rules must sit **above** the final
     `REJECT` rule (the position 6 above is typical for the Oracle Ubuntu image, adjust if yours differs).
5. **Pay As You Go and idle reclamation.** Oracle may reclaim Always Free compute instances it
   considers idle (as I recall: over a 7-day window, the 95th percentile of CPU, and for A1 also memory
   and network, all under about 20 percent). This stack idles low, so it can qualify. Upgrading the
   account to **Pay As You Go** is, as I recall, the way to exempt instances from reclamation; Always
   Free resources stay free after the upgrade as long as you stay inside the limits, and the $1 budget
   alert from step 2 is the safety net. **Confirm the current rules in Oracle's "Always Free Resources"
   page (the idle instance reclamation section) before relying on this.**

## Deploy

On the VM:

```bash
git clone <repo-url> flightmind && cd flightmind
git checkout <branch>            # if not the default branch
infra/deploy/up.sh
```

`up.sh`:

1. installs Docker with Docker's official script if `docker` is missing;
2. creates `infra/deploy/.env` from `.env.example` (mode 600), generates `POSTGRES_PASSWORD`, and when
   `FLIGHTMIND_HOST` is empty uses `<public-ip-with-dashes>.sslip.io` (a free name that resolves to
   that IP, so Caddy can get a certificate without you owning a domain);
3. builds the images (the first build compiles the ASTERIX decoder from source: expect several
   minutes on 2 OCPU) and starts the stack;
4. waits for the app's health check, then for `https://<host>/api/meta`, and prints the URL.

Optional keys go in `infra/deploy/.env` before or after the first run (then run `up.sh` again):
`ANTHROPIC_API_KEY` turns on the cited agent, `GEMINI_API_KEY` the embeddings. Without them the site
works and `/api/ask` answers from canned text. Never commit `.env`.

Re-running `up.sh` rebuilds and restarts and keeps the database and uploads. To start over, including
the database (it deletes all data):
`docker compose -f infra/deploy/docker-compose.prod.yml --env-file infra/deploy/.env down -v`.
`contracts/schema.sql` loads only into an empty database volume, so a schema change needs this reset.

## Load data

A fresh database has no recordings. Either upload a classic `.pcap` through the web UI, or load
the fixture seed:

```bash
docker compose -f infra/deploy/docker-compose.prod.yml --env-file infra/deploy/.env \
  exec -T db psql -U flightmind -d flightmind < fixtures/seed.sql
```

Run one app process only (the compose file does): the upload worker is per process.

## Smoke check

From any machine with Python 3 (standard library only):

```bash
python infra/smoke.py https://<host>
```

Exit 0 means the six checks passed (page, `/api/meta`, events, one event, one raw record, one track).
It needs at least one ready recording, so load the seed or upload a file first; on an empty database
`/api/events` fails with "expected a non-empty list of events".

## Not verified

`up.sh`, the Compose file and the image were written on a machine without Docker and have not been
run, and nothing has been tried on Oracle. The first real run on the VM is the test; expect to fix
small things (for example the A1 capacity message, or the iptables rule position).
