import os
import sys
from pathlib import Path

import dj_database_url
from django.contrib.messages import constants as message_constants
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

_RENDER = os.environ.get("RENDER", "").lower() in {"1", "true", "yes"}
_PYTEST = "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv)

DEBUG = os.environ.get("DEBUG", "0" if _RENDER else "1") == "1"

SECRET_KEY = os.environ.get("SECRET_KEY", "").strip()
if not SECRET_KEY:
    if _RENDER:
        raise ImproperlyConfigured("Defina SECRET_KEY no ambiente de produção.")
    SECRET_KEY = "django-insecure-climatec-somente-desenvolvimento"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]
if _RENDER:
    ALLOWED_HOSTS.append(".onrender.com")
    _external = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    if _external and _external not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_external)
if DEBUG or _PYTEST:
    for _host in ("localhost", "127.0.0.1", "testserver"):
        if _host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_host)

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if _RENDER:
    CSRF_TRUSTED_ORIGINS.append("https://*.onrender.com")
    if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
        CSRF_TRUSTED_ORIGINS.append(
            f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}"
        )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "atendimento",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "atendimento.context_processors.empresa",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

_database_url = os.environ.get("DATABASE_URL", "").strip()
if _database_url:
    DATABASES = {
        "default": dj_database_url.parse(
            _database_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
    DATABASES["default"].pop("CONN_MAX_AGE", None)
    DATABASES["default"].pop("CONN_HEALTH_CHECKS", None)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Fortaleza"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_ROOT.mkdir(exist_ok=True)
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
WHITENOISE_USE_FINDERS = DEBUG

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "entrar"
LOGIN_REDIRECT_URL = "painel"
LOGOUT_REDIRECT_URL = "home"

CSRF_FAILURE_VIEW = "atendimento.views_public.csrf_falhou"
SESSION_COOKIE_SECURE = _RENDER
CSRF_COOKIE_SECURE = _RENDER
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

MESSAGE_TAGS = {
    message_constants.ERROR: "danger",
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO"},
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
