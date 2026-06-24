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
    wget curl xvfb x11vnc novnc websockify \
    openbox

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

echo "=== [6/6] Scripts de execucao ==="

# Experimento headless (coleta de dataset)
cat > /workspace/run_experiment.sh << 'EOF'
#!/bin/bash
CARLA_DIR="/workspace/carla"
REPO_DIR="/workspace/carla-someip"
DURATION=${1:-300}

echo "[1] Iniciando CARLA headless..."
"$CARLA_DIR/CarlaUE4.sh" -RenderOffScreen -quality-level=Epic -nosound &
CARLA_PID=$!
sleep 20

echo "[2] Docker: ecu_bridge + ids_monitor..."
cd "$REPO_DIR/docker"
docker compose up -d ecu_bridge
docker compose --profile ids up -d ids_monitor

echo "[3] Simulacao por ${DURATION}s..."
source "$CARLA_DIR/venv/bin/activate"
cd "$REPO_DIR"
python carla_client.py --headless --duration "$DURATION" --npcs 30

echo "[4] Encerrando..."
docker compose down
kill $CARLA_PID 2>/dev/null || true
echo "Concluido. Logs em $REPO_DIR/traffic_logs/"
EOF
chmod +x /workspace/run_experiment.sh

# Display visual via VNC (porta 6080 — abrir no RunPod)
cat > /workspace/start_vnc.sh << 'EOF'
#!/bin/bash
CARLA_DIR="/workspace/carla"

echo "[VNC] Iniciando display virtual :1 (1920x1080)..."
pkill Xvfb x11vnc websockify 2>/dev/null || true
Xvfb :1 -screen 0 1920x1080x24 &
sleep 2

echo "[VNC] Iniciando x11vnc..."
x11vnc -display :1 -nopw -listen localhost -forever -quiet &
sleep 1

echo "[VNC] Iniciando noVNC na porta 6080..."
websockify --web=/usr/share/novnc/ 6080 localhost:5900 &
sleep 1

echo "[VNC] Iniciando CARLA com display..."
export DISPLAY=:1
"$CARLA_DIR/CarlaUE4.sh" -quality-level=Epic -nosound &
echo ""
echo "======================================="
echo " Acesse no browser do RunPod:"
echo " porta 6080 → /vnc.html"
echo "======================================="
EOF
chmod +x /workspace/start_vnc.sh

echo ""
echo "======================================"
echo " Setup concluido!"
echo "======================================"
echo " CARLA:      $CARLA_DIR"
echo " Projeto:    $REPO_DIR"
echo " Executar:   bash /workspace/run_experiment.sh [duracao_segundos]"
echo " Exemplo:    bash /workspace/run_experiment.sh 300"
echo "======================================"
