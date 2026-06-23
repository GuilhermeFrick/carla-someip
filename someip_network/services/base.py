"""
SomeIPService — classe base para todos os serviços SOME/IP.

Padrão AUTOSAR Adaptive ara::com:
  - publish()   → skeleton side (servidor envia notificação)
  - subscribe()  → proxy side   (cliente recebe notificação)
"""

import socket
import struct
import threading

from someip_network.packet import SomeIPPacket
from someip_network import METHOD_NOTIFY

MULTICAST_GROUP = '239.0.0.1'
MULTICAST_PORT  = 30490


class SomeIPService:
    service_id: int = 0x0000  # sobrescrito pela subclasse
    method_id:  int = METHOD_NOTIFY

    def __init__(self, multicast_group: str = MULTICAST_GROUP, port: int = MULTICAST_PORT):
        self._group   = multicast_group
        self._port    = port
        self._session = 0
        self._lock    = threading.Lock()
        self._sock    = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

    # ── Skeleton (publisher) ──────────────────────────────────────────────────

    def _next_session(self) -> int:
        with self._lock:
            self._session = (self._session % 0xFFFF) + 1
            return self._session

    def publish(self, payload: dict):
        pkt = SomeIPPacket(
            service_id=self.service_id,
            method_id=self.method_id,
            session_id=self._next_session(),
            payload=payload,
        )
        self._sock.sendto(pkt.encode(), (self._group, self._port))

    # ── Proxy (subscriber) ────────────────────────────────────────────────────

    def subscribe(self, callback, stop_event: threading.Event = None) -> threading.Thread:
        """Inicia thread que recebe notificações deste serviço e chama callback(payload_dict)."""
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        recv_sock.bind(('', self._port))
        mreq = struct.pack('4sL', socket.inet_aton(self._group), socket.INADDR_ANY)
        recv_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        recv_sock.settimeout(1.0)

        svc_id = self.service_id

        def _listen():
            while stop_event is None or not stop_event.is_set():
                try:
                    raw, _ = recv_sock.recvfrom(65535)
                    pkt = SomeIPPacket.decode(raw)
                    if pkt.service_id == svc_id:
                        callback(pkt.payload_json())
                except socket.timeout:
                    continue
                except Exception:
                    pass
            recv_sock.close()

        t = threading.Thread(target=_listen, daemon=True, name=f'sub-0x{svc_id:04X}')
        t.start()
        return t

    def close(self):
        self._sock.close()
