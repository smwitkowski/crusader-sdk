FROM ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 AS uv

FROM debian:bookworm-slim@sha256:c67e92c8099ba22853ab4cfda7cfb494d253d6012ca82dee98ba8976772af018

# Wine and the game are 32-bit; build on the amd64 platform.
# hadolint ignore=DL3008
RUN dpkg --add-architecture i386 && apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl unzip wine wine32:i386 libgl1:i386 libgl1-mesa-dri:i386 \
    libglx-mesa0:i386 xvfb xdotool x11-utils procps python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL -o /tmp/ucp.zip \
    https://github.com/UnofficialCrusaderPatch/UnofficialCrusaderPatch3/releases/download/v3.0.7/UCP3-3.0.7-77c6accf14.zip \
    && printf "%s\n" "a979816e4475e054b46b2f2793ef6a2109cfd03bf650e58e2b2f764804a8c105  /tmp/ucp.zip" > /tmp/ucp.sha256 \
    && sha256sum -c /tmp/ucp.sha256 && rm /tmp/ucp.sha256 \
    && mkdir /opt/ucp && unzip -q /tmp/ucp.zip -d /opt/ucp && rm /tmp/ucp.zip

WORKDIR /opt/sdk
COPY --from=uv /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv export --frozen --extra bridge --no-dev --no-emit-project -o /tmp/requirements.txt \
    && python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --no-deps --require-hashes -r /tmp/requirements.txt \
    && /opt/venv/bin/pip install --no-cache-dir --no-deps . \
    && rm /tmp/requirements.txt
COPY ucp3/crusader-bridge-0.1.0 /opt/sdk/ucp3/crusader-bridge-0.1.0
COPY docker/ucp-config.yml /opt/sdk/ucp-config.yml
COPY scripts/check-game-files.sh /opt/sdk/check-game-files.sh
COPY docker/run.sh /opt/sdk/run.sh
RUN useradd --create-home --uid 1000 crusader && mkdir /opt/crusader && chown crusader:crusader /opt/crusader
USER crusader
ENV HOME=/home/crusader WINEPREFIX=/home/crusader/.wine WINEARCH=win32 WINEDEBUG=-all DISPLAY=:99
ENV CRUSADER_GAME_DIR=/opt/crusader
ENTRYPOINT ["/bin/sh", "/opt/sdk/run.sh"]
