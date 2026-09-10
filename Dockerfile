FROM python:3.11-slim-bookworm

WORKDIR /app

# System deps for weasyprint (PDF generation) and solc
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc libssl-dev \
        libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install solc compiler (required by slither-analyzer)
RUN pip install solc-select && solc-select install 0.8.19 && solc-select use 0.8.19

COPY src/ src/

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD uvicorn src.web.app:app --host 0.0.0.0 --port ${PORT:-8000}
