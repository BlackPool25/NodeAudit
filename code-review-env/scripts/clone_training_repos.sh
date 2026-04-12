#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CORPUS_DIR="${CORPUS_DIR:-${ROOT_DIR}/training_corpus}"

mkdir -p "${CORPUS_DIR}"

clone_if_missing() {
  local repo_url="$1"
  local target_name="$2"
  local target_path="${CORPUS_DIR}/${target_name}"

  if [[ -d "${target_path}" ]]; then
    echo "[SKIP] ${target_name} already exists"
    return
  fi

  echo "[CLONE] ${repo_url} -> ${target_name}"
  git clone --depth 1 "${repo_url}" "${target_path}"
}

# Tier 1
clone_if_missing https://github.com/psf/requests.git requests
clone_if_missing https://github.com/pallets/flask.git flask
clone_if_missing https://github.com/fastapi/fastapi.git fastapi
clone_if_missing https://github.com/pydantic/pydantic.git pydantic

# Tier 2
clone_if_missing https://github.com/celery/celery.git celery
clone_if_missing https://github.com/scrapy/scrapy.git scrapy
clone_if_missing https://github.com/django/django.git django
clone_if_missing https://github.com/apache/airflow.git airflow

# Tier 3
clone_if_missing https://github.com/frappe/erpnext.git erpnext
clone_if_missing https://github.com/testdrivenio/fastapi-tdd-docker.git fastapi-tdd-docker
clone_if_missing https://github.com/tecladocode/rest-api-smorest-docker.git rest-api-smorest-docker

echo "[DONE] Training corpus cloned into ${CORPUS_DIR}"
