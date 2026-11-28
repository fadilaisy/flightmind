#!/usr/bin/env bash
# SCRUM-72: bring FlightMind up on one Ubuntu host (Oracle Always Free Ampere A1, arm64).
#
#   git clone <repo> && cd <repo> && infra/deploy/up.sh
#
# It installs Docker if missing, creates infra/deploy/.env on the first run, builds the
# images, starts the stack, waits until it is healthy and prints the URL. Safe to re-run:
# it rebuilds and restarts, and keeps the database and uploads.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$HERE/docker-compose.prod.yml"
ENV_FILE="$HERE/.env"

say() { printf '==> %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# --- 1. Docker -----------------------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  say "Docker is not installed. Installing it with Docker's official script (get.docker.com)."
  command -v curl >/dev/null 2>&1 || { sudo apt-get update -y && sudo apt-get install -y curl ca-certificates; }
  tmp="$(mktemp)"
  curl -fsSL https://get.docker.com -o "$tmp"
  sudo sh "$tmp"
  rm -f "$tmp"
  sudo systemctl enable --now docker
fi

# Use sudo for docker when the current user is not in the docker group (first run after install).
DOCKER=(docker)
if ! docker info >/dev/null 2>&1; then
  sudo docker info >/dev/null 2>&1 || die "Docker is installed but not running. Try: sudo systemctl start docker"
  DOCKER=(sudo docker)
fi
"${DOCKER[@]}" compose version >/dev/null 2>&1 || die "The 'docker compose' plugin is missing. Install docker-compose-plugin."

# --- 2. .env -------------------------------------------------------------------------------
[ -f "$ENV_FILE" ] || { cp "$HERE/.env.example" "$ENV_FILE"; chmod 600 "$ENV_FILE"; say "Created $ENV_FILE"; }

# Read the current value of a key (empty when unset).
get_env() { sed -n "s/^$1=//p" "$ENV_FILE" | tail -n1; }
# Set a key in .env (replaces the line, or appends it).
set_env() {
  if grep -q "^$1=" "$ENV_FILE"; then
    sed -i "s|^$1=.*|$1=$2|" "$ENV_FILE"
  else
    printf '%s=%s\n' "$1" "$2" >> "$ENV_FILE"
  fi
}

if [ -z "$(get_env POSTGRES_PASSWORD)" ]; then
  # The database is created with this password on first start only; keep it afterwards.
  set_env POSTGRES_PASSWORD "$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  say "Generated a database password in $ENV_FILE"
fi

HOST="$(get_env FLIGHTMIND_HOST)"
if [ -z "$HOST" ]; then
  ip="$(curl -4 -fsS --max-time 10 https://ifconfig.me 2>/dev/null || true)"
  case "$ip" in
    *[!0-9.]*|'') die "Could not find this machine's public IP. Set FLIGHTMIND_HOST in $ENV_FILE (for example 203-0-113-5.sslip.io)." ;;
  esac
  HOST="$(printf '%s' "$ip" | tr . -).sslip.io"
  set_env FLIGHTMIND_HOST "$HOST"
  say "FLIGHTMIND_HOST not set: using $HOST"
fi

# --- 3. Build and start --------------------------------------------------------------------
say "Building and starting (the first build compiles the ASTERIX decoder and takes several minutes)"
"${DOCKER[@]}" compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build

# --- 4. Wait for health --------------------------------------------------------------------
say "Waiting for the app to become healthy"
cid="$("${DOCKER[@]}" compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps -q app)"
[ -n "$cid" ] || die "The app container did not start. See: docker compose -f $COMPOSE_FILE logs app"
status=starting
for _ in $(seq 1 60); do
  status="$("${DOCKER[@]}" inspect --format '{{.State.Health.Status}}' "$cid" 2>/dev/null || echo unknown)"
  [ "$status" = healthy ] && break
  sleep 5
done
[ "$status" = healthy ] || die "The app is '$status' after 5 minutes. See: docker compose -f $COMPOSE_FILE logs app db"

URL="https://$HOST"
say "Waiting for HTTPS at $URL (the certificate is requested on first start)"
ok=0
for _ in $(seq 1 24); do
  if curl -fsS --max-time 10 "$URL/api/meta" >/dev/null 2>&1; then ok=1; break; fi
  sleep 5
done

if [ "$ok" = 1 ]; then
  say "FlightMind is up: $URL"
  echo "Check it from any machine:  python infra/smoke.py $URL"
else
  echo "The containers are healthy, but $URL did not answer within 2 minutes." >&2
  echo "Most likely ports 80 and 443 are closed: check the Oracle security list and iptables" >&2
  echo "(infra/deploy/README.md, step 3), then look at: docker compose -f $COMPOSE_FILE logs caddy" >&2
  exit 1
fi
