"""
Bridge TCP (Windows CARLA) → SOME/IP UDP (Docker/WSL2).

Windows roda o CARLA e envia telemetria via TCP.
Este módulo roda no container Linux, recebe e republica como SOME/IP.
"""

import json
import socket

from someip_network.network import SomeIPNetwork
from someip_network import BRIDGE_PORT


def serve(host='0.0.0.0', port=BRIDGE_PORT):
    net = SomeIPNetwork()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(1)
    print(f'[BRIDGE] Aguardando CARLA em {host}:{port}...')

    while True:
        conn, addr = srv.accept()
        print(f'[BRIDGE] CARLA conectado: {addr}')
        _handle(conn, net)


def _handle(conn: socket.socket, net: SomeIPNetwork):
    buf = b''
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
            while b'\n' in buf:
                line, buf = buf.split(b'\n', 1)
                try:
                    data = json.loads(line.decode())
                    net.publish_tick(data)
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        print(f'[BRIDGE] Conexão encerrada: {e}')
    finally:
        conn.close()
        print('[BRIDGE] CARLA desconectado.')


if __name__ == '__main__':
    serve()
