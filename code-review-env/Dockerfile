FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and uv in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl nodejs npm \
    build-essential cmake ninja-build pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.local/bin:${PATH}"

# Copy and install Python dependencies using uv for speed
COPY requirements.txt /app/
RUN uv pip install --system --no-cache -r requirements.txt

COPY . /app
RUN python -m db.seed sample_project/ --force
EXPOSE 7860
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
