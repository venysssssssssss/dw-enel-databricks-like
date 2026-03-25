"""Superset configuration for local development."""

from __future__ import annotations

import os

SQLALCHEMY_DATABASE_URI = os.environ.get(
    "DATABASE_URL",
    "postgresql://enel:enel123@postgres:5432/superset",
)
SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "changeme")
WTF_CSRF_ENABLED = True
ENABLE_PROXY_FIX = True
SUPERSET_WEBSERVER_TIMEOUT = 120
SQL_MAX_ROW = 50000
ROW_LIMIT = 10000
SAMPLES_ROW_LIMIT = 1000
