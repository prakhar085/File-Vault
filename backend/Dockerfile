FROM python:3.10

WORKDIR /app

# Install system dependencies including Node.js for frontend build
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (for frontend build)
# Update CA certificates first, then install Node.js using NodeSource repository
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    update-ca-certificates && \
    mkdir -p /etc/apt/keyrings && \
    curl -k -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_18.x nodistro main" > /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends nodejs npm && \
    rm -rf /var/lib/apt/lists/* && \
    node --version && \
    npm --version

# Copy backend files
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy backend project files
COPY backend/ .

# Build frontend (copy frontend files and build)
COPY frontend/ /tmp/frontend
WORKDIR /tmp/frontend
RUN npm ci && npm run build

# Copy built frontend files to backend staticfiles
WORKDIR /app
RUN cp -r /tmp/frontend/dist/* staticfiles/ 2>/dev/null || true && \
    cp /tmp/frontend/dist/index.html staticfiles/index.html 2>/dev/null || true

# Create necessary directories
RUN mkdir -p media staticfiles data

# Set permissions
RUN chmod -R 777 data media staticfiles

# Collect static files
RUN python manage.py collectstatic --noinput

# Make start script executable
RUN chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"] 