# Base image
FROM python:3.11-slim

# Install necessary packages
RUN apt-get update && apt-get install -y \
    wkhtmltopdf \
    && apt-get clean

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set environment variables
ENV FLASK_APP=app.py

# Expose the port Flask will run on
EXPOSE 8080

# Run the application
CMD ["flask", "run", "--host=0.0.0.0", "--port=8080"]
