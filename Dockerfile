# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install system dependencies (if required)
RUN apt-get update && apt-get install -y --no-install-recommends gcc && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on
EXPOSE 5000

# Set the Flask app environment variable
ENV FLASK_APP=app.py

# Set a default environment variable for production
ENV FLASK_ENV=production

# Run the application with Gunicorn
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:5000", "--workers", "4", "--threads", "2"]
