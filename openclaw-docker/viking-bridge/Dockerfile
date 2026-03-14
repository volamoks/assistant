FROM python:3.11-slim

WORKDIR /app

# Install dependencies
# Note: openviking might have specific installation instructions. 
RUN pip install --default-timeout=100 fastapi uvicorn pydantic openviking openai httpx

COPY main.py .

EXPOSE 8100

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8100"]
