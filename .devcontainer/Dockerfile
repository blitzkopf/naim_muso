

FROM mcr.microsoft.com/vscode/devcontainers/python:0-3.11

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Uninstall pre-installed formatting and linting tools
# They would conflict with our pinned versions
RUN pipx uninstall black
RUN pipx uninstall pydocstyle
RUN pipx uninstall pycodestyle
RUN pipx uninstall mypy
RUN pipx uninstall pylint

RUN \
    curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        # Additional library needed by some tests and accordingly by VScode Tests Discovery
        bluez \
        libudev-dev \
        libavformat-dev \
        libavcodec-dev \
        libavdevice-dev \
        libavutil-dev \
        libswscale-dev \
        libswresample-dev \
        libavfilter-dev \
        libpcap-dev \
        libturbojpeg0 \
        libyaml-dev \
        libxml2 \
        git \
        cmake \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src

# get Home Assistant core
RUN git clone --depth 1 https://github.com/home-assistant/core \
    && pip3 install -e core/
# Setup hass-release
RUN git clone --depth 1 https://github.com/home-assistant/hass-release \
    && pip3 install -e hass-release/

# Install Python dependencies from requirements
COPY requirements.txt ./
#COPY homeassistant/package_constraints.txt homeassistant/package_constraints.txt
RUN pip3 install -r requirements.txt --use-deprecated=legacy-resolver
COPY requirements-dev.txt ./
RUN pip3 install -r requirements-dev.txt --use-deprecated=legacy-resolver
RUN rm -rf requirements.txt requirements_test.txt requirements_test_pre_commit.txt homeassistant/

# Set the default shell to bash instead of sh
ENV SHELL /bin/bash