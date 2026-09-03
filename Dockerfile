# syntax=docker/dockerfile:1

# facetmark in a container. Adapted from hister's deployment story (its
# Dockerfile + compose.yml), which is the shape a self-hosted personal search
# engine should ship: non-root, one writable volume, a healthcheck, and an
# image that carries the source rather than fetching a version from PyPI --
# the container is the pin.
#
# The service binds 0.0.0.0 here because that is what a container must do to
# be reachable through a port mapping; the compose file binds the *host* side
# of the mapping to 127.0.0.1, so the default deployment is still loopback-
# only from the machine's point of view. Publishing it wider is a one-line
# edit the reader makes on purpose.

FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="facetmark" \
      org.opencontainers.image.description="Local-first bookmark retrieval on SQLite" \
      org.opencontainers.image.source="https://github.com/88lin/facetmark" \
      org.opencontainers.image.licenses="MIT"

# A non-root user that owns the data directory, so the SQLite file the whole
# product lives in is never written as root.
RUN groupadd -g 65532 facetmark \
    && useradd -u 65532 -g facetmark -m -d /home/facetmark facetmark \
    && mkdir -p /data \
    && chown 65532:65532 /data

WORKDIR /app

# Two layers, in dependency order: the requirements first, then the source.
# A source-only change then rebuilds only the (small, no-deps) second layer.
# The dependency list is read out of pyproject.toml rather than restated here,
# because a second copy of it would drift the first time someone edited one.
# Installed from Python rather than through the shell: a marker such as
# ``tomli; python_version < '3.11'`` is one requirement with spaces in it,
# and shell word-splitting would turn its comparator into a redirection.
COPY pyproject.toml README.md ./
RUN python -c "import subprocess, sys, tomllib; deps = tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']; subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--no-cache-dir', *deps])"

COPY LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps .

USER 65532:65532
ENV FACETMARK_DATA_DIR=/data \
    FACETMARK_HOST=0.0.0.0 \
    FACETMARK_PORT=8787 \
    PYTHONUNBUFFERED=1

VOLUME /data
EXPOSE 8787

# urllib rather than curl: slim has no curl, and installing it just to answer
# "are you up" is a package the image does not otherwise need.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8787/health', timeout=4).status == 200 else 1)"]

CMD ["facetmark", "serve"]
