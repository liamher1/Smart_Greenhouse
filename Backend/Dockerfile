# 1. Use an official Python runtime as a parent image
FROM python:3.11-slim

# 2. Set environment variables
# Prevents Python from writing .pyc files and ensures output is sent to logs
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Set the working directory in the container
WORKDIR /app

# 4. Install system dependencies (needed for some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

# 5. Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of the code
# (In development, this will be overridden by the Volume mirroring)
COPY . .

# 7. Command to run the application
# We use "--reload" to ensure the app restarts when you change code in PyCharm
CMD ["python", "main.py"]