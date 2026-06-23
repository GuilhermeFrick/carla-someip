"""
Bridge TCP (Windows CARLA) → SOME/IP UDP (Docker/WSL2).

Windows roda o CARLA e envia telemetria via TCP.
Este modulo roda no container Linux, recebe e republica como SOME/IP.
"""

import json
import socket
import threading

from someip_network.network import SomeIPNetwork
from someip_network import BRIDGE_PORT

TICK_COUNTERS = {}
FREQ = {
    'dynamics': 1,   # todo tick (50Hz se FREQUENCIA=50)
    'gnss':     10,  # a cada 10 ticks (5Hz se FREQUENCIA=50)
    'imu':      1,   # todo tick
    'lidar':    5,   # a cada 5 ticks (10Hz)
    'adas':     2,   # a cada 2 ticks (25Hz)
}


def _should_send(service: str, tick: int) -> bool:
    return tick % FREQ[service] == 0


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
    buf  = b''
    tick = 0
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
                    tick += 1
                    if _should_send('dynamics', tick):
                        net.send_dynamics(data)
                    if _should_send('gnss', tick) and data.get('latitude'):
                        net.send_gnss(data)
                    if _should_send('imu', tick) and data.get('acel_x') is not None:
                        net.send_imu(data)
                    if _should_send('lidar', tick) and data.get('lidar_pontos'):
                        net.send_lidar(data)
                    if _should_send('adas', tick):
                        net.send_adas(data)
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        print(f'[BRIDGE] Conexao encerrada: {e}')
    finally:
        conn.close()
        print('[BRIDGE] CARLA desconectado.')


if __name__ == '__main__':
    serve()
