#!/bin/bash
# Coleta dataset de trafego NORMAL
# Uso: bash run_experiment.sh [duracao_segundos]
DURATION=${1:-300}
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$REPO_DIR/docker"

echo "[1] Subindo CARLA + ecu_bridge + ids_monitor..."
docker compose --profile ids up -d carla_server ecu_bridge ids_monitor

echo "[2] Aguardando CARLA iniciar (30s)..."
sleep 30

echo "[3] Rodando simulacao por ${DURATION}s..."
docker compose run --rm \
    -e DURATION="$DURATION" \
    carla_client \
    python3 carla_client.py --headless --duration "$DURATION" --npcs 30

echo "[4] Encerrando servicos..."
docker compose down

echo "Concluido. Dataset em: $REPO_DIR/traffic_logs/"
