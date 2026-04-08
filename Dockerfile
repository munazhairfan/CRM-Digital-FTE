FROM python:3.12

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1
# Keeps Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy dependency files
COPY pyproject.toml .

# Install dependencies using pip
RUN pip install --no-cache-dir .

# Copy project code
COPY production/ ./production/
COPY prototype.py .
COPY context/ ./context/

# Run the application
CMD ["uvicorn", "production.main:app", "--host", "0.0.0.0", "--port", "8000"]
