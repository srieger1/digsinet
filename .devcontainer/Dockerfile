# Set debian buster as base for the digsinet environment
FROM mcr.microsoft.com/vscode/devcontainers/python:3.12-bookworm
# Allow containerlab version to be set in devcontainer.json
ARG CLAB_VERSION
# Set permissions for correct mounting in devcontainer.json
RUN mkdir -p /home/vscode/.vscode-server/bin
RUN chown -R vscode:vscode /home/vscode/.vscode-server
# Install basic tools for container lab
RUN apt update && \
    apt upgrade -y && \
    apt install -y --no-install-recommends \
    sshpass \
    curl \
    iputils-ping \
    htop \
    yamllint \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /usr/share/doc && rm -rf /usr/share/man \
    && apt clean

COPY requirements.txt /tmp/pip-tmp
#RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
#   && rm -rf /tmp/pip-tmp

# Install the preferred version of container lab
RUN bash -c "$(curl -sL https://get.containerlab.dev)" -- -v ${CLAB_VERSION}

