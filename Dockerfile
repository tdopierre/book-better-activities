FROM python:3.12-slim

# Install uv
RUN python3 -m pip install uv

# Set up working dir
WORKDIR /app
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync

# Copy application code
COPY src/ ./src/
COPY config.yaml ./

ENV PYTHONPATH="/app"

# Run the scheduler
CMD ["uv", "run", "python", "src/scripts/scheduled_booking.py"]
