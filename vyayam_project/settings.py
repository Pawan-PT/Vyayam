"""
VYAYAM STRENGTH TRAINING - DJANGO SETTINGS
"""

import os
from pathlib import Path
import dj_database_url  # ADD THIS

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-dev-fallback-change-in-production')

DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if h.strip()]
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']
if not DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['.onrender.com']  # ADDED — catches your render subdomain automatically

CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in
    os.environ.get('DJANGO_CSRF_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000').split(',')
]

# ... INSTALLED_APPS, MIDDLEWARE, TEMPLATES unchanged ...

# DATABASE — REPLACED manual parsing with dj-database-url
_db_url = os.environ.get('DATABASE_URL', '')
if _db_url:
    DATABASES = {
        'default': dj_database_url.config(
            default=_db_url,
            conn_max_age=600,
            ssl_require=not DEBUG,  # enforce SSL in prod
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ... rest unchanged until LOGGING ...

# LOGGING — FIXED: no file handler in production (Render disk is ephemeral)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}