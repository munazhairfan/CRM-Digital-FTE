FROM python:3.12-slim

# Prevents Python from writing pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Keeps Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies using pip
# (Switched from uv sync due to Windows Docker I/O issues)
RUN pip install --no-cache-dir .

# Copy project code
COPY production/ ./production/
COPY context/ ./context/
COPY token.json .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "production.main:app", "--host", "0.0.0.0", "--port", "8000"]
