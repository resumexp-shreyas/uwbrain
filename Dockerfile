# Use official Python image
FROM python:3.11

# Set working directory inside container
WORKDIR /app

# Copy dependency list
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port 8080 (custom port)
EXPOSE 8080

# Run Django app with Gunicorn
CMD ["gunicorn", "-b", ":8080", "uwbrain.wsgi:application"]