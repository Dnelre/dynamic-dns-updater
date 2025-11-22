FROM python:3.14-slim

# Set working directory inside container
WORKDIR /app

# Copy only requirements first (better build cache)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY script/ .

# Run your script
CMD ["python", "dns-updater.py"]
