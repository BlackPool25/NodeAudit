FROM python:3.11-slim

WORKDIR /app/code-review-env
COPY code-review-env/requirements.txt /app/code-review-env/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY code-review-env /app/code-review-env

ENV GRAPHREVIEW_SOURCE_ROOT=/app/code-review-env/sample_project
RUN python -m db.seed sample_project/ --force

CMD ["uvicorn", "server.app:app", "--app-dir", "/app/code-review-env", "--host", "0.0.0.0", "--port", "7860"]
