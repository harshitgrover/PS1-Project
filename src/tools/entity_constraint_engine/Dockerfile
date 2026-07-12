FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/src/tools/entity_constraint_engine
COPY . /app/src/tools/entity_constraint_engine/

ENV PYTHONPATH=/app

EXPOSE 8001

CMD ["uvicorn", "src.tools.entity_constraint_engine.api:app", "--host", "0.0.0.0", "--port", "8001"]
