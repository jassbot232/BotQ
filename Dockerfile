FROM python:3.9-slim

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY bot.py .
COPY .env .

# Create temporary directory for large files
RUN mkdir -p /tmp/videos && chmod 755 /tmp/videos

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TEMP_DIR=/tmp/videos
ENV MAX_FILE_SIZE=2147483648  # 2GB in bytes

# Expose port (though we're using polling)
EXPOSE 8080

# Run the bot
CMD ["python", "bot.py"]
