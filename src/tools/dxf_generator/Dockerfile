FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for ezdxf/matplotlib if necessary
RUN apt-get update && apt-get install -y --no-install-recommends \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/src/tools/dxf_generator
COPY . /app/src/tools/dxf_generator/

ENV PYTHONPATH=/app

EXPOSE 8003

CMD ["uvicorn", "src.tools.dxf_generator.api:app", "--host", "0.0.0.0", "--port", "8003"]
