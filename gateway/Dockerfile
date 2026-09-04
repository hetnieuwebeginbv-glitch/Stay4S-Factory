FROM python:3.12-slim-bookworm
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY gateway /app/gateway
COPY hoofdagent /app/hoofdagent
ENV PYTHONPATH=/app
EXPOSE 8080
CMD ["uvicorn", "gateway.app:app", "--host", "0.0.0.0", "--port", "8080"]
