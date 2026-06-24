#!/bin/bash
# Setup CARLA + carla-someip no RunPod (Ubuntu 22.04 + CUDA)
# Uso: bash setup_runpod.sh
set -e

CARLA_VERSION="0.9.15"
CARLA_DIR="/workspace/carla"
REPO_DIR="/workspace/carla-someip"

echo "=== [1/6] Dependencias do sistema ==="
apt-get update -q
apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    libjpeg8 libtiff6 libssl-dev \
    wget curl xvfb

# Docker ja disponivel no RunPod via host socket
docker info > /dev/null 2>&1 && echo "Docker OK" || echo "AVISO: Docker nao disponivel"

echo "=== [2/6] CARLA $CARLA_VERSION ==="
mkdir -p "$CARLA_DIR"
cd "$CARLA_DIR"

if [ ! -f "CarlaUE4.sh" ]; then
    wget -q --show-progress \
        "https://carla-releases.s3.us-east-005.backblazeb2.com/Linux/CARLA_${CARLA_VERSION}.tar.gz" \
        -O carla.tar.gz
    tar -xzf carla.tar.gz --strip-components=1
    rm carla.tar.gz
    echo "CARLA extraido em $CARLA_DIR"
else
    echo "CARLA ja instalado."
fi

echo "=== [3/6] Python venv + carla wheel ==="
python3 -m venv "$CARLA_DIR/venv"
source "$CARLA_DIR/venv/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet \
    carla=="${CARLA_VERSION}" \
    numpy \
    pygame
deactivate

echo "=== [4/6] Repositorio carla-someip ==="
if [ ! -d "$REPO_DIR" ]; then
    git clone https://github.com/GuilhermeFrick/carla-someip.git "$REPO_DIR"
else
    git -C "$REPO_DIR" pull
fi

echo "=== [5/6] Docker images ==="
cd "$REPO_DIR/docker"
docker compose build ecu_bridge

echo "=== [6/6] Script de execucao ==="
cat > /workspace/run_experiment.sh << 'EOF'
#!/bin/bash
# Inicia CARLA headless + ecu_bridge + carla_client

CARLA_DIR="/workspace/carla"
REPO_DIR="/workspace/carla-someip"
DURATION=${1:-300}   # segundos, default 5 min

echo "[1] Iniciando CARLA headless..."
"$CARLA_DIR/CarlaUE4.sh" -RenderOffScreen -quality-level=Epic -nosound &
CARLA_PID=$!
echo "CARLA PID=$CARLA_PID — aguardando 20s..."
sleep 20

echo "[2] Iniciando ecu_bridge..."
cd "$REPO_DIR/docker"
docker compose up -d ecu_bridge

echo "[3] Iniciando ids_monitor..."
docker compose --profile ids up -d ids_monitor

echo "[4] Rodando simulacao por ${DURATION}s (headless)..."
source "$CARLA_DIR/venv/bin/activate"
cd "$REPO_DIR"
python carla_client.py --headless --duration "$DURATION" --npcs 30

echo "[5] Encerrando..."
docker compose down
kill $CARLA_PID 2>/dev/null || true
echo "Experimento concluido. Logs em $REPO_DIR/data/"
EOF
chmod +x /workspace/run_experiment.sh

echo ""
echo "======================================"
echo " Setup concluido!"
echo "======================================"
echo " CARLA:      $CARLA_DIR"
echo " Projeto:    $REPO_DIR"
echo " Executar:   bash /workspace/run_experiment.sh [duracao_segundos]"
echo " Exemplo:    bash /workspace/run_experiment.sh 300"
echo "======================================"
