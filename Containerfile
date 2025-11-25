# OSIA Clean Binary Container
# Based on Universal Base Image for RHEL 9
FROM registry.access.redhat.com/ubi9/ubi:latest

# Set labels
LABEL name="osia-binary" \
      version="0.2.0-alpha17" \
      description="OpenShift Infrastructure Automation - Clean Binary"

# Install required packages
RUN dnf update -y && \
    dnf install -y --allowerasing \
    python3.11 \
    python3.11-pip \
    python3.11-devel \
    git \
    bind-utils \
    curl \
    wget \
    unzip \
    && dnf clean all \
    && rm -rf /var/cache/dnf

# Install kubectl manually
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/kubectl

# Install Poetry globally
RUN curl -sSL https://install.python-poetry.org | python3.11 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Set working directory for build
WORKDIR /build

# Copy only necessary files for building
COPY pyproject.toml poetry.lock README.md ./
COPY osia/ ./osia/

# Install dependencies and build the package
RUN poetry config virtualenvs.create false && \
    poetry install --only=main --no-root && \
    poetry build

# Install the built package globally
RUN pip3.11 install dist/*.whl

# Create a clean working directory
WORKDIR /workspace

# Create directories for installers and clusters
RUN mkdir -p /workspace/installers /workspace/clusters

# Create a non-root user for security
RUN useradd -m -u 1001 osia && \
    chown -R osia:osia /workspace

# Switch to non-root user
USER osia

# Set working directory
WORKDIR /workspace

# Set environment variables
ENV PYTHONPATH="/usr/local/lib/python3.11/site-packages"

# Default command
CMD ["osia", "--help"]
