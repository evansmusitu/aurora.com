# Development reference image. Base digest pin + image signature are pre-production gates.
FROM ubuntu:24.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl xz-utils python3 libx11-6 libxi6 libxrender1 \
    libxxf86vm1 libxfixes3 libsm6 libglib2.0-0 libegl1 libxkbcommon0 \
    libgl1 libxext6 libxrandr2 libxinerama1 && \
    rm -rf /var/lib/apt/lists/*
ARG BLENDER_SHA256=9ba871ff2ecd36526b77432745980b7e6664ecd0c7ca11c48849073dcfe06da3
RUN set -eu; \
    curl -fSL --retry 3 -o /tmp/blender.tar.xz https://download.blender.org/release/Blender4.5/blender-4.5.14-linux-x64.tar.xz; \
    echo "${BLENDER_SHA256}  /tmp/blender.tar.xz" | sha256sum -c -; \
    mkdir -p /opt/blender; tar -xf /tmp/blender.tar.xz --strip-components=1 -C /opt/blender; \
    rm /tmp/blender.tar.xz
COPY studio /opt/musitu/studio
WORKDIR /opt/musitu
# Application starts as nonroot; operator MUST also enforce runtime policy.
RUN useradd -m -u 10001 -s /usr/sbin/nologin musitu
USER 10001:10001
ENTRYPOINT ["python3", "/opt/musitu/studio/enterprise_worker.py"]
