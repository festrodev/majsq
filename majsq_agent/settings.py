"""Settings for the maj$q agent.

Everything that differs between a fork, a laptop and Cloud Run comes from the
environment; see ``.env.example`` at the repo root for the full list. A fork
with no keys at all still runs: ``FESTRO_MOCK=1`` serves the bundled fixture
catalog and the brain falls back to its deterministic composer when there is no
model key.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def _csv(name: str, default: str = "") -> list[str]:
    return [part.strip() for part in os.environ.get(name, default).split(",") if part.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = _flag("DJANGO_DEBUG", "1")
ALLOWED_HOSTS = _csv("DJANGO_ALLOWED_HOSTS", "*")
CSRF_TRUSTED_ORIGINS = _csv("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "core",
    "api",
    "agui",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "majsq_agent.urls"
WSGI_APPLICATION = "majsq_agent.wsgi.application"
ASGI_APPLICATION = "majsq_agent.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

# SQLite, deliberately. A hackathon clone must migrate and run with nothing
# installed but pip packages. Postgres is a deployment concern: add
# `psycopg[binary]` and `dj-database-url` and read DATABASE_URL here when this
# service moves to Cloud Run.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-ca"
TIME_ZONE = os.environ.get("MAJSQ_TZ", "America/Toronto")
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
}

# The Next.js server is the only browser-facing caller and it proxies through
# its own route handlers, so CORS stays closed unless a fork opens it.
CORS_ALLOWED_ORIGINS = _csv("CORS_ALLOWED_ORIGINS")

# ---------------------------------------------------------------- maj$q ----

# Shared secret between majsqweb's server and this service. The browser never
# holds it: Next.js route handlers add it server-side. Requests to /agui/
# without it are rejected (except when MAJSQ_OPEN_AGUI=1, for local curl).
MAJSQ_SERVICE_SECRET = os.environ.get("MAJSQ_SERVICE_SECRET", "")
MAJSQ_OPEN_AGUI = _flag("MAJSQ_OPEN_AGUI", "0")

# Public base URL of majsqweb, used to build map-share links.
MAJSQ_WEB_URL = os.environ.get("MAJSQ_WEB_URL", "http://localhost:3000").rstrip("/")

# --------------------------------------------------------------- Festro ----

FESTRO_API_BASE = os.environ.get("FESTRO_API_BASE", "https://api.festro.com").rstrip("/")
FESTRO_SITE_BASE = os.environ.get("FESTRO_SITE_BASE", "https://festro.com").rstrip("/")
FESTRO_MARKET = os.environ.get("FESTRO_MARKET", "montreal")

# Registered third-party client credentials (apiclients.ApiApplication). Absent
# in a fork — the public catalog answers anonymously today, and the client trust
# gate is in monitor mode — but sent whenever present so maj$q keeps working
# once App Check enforcement is switched on.
FESTRO_CLIENT_ID = os.environ.get("FESTRO_CLIENT_ID", "")
FESTRO_CLIENT_SECRET = os.environ.get("FESTRO_CLIENT_SECRET", "")

# Serve the bundled fixture catalog instead of calling api.festro.com. A fork
# with no credentials runs the whole demo this way.
FESTRO_MOCK = _flag("FESTRO_MOCK", "0")
FESTRO_FIXTURES = Path(os.environ.get("FESTRO_FIXTURES", BASE_DIR / "fixtures"))

# Every outbound call is identifiable, so a noisy fork can be rate-limited
# without touching real Festro users.
FESTRO_USER_AGENT = os.environ.get(
    "FESTRO_USER_AGENT", "majsq-agent/0.1 (+https://github.com/festrodev/majsq)"
)
FESTRO_TIMEOUT = float(os.environ.get("FESTRO_TIMEOUT", "8"))
FESTRO_CACHE_SECONDS = int(os.environ.get("FESTRO_CACHE_SECONDS", "60"))

# ---------------------------------------------------------------- Model ----

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
MAJSQ_MODEL = os.environ.get("MAJSQ_MODEL", "gpt-5")

# -------------------------------------------------------------- Telegram ----

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
# Echoed by Telegram as X-Telegram-Bot-Api-Secret-Token on every webhook POST.
# Without it the webhook refuses to process updates.
TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
