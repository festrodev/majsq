# maj$q agent — one image, two transports (HTTP contract + AG-UI stream).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # Cloud Run gives a writable /tmp and nothing else. SQLite lives there by
    # default, which means the conversation store is LOST ON EVERY RESTART —
    # fine for a demo, wrong for anything real. Set DATABASE_URL and add
    # psycopg + dj-database-url when this needs to survive a redeploy.
    MAJSQ_DB_DIR=/tmp

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt gunicorn==23.0.0

COPY . .

# Collected at build time so the container filesystem can stay read-only.
RUN python manage.py collectstatic --noinput || true

# Cloud Run sets $PORT and ignores EXPOSE, but it documents the contract and
# makes `docker run -p 8000:8000` work locally without a flag.
EXPOSE 8000

# migrate on boot: the agent's schema is small and the instance count is one.
# If this ever scales past a single instance, move migrations to a release step
# — concurrent boots racing on the same schema is a bad way to find out.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn majsq_agent.wsgi --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4 --timeout 60"]
