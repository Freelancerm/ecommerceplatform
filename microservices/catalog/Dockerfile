FROM python:3.11-slim

WORKDIR /src
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY microservices/catalog/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared-libs /app/shared
RUN pip install /app/shared/

COPY microservices/catalog/src /src/app/

COPY microservices/catalog/scripts .
RUN python seed_db.py

