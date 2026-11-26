# SCRUM-38 phase 1: one image serving the built web UI and the mock API on one origin.
# Build from the repo root:  docker build -t flightmind-web .

# Stage 1: build the web UI. contracts/ is copied because the web build reads
# contracts/types.ts from ../contracts relative to web/.
FROM node:22-slim AS web
WORKDIR /src
COPY contracts/ contracts/
COPY web/package.json web/package-lock.json web/
WORKDIR /src/web
RUN npm ci
COPY web/ ./
# WORKAROUND, not a design: the web client has no same-origin mode (an empty
# VITE_API_BASE selects the in-browser fixture). "/." makes the browser turn
# "/./api/meta" into "/api/meta" on whatever host serves the page. Remove when
# Role 1 adds a same-origin base (requirements.md, Open item 2).
ARG VITE_API_BASE=/.
ENV VITE_API_BASE=${VITE_API_BASE}
RUN npm run build

# Stage 2: runtime. Only fastapi and uvicorn; no test or dev packages.
FROM python:3.12-slim
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY services/intel/requirements-serve.txt .
RUN pip install --no-cache-dir -r requirements-serve.txt
COPY services/intel/mock_api/ mock_api/
COPY services/intel/agent/ agent/
COPY services/intel/serve.py .
COPY --from=web /src/web/dist /app/web-dist
ENV FLIGHTMIND_WEB_DIST=/app/web-dist
USER app
# sh -c so ${PORT:-8000} expands (Railway sets PORT); exec so uvicorn gets the stop signal.
CMD ["sh", "-c", "exec uvicorn serve:app --host 0.0.0.0 --port ${PORT:-8000}"]
