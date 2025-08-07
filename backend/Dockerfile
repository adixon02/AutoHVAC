FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for production with enhanced OCR support
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        # Build dependencies
        libjpeg-dev zlib1g-dev libfreetype6-dev build-essential \
        gcc g++ python3-dev \
        # Tesseract OCR with English language pack
        tesseract-ocr tesseract-ocr-eng \
        # PDF processing tools
        libpoppler-utils poppler-utils libpoppler-cpp-dev \
        # OpenCV and PaddleOCR dependencies
        libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 \
        # PyMuPDF dependencies
        libmupdf-dev mupdf-tools \
        # Fonts for better OCR accuracy
        fonts-liberation fonts-dejavu-core \
        # Utilities
        file psmisc wget curl \
        && rm -rf /var/lib/apt/lists/* && \
        apt-get clean

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
# PaddleOCR is now included in requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

EXPOSE 8000

# Production command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]