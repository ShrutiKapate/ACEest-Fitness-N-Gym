FROM python:3.10-slim

# install system dependencies for tkinter
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      tk \
      tcl \
      libx11-6 \
      && rm -rf /var/lib/apt/lists/*

# copy and install python deps
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "app.py"]

FROM jenkins/jenkins:lts

FROM node:18
WORKDIR /app
COPY . .
RUN npm install
CMD ["npm", "start"]

USER root

# Install Jenkins plugins
RUN jenkins-plugin-cli --plugins \
    git \
    docker-workflow \
    junit \
    warnings-ng
