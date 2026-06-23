"""
Roda no container ids_monitor.
Captura trafego SOME/IP UDP e registra para analise pelo IDS.
"""

import socket
import struct
import json
import time
import os
from datetime import datetime

from someip_network.packet import SomeIPPacket, HEADER_SIZE
from someip_network import (
    SERVICE_DYNAMICS, SERVICE_GNSS, SERVICE_IMU,
    SERVICE_LIDAR, SERVICE_ADAS,
)

MULTICAST_GROUP = '239.0.0.1'
MULTICAST_PORT  = 30490
LOG_DIR         = '/app/traffic_logs'

SERVICE_NAMES = {
    SERVICE_DYNAMICS: 'DYNAMICS',
    SERVICE_GNSS:     'GNSS',
    SERVICE_IMU:      'IMU',
    SERVICE_LIDAR:    'LIDAR',
    SERVICE_ADAS:     'ADAS',
}


def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    ts      = datetime.now().strftime('%Y%m%d_%H%M%S')
    logfile = os.path.join(LOG_DIR, f'someip_{ts}.jsonl')

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', MULTICAST_PORT))
    mreq = struct.pack('4sL', socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    print(f'[IDS] Monitorando SOME/IP UDP:{MULTICAST_PORT} → {logfile}')

    with open(logfile, 'w') as f:
        while True:
            raw, addr = sock.recvfrom(65535)
            ts_recv   = time.time()
            try:
                pkt = SomeIPPacket.decode(raw)
                svc = SERVICE_NAMES.get(pkt.service_id, f'0x{pkt.service_id:04X}')
                record = {
                    'ts':         ts_recv,
                    'src':        addr[0],
                    'service_id': pkt.service_id,
                    'method_id':  pkt.method_id,
                    'msg_type':   pkt.msg_type,
                    'session_id': pkt.session_id,
                    'payload_len': len(pkt.payload),
                    'service':    svc,
                    'label':      'normal',   # sera sobrescrito nos ataques
                }
                f.write(json.dumps(record) + '\n')
                f.flush()
            except Exception:
                pass


if __name__ == '__main__':
    main()
