# SCRUM-71: the pipeline with a native Linux ASTERIX decoder, for linux/amd64 and linux/arm64.
#
# The decoder is CroatiaControlLtd/asterix (GPL-2.0, see infra/README.md). It is cloned and built
# here at a pinned release tag; its source is not stored in this repo. Only the binary and its
# config folder reach the final image.
#
# Build from the repo root:
#   docker buildx build --platform linux/arm64,linux/amd64 -f infra/Dockerfile.app -t flightmind-app .

# Stage 1: build the asterix tool. Only distribution packages, no architecture-specific names.
FROM debian:bookworm-slim AS asterix-build
# Latest GitHub release when this was written (2026-11-28).
ARG ASTERIX_REF=v2.8.10
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential cmake git ca-certificates libexpat1-dev \
 && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch "${ASTERIX_REF}" https://github.com/CroatiaControlLtd/asterix.git /src
WORKDIR /src
# The CMake project writes the executable to <build dir>/install/asterix.
RUN cmake -S . -B /build -DCMAKE_BUILD_TYPE=Release \
 && cmake --build /build --parallel \
 && test -x /build/install/asterix
# Copy only what the final image needs, in the layout the environment variables point at.
RUN mkdir -p /out/bin /out/config \
 && cp /build/install/asterix /out/bin/asterix \
 && cp /src/install/config/* /out/config/ \
 && cp /src/COPYING /out/COPYING.asterix

# Stage 2 (SCRUM-72, only built for the `app` target): the web UI, as in the root Dockerfile.
# contracts/ is copied because the web build reads contracts/types.ts from ../contracts.
FROM node:22-slim AS web
WORKDIR /src
COPY contracts/ contracts/
COPY web/package.json web/package-lock.json web/
WORKDIR /src/web
RUN npm ci
COPY web/ ./
# "/." makes the browser turn "/./api/meta" into "/api/meta" on the serving host (see infra/README.md).
ARG VITE_API_BASE=/.
ENV VITE_API_BASE=${VITE_API_BASE}
RUN npm run build

# Stage 3: runtime. Same Debian release as stage 1, so the expat and libstdc++ versions match.
FROM python:3.12-slim-bookworm AS runtime
RUN apt-get update \
 && apt-get install -y --no-install-recommends libexpat1 libstdc++6 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 app
COPY --from=asterix-build /out/bin/asterix /opt/asterix/bin/asterix
COPY --from=asterix-build /out/config/ /opt/asterix/config/
COPY --from=asterix-build /out/COPYING.asterix /opt/asterix/COPYING
ENV FLIGHTMIND_ASTERIX_BIN=/opt/asterix/bin/asterix \
    FLIGHTMIND_ASTERIX_INI=/opt/asterix/config/asterix.ini
WORKDIR /app
COPY services/pipeline/pyproject.toml services/pipeline/
COPY services/pipeline/flightmind_pipeline/ services/pipeline/flightmind_pipeline/
RUN pip install --no-cache-dir ./services/pipeline

# Stage 4 (SCRUM-72): the deployable app. Real API (Postgres), the upload worker, the decoder and
# the built web UI, behind serve.py on one origin. Build with `--target app`.
# The code sits at /srv/flightmind/services/intel because real_api finds the repo root as
# parents[3] of its own file.
FROM runtime AS app
WORKDIR /srv/flightmind/services/intel
COPY services/intel/requirements-serve.txt .
RUN pip install --no-cache-dir -r requirements-serve.txt
COPY services/intel/real_api/ real_api/
COPY services/intel/agent/ agent/
COPY services/intel/embeddings/ embeddings/
COPY services/intel/serve.py .
COPY --from=web /src/web/dist /srv/flightmind/web-dist
RUN mkdir -p /data/uploads /data/reports && chown -R app:app /data
ENV FLIGHTMIND_API_APP=real_api.app:app \
    FLIGHTMIND_WEB_DIST=/srv/flightmind/web-dist \
    FLIGHTMIND_UPLOAD_DIR=/data/uploads \
    FLIGHTMIND_REPORT_DIR=/data/reports \
    FLIGHTMIND_API_BASE=http://127.0.0.1:8000
USER app
EXPOSE 8000
# One process only: the upload worker is per process (see services/intel/README.md).
CMD ["uvicorn", "serve:app", "--host", "0.0.0.0", "--port", "8000"]

# Final stage, so a plain `docker build` still gives the SCRUM-71 image.
FROM runtime AS pipeline
USER app
# Prints the decoded block count of a recording: docker run -v /path:/data flightmind-app /data/x.pcap
ENTRYPOINT ["python", "-c", "import sys; from flightmind_pipeline.pcap_source import decode_blocks; print(sum(1 for _ in decode_blocks(sys.argv[1])))"]