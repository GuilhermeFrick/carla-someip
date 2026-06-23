"""
SomeIPNetwork — orquestrador dos serviços SOME/IP.

Análogo ao CAN_Network do yes-carla-can, mas orientado a serviços AUTOSAR AP.
Cada serviço tem sua própria classe em someip_network/services/.

Frequências configuradas (base: 20 Hz de simulação):
  dynamics : todo tick  → 20 Hz
  gnss     : a cada 4   →  5 Hz
  imu      : todo tick  → 20 Hz
  lidar    : a cada 2   → 10 Hz
  aeb      : todo tick  → 20 Hz (segurança crítica)
"""

from someip_network.services import (
    VehicleDynamicsService,
    GNSSService,
    IMUService,
    LiDARService,
    AEBService,
)

MULTICAST_GROUP = '239.0.0.1'
MULTICAST_PORT  = 30490

_FREQ = {
    'dynamics': 1,
    'gnss':     4,
    'imu':      1,
    'lidar':    2,
    'aeb':      1,
}


class SomeIPNetwork:
    def __init__(self):
        self.dynamics = VehicleDynamicsService()
        self.gnss     = GNSSService()
        self.imu      = IMUService()
        self.lidar    = LiDARService()
        self.aeb      = AEBService()
        self._tick    = 0

    def publish_tick(self, data: dict):
        """Publica todos os serviços conforme suas frequências configuradas."""
        self._tick += 1
        if self._tick % _FREQ['dynamics'] == 0:
            self.dynamics.publish_from_carla(data)
        if self._tick % _FREQ['gnss'] == 0:
            self.gnss.publish_from_carla(data)
        if self._tick % _FREQ['imu'] == 0:
            self.imu.publish_from_carla(data)
        if self._tick % _FREQ['lidar'] == 0:
            self.lidar.publish_from_carla(data)
        if self._tick % _FREQ['aeb'] == 0:
            self.aeb.publish_from_carla(data)

    def close(self):
        for svc in [self.dynamics, self.gnss, self.imu, self.lidar, self.aeb]:
            svc.close()
