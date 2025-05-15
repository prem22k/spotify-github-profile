FROM python:3.11-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies required for Pillow and other system packages
RUN apt-get update && apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    && apt-get clean

WORKDIR /app

COPY ./api/requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/
