#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CORPUS_DIR="${CORPUS_DIR:-${ROOT_DIR}/training_corpus}"
CORPUS_DB_DIR="${CORPUS_DB_DIR:-${ROOT_DIR}/outputs/corpus_dbs}"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python}"

mkdir -p "${CORPUS_DB_DIR}"
cd "${ROOT_DIR}"

seed_one() {
  local name="$1"
  local rel_path="$2"
  local source_path="${CORPUS_DIR}/${rel_path}"
  local db_path="${CORPUS_DB_DIR}/${name}.db"

  if [[ ! -d "${source_path}" ]]; then
    echo "[WARN] Missing source for ${name}: ${source_path}"
    return
  fi

  echo "[SEED] ${name} from ${source_path}"
  GRAPHREVIEW_DB_PATH="${db_path}" "${PYTHON_BIN}" -m db.seed "${source_path}" --force
}

# Tier 1
seed_one requests requests/src/requests
seed_one flask flask/src/flask
seed_one fastapi fastapi/fastapi
seed_one pydantic pydantic/pydantic

# Tier 2
seed_one celery celery/celery
seed_one scrapy_core scrapy/scrapy/core
seed_one scrapy_pipelines scrapy/scrapy/pipelines
seed_one django_db django/django/db
seed_one django_http django/django/http
seed_one django_auth django/django/contrib/auth
seed_one airflow airflow/airflow

# Tier 3
seed_one erpnext erpnext/erpnext
seed_one fastapi_tdd fastapi-tdd-docker/project
seed_one rest_api_smorest rest-api-smorest-docker/app

echo "[DONE] Corpus seeding complete -> ${CORPUS_DB_DIR}"
