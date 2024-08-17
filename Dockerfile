# Official Python image from Docker Hub
FROM python:3.10

# Set environment variables to ensure Python outputs to stdout/stderr in real-time
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file to the working directory
COPY requirements.txt /app/

# Install the Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the entire Django project into the working directory
COPY . /app/

# Expose port 8000 to be used by the container
EXPOSE 8000

# Command to run the Django app on startup
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
