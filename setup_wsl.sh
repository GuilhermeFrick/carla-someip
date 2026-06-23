#!/bin/bash
# Configura ambiente WSL2 Ubuntu 22.04 para o projeto carla-someip.
# Uso: bash setup_wsl.sh

set -e

echo "=== carla-someip WSL2 setup ==="

# Pacotes base
sudo apt-get update -q
sudo apt-get install -y --no-install-recommends \
    git \
    python3 \
    python3-pip \
    python3-venv \
    tcpdump \
    tshark \
    wireshark-common \
    net-tools \
    iputils-ping \
    curl \
    jq

# Python deps para rodar os scripts de analise dentro do WSL
pip3 install --user \
    scapy \
    pandas \
    numpy \
    xgboost \
    scikit-learn \
    joblib

echo ""
echo "=== Verificacao ==="
python3 --version
git --version
tcpdump --version 2>&1 | head -1
echo ""
echo "Pronto. Para usar o Docker, instale o Docker Desktop no Windows"
echo "e habilite a integracao WSL2 em Settings > Resources > WSL Integration."
