# Use Ubuntu 20.04 as base
FROM ubuntu:20.04

# Set non-interactive mode to avoid user prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:alex-p/tesseract-ocr-devel -y \
    && apt-get update \
    && apt-get install -y tesseract-ocr \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Verify installation
RUN tesseract --version

# Set working directory
WORKDIR /app

# Default command
CMD ["tail", "-f", "/dev/null"]