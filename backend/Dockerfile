FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for production
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libjpeg-dev zlib1g-dev libfreetype6-dev build-essential \
        tesseract-ocr tesseract-ocr-eng \
        libpoppler-utils poppler-utils \
        libgl1-mesa-glx libglib2.0-0 \
        libmupdf-dev mupdf-tools \
        fonts-liberation fonts-dejavu-core \
        file \
        psmisc \
        && rm -rf /var/lib/apt/lists/* && \
        apt-get clean

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    # Optional: Install PaddleOCR for enhanced OCR if enabled via env
    pip install --no-cache-dir paddlepaddle==2.5.2 -i https://mirror.baidu.com/pypi/simple && \
    pip install --no-cache-dir paddleocr

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

EXPOSE 8000

# Production command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]