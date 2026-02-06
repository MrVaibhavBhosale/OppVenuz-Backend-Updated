from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ================= SECURITY =================

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = False   # RENDER VAR NEHMICH FALSE

ALLOWED_HOSTS = [
    "oppvenuz-backend-new.onrender.com",
    "api.oppvenuz.com",
    "api-dev.oppvenuz.com",
    ".onrender.com",
]

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ================= CORS & CSRF =================

CORS_ALLOWED_ORIGINS = [
    "https://oppvenuz.com",
    "https://www.oppvenuz.com",
    "https://admin.oppvenuz.com",
    "http://localhost:3000",
]

CSRF_TRUSTED_ORIGINS = [
    "https://oppvenuz.com",
    "https://api.oppvenuz.com",
    "https://oppvenuz-backend-new.onrender.com",
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    "authorization",
    "content-type",
]

# ================= EMAIL & SMS =================

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")

TEXT_LOCAL_API_KEY = os.getenv("TEXT_LOCAL_API_KEY")
TEXTLOCAL_SENDER = os.getenv("TEXTLOCAL_SENDER", "OPPVNZ")

# ================= APPS =================

INSTALLED_APPS = [
    "admin_master",

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "drf_yasg",
    "rest_framework",
    "django_filters",
    "corsheaders",

    "vendor",
    "user",
    "oauth2_provider",
    "manager",
    "team_head",
    "executive",
    "celebrity",
    "multiRole",
]

AUTH_USER_MODEL = "admin_master.AdminUser"

# ================= AUTH =================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "vendor.authentication.VendorJWTAuthentication",
        "admin_master.authentication.AdminJWTAuthentication",
    ),

    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],

    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "vendor.backends.VendorAuthBackend",
    "admin_master.backends.AdminAuthBackend",
]

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ================= MIDDLEWARE =================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "corsheaders.middleware.CorsMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# ================= DATABASE =================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
    }
}

# ================= STATIC =================

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ================= LOGGING =================

LOGGING_DIR = os.path.join(BASE_DIR, "log")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },

    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}

# ================= DEFAULT ADMIN =================

DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD")
DEFAULT_ADMIN_MOBILE = os.getenv("DEFAULT_ADMIN_MOBILE")
DEFAULT_ADMIN_FULL_NAME = os.getenv("DEFAULT_ADMIN_FULL_NAME")

TIME_ZONE = "Asia/Kolkata"
USE_TZ = True
