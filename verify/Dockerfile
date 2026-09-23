# Verification image: contains both the Python and Node toolchains so one
# one-shot container can run backend tests, the frontend production build
# and a live API smoke test, then exit with a meaningful status code.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python toolchain (including pytest and httpx for the smoke checks).
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install -r /app/backend/requirements.txt

# Frontend toolchain pre-fetched at image build time so the one-shot verify
# run itself needs no registry access.
COPY frontend/package.json frontend/package-lock.json /app/frontend/
RUN cd /app/frontend && npm ci --no-audit --no-fund

COPY backend /app/backend
COPY frontend /app/frontend
COPY verify /app/verify

CMD ["bash", "/app/verify/run.sh"]
