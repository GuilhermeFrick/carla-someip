"""
GNSSService — AUTOSAR AP PositioningService interface.

Service ID : 0x1002
Frequência : 5 Hz

Campos baseados em:
  AUTOSAR AP SWS Positioning — GNSSDataInterface (latitude, longitude, altitude, heading)
  NMEA GGA / RMC sentence fields mapeados para AUTOSAR
"""

from someip_network.services.base import SomeIPService
from someip_network import SERVICE_GNSS


class GNSSService(SomeIPService):
    service_id = SERVICE_GNSS

    def from_carla(self, data: dict) -> dict:
        return {
            'latitude_deg':          data.get('latitude'),
            'longitude_deg':         data.get('longitude'),
            'altitude_m':            data.get('altitude'),
            'heading_deg':           data.get('heading_deg'),         # 0–360, norte = 0
            'speed_over_ground_kmh': data.get('velocidade_kmh'),
            'hdop':                  data.get('hdop', 1.0),           # dilution of precision
            'fix_quality':           1,                               # 1 = GPS fix
            'satellites_used':       data.get('satellites_used', 8),
        }

    def publish_from_carla(self, data: dict):
        self.publish(self.from_carla(data))
