"""
Roda no Windows junto com o CARLA.
Recebe telemetria do main.py via fila e envia para o container via TCP.
"""

import json
import socket
import threading
import queue
import time

BRIDGE_HOST = 'localhost'   # IP do container — ajustar se necessario
BRIDGE_PORT = 5000

_queue: queue.Queue = queue.Queue(maxsize=500)
_conn:  socket.socket | None = None
_lock   = threading.Lock()


def _connect():
    global _conn
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((BRIDGE_HOST, BRIDGE_PORT))
            with _lock:
                _conn = s
            print(f'[BRIDGE] Conectado ao container {BRIDGE_HOST}:{BRIDGE_PORT}')
            return
        except ConnectionRefusedError:
            print('[BRIDGE] Container nao disponivel, tentando em 2s...')
            time.sleep(2)


def _worker():
    global _conn
    _connect()
    while True:
        data = _queue.get()
        msg  = (json.dumps(data) + '\n').encode()
        try:
            with _lock:
                if _conn:
                    _conn.sendall(msg)
        except (BrokenPipeError, OSError):
            print('[BRIDGE] Conexao perdida, reconectando...')
            _connect()


def start():
    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def enviar(dados: dict):
    try:
        _queue.put_nowait(dados)
    except queue.Full:
        pass   # descarta se fila cheia (nao bloqueia a simulacao)
