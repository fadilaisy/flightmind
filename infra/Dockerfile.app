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

# Stage 2: runtime. Same Debian release as stage 1, so the expat and libstdc++ versions match.
FROM python:3.12-slim-bookworm
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
USER app
# Prints the decoded block count of a recording: docker run -v /path:/data flightmind-app /data/x.pcap
ENTRYPOINT ["python", "-c", "import sys; from flightmind_pipeline.pcap_source import decode_blocks; print(sum(1 for _ in decode_blocks(sys.argv[1])))"]
