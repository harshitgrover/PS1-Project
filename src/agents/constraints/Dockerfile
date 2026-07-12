FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/src/agents/constraints
COPY . /app/src/agents/constraints/

ENV PYTHONPATH=/app

EXPOSE 8002

CMD ["uvicorn", "src.agents.constraints.api:app", "--host", "0.0.0.0", "--port", "8002"]
