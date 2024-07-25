# Base image
FROM python:3.11-slim

# Install wkhtmltopdf
RUN apt-get update && \
    apt-get install -y wget && \
    wget https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.bionic_amd64.deb && \
    apt-get install -y ./wkhtmltox_0.12.6-1.bionic_amd64.deb && \
    rm wkhtmltox_0.12.6-1.bionic_amd64.deb

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copy the application code
COPY . .

# Run the application
CMD ["python", "app.py"]
