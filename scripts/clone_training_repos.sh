#!/bin/sh
# Clone open-source Python corpora for NodeAudit / GraphReview training.
# Licensed MIT/Apache per upstream projects. Uses shallow clones to save disk.
# POSIX sh — safe to run as: sh scripts/clone_training_repos.sh

set -eu

ROOT="$(CDPATH='' cd "$(dirname "$0")/.." && pwd)"
CORPUS_DIR="${CORPUS_DIR:-$ROOT/training_corpus}"
mkdir -p "$CORPUS_DIR"

clone_if_missing() {
  url="$1"
  dest="$2"
  if [ -d "$dest" ] && [ -e "$dest/.git" ]; then
    echo "skip (exists): $dest"
    return
  fi
  git clone --depth=1 "$url" "$dest"
}

echo "Corpus directory: $CORPUS_DIR"

# Tier 1 — core training
clone_if_missing https://github.com/pallets/flask "$CORPUS_DIR/flask"
clone_if_missing https://github.com/celery/celery "$CORPUS_DIR/celery"
clone_if_missing https://github.com/psf/requests "$CORPUS_DIR/requests"
clone_if_missing https://github.com/encode/httpx "$CORPUS_DIR/httpx"
clone_if_missing https://github.com/fastapi/fastapi "$CORPUS_DIR/fastapi"
clone_if_missing https://github.com/sqlalchemy/sqlalchemy "$CORPUS_DIR/sqlalchemy"
clone_if_missing https://github.com/pydantic/pydantic "$CORPUS_DIR/pydantic"

# Tier 2 — topology diversity (large clones)
clone_if_missing https://github.com/spotify/luigi "$CORPUS_DIR/luigi"
clone_if_missing https://github.com/scrapy/scrapy "$CORPUS_DIR/scrapy"
clone_if_missing https://github.com/paramiko/paramiko "$CORPUS_DIR/paramiko"
clone_if_missing https://github.com/django/django "$CORPUS_DIR/django"
clone_if_missing https://github.com/apache/airflow "$CORPUS_DIR/airflow"

# Tier 3 — synthetic bug injection / smaller templates
# Small Flask-Smorest API (Real Python course flavor; original realpython/flask-smorest-api URL is not public)
clone_if_missing https://github.com/tecladocode/rest-api-smorest-docker "$CORPUS_DIR/rest-api-smorest-docker"
clone_if_missing https://github.com/tiangolo/full-stack-fastapi-template "$CORPUS_DIR/full-stack-fastapi-template"
clone_if_missing https://github.com/miguelgrinberg/flasky "$CORPUS_DIR/flasky"
clone_if_missing https://github.com/testdrivenio/fastapi-tdd-docker "$CORPUS_DIR/fastapi-tdd-docker"

count="$(find "$CORPUS_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l)"
echo "Top-level corpus entries: $count"
