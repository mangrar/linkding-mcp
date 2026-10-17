FROM python:3.12-slim

WORKDIR /app

# Install system dependencies if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY server.py .

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    LINKDING_URL="http://localhost:9090" \
    MCP_TRANSPORT="streamable-http" \
    MCP_HOST="0.0.0.0" \
    MCP_PORT="8000"

EXPOSE 8000

# Default entrypoint for HTTP microservice (reads MCP_TRANSPORT: streamable-http or sse)
CMD ["python", "server.py"]
