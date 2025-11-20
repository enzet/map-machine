FROM python:3.9-slim

# Avoid warnings by switching to noninteractive
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libcairo2-dev \
    libgeos-dev \
    pkg-config \
    procps \
    iputils-ping \
    wget \
    ca-certificates \
    netcat-traditional \
    htop \
    vim \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Switch back to dialog for any ad-hoc use of apt
ENV DEBIAN_FRONTEND=dialog

RUN python -m pip install --upgrade pip

# Create a non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Set up working directory
WORKDIR /workspaces/map-machine

# Switch to the vscode user
USER $USERNAME

# Set Python path
ENV PATH="/home/$USERNAME/.local/bin:${PATH}"
