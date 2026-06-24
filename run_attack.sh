#!/bin/bash
# Coleta dataset com ATAQUE AEB spoofing
# Uso: bash run_attack.sh [modo: suppress|inject] [duracao_segundos]
MODE=${1:-suppress}
DURATION=${2:-120}
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$REPO_DIR/docker"

echo "[1] Subindo CARLA + ecu_bridge + ids_monitor..."
docker compose --profile ids up -d carla_server ecu_bridge ids_monitor

echo "[2] Aguardando CARLA iniciar (30s)..."
sleep 30

echo "[3] Iniciando simulacao em background..."
docker compose run -d --name carla_client_atk \
    carla_client \
    python3 carla_client.py --headless --duration "$DURATION" --npcs 30

echo "[4] Aguardando 10s antes de injetar ataque..."
sleep 10

echo "[5] Injetando ataque: modo=$MODE duracao=${DURATION}s..."
docker compose --profile attack run --rm \
    -e MODE="$MODE" \
    attacker \
    python attacks/spoof.py --mode "$MODE" --duration "$DURATION"

echo "[6] Aguardando simulacao terminar..."
docker wait carla_client_atk 2>/dev/null || true

echo "[7] Encerrando..."
docker compose down
docker rm carla_client_atk 2>/dev/null || true

echo "Concluido. Dataset em: $REPO_DIR/traffic_logs/"
