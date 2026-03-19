FROM python:3.12-slim

RUN pip install --no-cache-dir mistune==3.0.2

WORKDIR /app
COPY server.py .
COPY webapp/ webapp/

ENV PORT=7080
ENV VAULT_PATH=/data/obsidian/vault

EXPOSE 7080

CMD ["python3", "server.py"]
