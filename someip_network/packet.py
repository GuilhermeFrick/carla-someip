"""
SOME/IP packet encoder/decoder.

Header format (16 bytes):
 0       1       2       3
 Service ID      Method ID
 Length (payload + 8)
 Client ID       Session ID
 Proto   Iface   Msg Type  Return Code
"""

import struct
import json


HEADER_FMT  = '>HHIHHBBBB'
HEADER_SIZE = 16


class SomeIPPacket:
    def __init__(self, service_id, method_id, payload=b'',
                 client_id=0x0001, session_id=0x0001,
                 proto=0x01, iface=0x01,
                 msg_type=0x02, return_code=0x00):
        self.service_id  = service_id
        self.method_id   = method_id
        self.payload     = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.client_id   = client_id
        self.session_id  = session_id
        self.proto       = proto
        self.iface       = iface
        self.msg_type    = msg_type
        self.return_code = return_code

    def encode(self) -> bytes:
        length = 8 + len(self.payload)
        header = struct.pack(
            HEADER_FMT,
            self.service_id,
            self.method_id,
            length,
            self.client_id,
            self.session_id,
            self.proto,
            self.iface,
            self.msg_type,
            self.return_code,
        )
        return header + self.payload

    @staticmethod
    def decode(raw: bytes) -> 'SomeIPPacket':
        if len(raw) < HEADER_SIZE:
            raise ValueError(f'Packet too short: {len(raw)} bytes')
        fields = struct.unpack(HEADER_FMT, raw[:HEADER_SIZE])
        payload = raw[HEADER_SIZE:]
        return SomeIPPacket(
            service_id  = fields[0],
            method_id   = fields[1],
            client_id   = fields[4],
            session_id  = fields[5],
            proto       = fields[6],
            iface       = fields[7],
            msg_type    = fields[8],
            return_code = fields[9],
            payload     = payload,
        )

    def payload_json(self) -> dict:
        return json.loads(self.payload.decode())

    def __repr__(self):
        return (f'SomeIPPacket(svc=0x{self.service_id:04X} '
                f'meth=0x{self.method_id:04X} '
                f'type=0x{self.msg_type:02X} '
                f'len={len(self.payload)}B)')
