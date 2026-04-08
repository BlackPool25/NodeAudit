FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
RUN python -m db.seed sample_project/ --force
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
