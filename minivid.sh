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

docker compose up -d
echo "MiniVid est disponible sur http://localhost:${MINIVID_PORT:-8080}."
