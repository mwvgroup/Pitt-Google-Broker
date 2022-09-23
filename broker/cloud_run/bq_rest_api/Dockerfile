FROM python:3.9-slim

WORKDIR /app

# Make sure python output doesn't get caught in buffer
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Run the app
COPY main.py .
CMD [ "gunicorn",  "--bind",  "0.0.0.0:8080", "main:app" ]
