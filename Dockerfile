FROM python:3.9-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium-driver \
    chromium \
    curl gnupg ca-certificates \
    libnss3 libxss1 libxcomposite1 libxrandr2 libatk1.0-0 libgtk-3-0 \
    libx11-xcb1 libxdamage1 libgbm1 libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables so Selenium finds Chrome
ENV CHROME_BIN=/usr/bin/chromium
ENV PATH="${CHROME_BIN}:${PATH}"

# Set workdir
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Expose port
EXPOSE 5000

# Run the app using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "2", "--timeout", "90", "app:app"]

