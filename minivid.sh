#!/bin/sh
set -eu

cd "$(dirname "$0")"

if ! docker compose version >/dev/null 2>&1; then
    echo "Docker Compose est requis : https://docs.docker.com/engine/install/"
    exit 1
fi

if [ ! -f .env ]; then
    cp .env.example .env
    if command -v openssl >/dev/null 2>&1; then
        secret_key=$(openssl rand -hex 32)
    else
        secret_key=$(od -An -N32 -tx1 /dev/urandom | tr -d ' \n')
    fi
    sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$secret_key/" .env
    mkdir -p videos data cache
    echo "Configuration créée dans .env (vidéos : ./videos)."
fi

mode=${MINIVID_GPU:-auto}
overlay=""

case "$mode" in
    auto)
        if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
            overlay=docker-compose.nvidia.yml
        elif [ -e /dev/dri/renderD128 ]; then
            overlay=docker-compose.vaapi.yml
        fi
        ;;
    nvidia) overlay=docker-compose.nvidia.yml ;;
    vaapi|intel|amd) overlay=docker-compose.vaapi.yml ;;
    cpu|none) ;;
    *) echo "MINIVID_GPU doit valoir auto, cpu, nvidia, vaapi, intel ou amd."; exit 1 ;;
esac

if [ "$overlay" = docker-compose.vaapi.yml ]; then
    video_gid=$(getent group video 2>/dev/null | cut -d: -f3 || true)
    render_gid=$(getent group render 2>/dev/null | cut -d: -f3 || true)
    export MINIVID_VIDEO_GID="${video_gid:-44}"
    export MINIVID_RENDER_GID="${render_gid:-109}"
fi

if [ -n "$overlay" ] && docker compose -f docker-compose.yml -f "$overlay" config >/dev/null 2>&1; then
    if docker compose -f docker-compose.yml -f "$overlay" up -d; then
        echo "MiniVid démarré avec l'accélération $(printf '%s' "$overlay" | sed 's/docker-compose\.//;s/\.yml//')."
        exit 0
    fi
    if [ "$mode" != auto ]; then
        echo "L'accélération demandée n'est pas disponible. Relancez avec MINIVID_GPU=cpu."
        exit 1
    fi
    echo "GPU non disponible pour Docker, démarrage en CPU."
fi

docker compose up -d
echo "MiniVid est disponible sur http://localhost:${MINIVID_PORT:-8080} (mode CPU)."
