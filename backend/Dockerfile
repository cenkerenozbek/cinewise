FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Bundle pre-generated ML artifacts into the image
COPY artifacts/ /artifacts/

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2
