#!/bin/sh
# Seed GraphReview SQLite DBs from training_corpus subpaths (application core only).
# Run after scripts/clone_training_repos.sh. Executes from code-review-env so `python -m db.seed` resolves.
# POSIX sh — safe to run as: sh scripts/seed_training_corpus.sh

set -eu

ROOT="$(CDPATH='' cd "$(dirname "$0")/.." && pwd)"
ENV_DIR="$ROOT/code-review-env"
CORPUS_DIR="${CORPUS_DIR:-$ROOT/training_corpus}"
OUT_DIR="${CORPUS_DB_DIR:-$ROOT/outputs/corpus_dbs}"

if [ ! -d "$ENV_DIR" ]; then
  echo "error: expected code-review-env at $ENV_DIR" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
cd "$ENV_DIR"

seed_one() {
  db_basename="$1"
  relative_path="$2"
  target="$CORPUS_DIR/$relative_path"
  db_path="$OUT_DIR/${db_basename}.db"

  if [ ! -d "$target" ]; then
    echo "[skip] missing directory: $target"
    return 0
  fi

  echo "[seed] $target -> $db_path"
  python -m db.seed "$target" --db-path "$db_path" --force
}

# Tier 1 — single package roots matching training corpus seed table
seed_one corpus_flask "flask/src/flask"
# Full celery package (app/, worker/, backends/ live under this tree)
seed_one corpus_celery "celery/celery"
seed_one corpus_requests "requests/src/requests"
seed_one corpus_httpx "httpx/httpx"
seed_one corpus_fastapi "fastapi/fastapi"
seed_one corpus_sqlalchemy "sqlalchemy/lib/sqlalchemy"
seed_one corpus_pydantic "pydantic/pydantic"

# Tier 2
seed_one corpus_luigi "luigi/luigi"
# Focus: middleware stack modules (omit tests/spiders noise)
seed_one corpus_scrapy_core "scrapy/scrapy/core"
seed_one corpus_scrapy_pipelines "scrapy/scrapy/pipelines"
seed_one corpus_paramiko "paramiko/paramiko"
seed_one corpus_airflow "airflow/airflow"

# Django: seed focused subtrees (separate DBs — no cross-edges between DBs)
seed_one corpus_django_db "django/django/db"
seed_one corpus_django_http "django/django/http"
seed_one corpus_django_auth "django/django/contrib/auth"

# Tier 3 — small templates (paths vary; adjust if upstream layout changes)
# App root: models/, resources/, app.py (Flask-Smorest sample)
seed_one corpus_rest_api_smorest_docker "rest-api-smorest-docker"
seed_one corpus_fullstack_fastapi_template "full-stack-fastapi-template/backend/app"
seed_one corpus_flasky "flasky/app"
# Layout: project/{app,db,migrations,tests}
if [ -d "$CORPUS_DIR/fastapi-tdd-docker/project" ]; then
  seed_one corpus_fastapi_tdd "fastapi-tdd-docker/project"
else
  echo "[skip] fastapi-tdd-docker/project — clone testdrivenio/fastapi-tdd-docker first"
fi

echo "Done. Databases under: $OUT_DIR"
