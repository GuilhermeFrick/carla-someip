"""
SomeIPNetwork — publica serviços SOME/IP via UDP.
Analogo ao CAN_Network do yes-carla-can.
"""

import json
import socket
import threading
import time

from someip_network.packet import SomeIPPacket
from someip_network import (
    SERVICE_DYNAMICS, SERVICE_GNSS, SERVICE_IMU,
    SERVICE_LIDAR, SERVICE_ADAS, METHOD_NOTIFY,
)

MULTICAST_GROUP = '239.0.0.1'
MULTICAST_PORT  = 30490


class SomeIPNetwork:
    def __init__(self, host='0.0.0.0', port=MULTICAST_PORT):
        self.host    = host
        self.port    = port
        self._sock   = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        self._session = 0
        self._lock    = threading.Lock()

    def _next_session(self) -> int:
        with self._lock:
            self._session = (self._session % 0xFFFF) + 1
            return self._session

    def _send(self, service_id: int, payload: dict):
        pkt = SomeIPPacket(
            service_id = service_id,
            method_id  = METHOD_NOTIFY,
            session_id = self._next_session(),
            payload    = payload,
        )
        self._sock.sendto(pkt.encode(), (MULTICAST_GROUP, self.port))

    # ── Serviços ──────────────────────────────────────────────────────────────

    def send_dynamics(self, data: dict):
        self._send(SERVICE_DYNAMICS, {
            'velocidade_kmh': data.get('velocidade_kmh'),
            'throttle':       data.get('throttle'),
            'brake':          data.get('brake'),
            'steering':       data.get('steering'),
            'marcha_re':      data.get('marcha_re'),
        })

    def send_gnss(self, data: dict):
        self._send(SERVICE_GNSS, {
            'latitude':  data.get('latitude'),
            'longitude': data.get('longitude'),
            'altitude':  data.get('altitude'),
        })

    def send_imu(self, data: dict):
        self._send(SERVICE_IMU, {
            'acel_x': data.get('acel_x'), 'acel_y': data.get('acel_y'), 'acel_z': data.get('acel_z'),
            'giro_x': data.get('giro_x'), 'giro_y': data.get('giro_y'), 'giro_z': data.get('giro_z'),
        })

    def send_lidar(self, data: dict):
        self._send(SERVICE_LIDAR, {
            'pontos': data.get('lidar_pontos'),
        })

    def send_adas(self, data: dict):
        self._send(SERVICE_ADAS, {
            'veiculo':   data.get('adas_veiculo'),
            'pedestre':  data.get('adas_pedestre'),
            'semaforo':  data.get('adas_semaforo'),
            'dist_m':    data.get('dist_frente_m'),
            'n_veic':    data.get('n_veiculos'),
            'n_ped':     data.get('n_pedestres'),
        })

    def send_all(self, data: dict):
        self.send_dynamics(data)
        self.send_gnss(data)
        self.send_imu(data)
        self.send_lidar(data)
        self.send_adas(data)

    def close(self):
        self._sock.close()
