# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install system-level dependencies for Tkinter and a virtual display (Xvfb)
# These are required because they are not included in the standard Python image
RUN apt-get update && apt-get install -y \
    python3-tk \
    tcl-dev \
    tk-dev \
    libx11-dev \
    xvfb \
    x11-apps \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# No CMD needed if you only use this for 'auto-test' in GitHub Actions.
# If you want to run the app normally, use:
# CMD ["xvfb-run", "python", "app.py"]