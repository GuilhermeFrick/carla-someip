#!/bin/bash
# Setup carla-someip no RunPod — tudo em Docker
# Uso: bash setup_runpod.sh
set -e

REPO_DIR="/carla-someip"

echo "=== [1/3] Docker daemon ==="
if docker info > /dev/null 2>&1; then
    echo "Docker OK"
else
    echo "Iniciando dockerd..."
    dockerd > /tmp/dockerd.log 2>&1 &
    sleep 10
    docker info > /dev/null 2>&1 && echo "Docker OK" || { echo "ERRO: Docker nao iniciou. Ver /tmp/dockerd.log"; exit 1; }
fi

echo "=== [2/3] Repositorio ==="
if [ ! -d "$REPO_DIR" ]; then
    git clone https://github.com/GuilhermeFrick/carla-someip.git "$REPO_DIR"
else
    git -C "$REPO_DIR" pull
fi

echo "=== [3/3] Build das imagens ==="
cd "$REPO_DIR/docker"
docker compose build ecu_bridge ids_monitor carla_client

mkdir -p "$REPO_DIR/traffic_logs"

echo ""
echo "======================================"
echo " Setup concluido!"
echo "======================================"
echo ""
echo " Experimento normal (300s):"
echo "   bash /carla-someip/run_experiment.sh"
echo ""
echo " Com ataque:"
echo "   bash /carla-someip/run_attack.sh"
echo "======================================"
