"""
LiDARService — AUTOSAR AP LiDARService interface.

Service ID : 0x1004
Frequência : 10 Hz

Campos baseados em:
  AUTOSAR AP SWS SensorFusion — LiDARPointCloudInterface
  Simplificado: resumo do point cloud + objetos detectados com classe e distância
"""

from someip_network.services.base import SomeIPService
from someip_network import SERVICE_LIDAR


class LiDARService(SomeIPService):
    service_id = SERVICE_LIDAR

    def from_carla(self, data: dict) -> dict:
        return {
            'num_points':         data.get('lidar_pontos'),
            'nearest_obstacle_m': data.get('lidar_nearest_m'),   # menor distância no cone frontal
            'range_m':            50.0,                           # alcance configurado no sensor
            'detected_objects':   data.get('lidar_objects', []),  # lista de {class, distance_m, azimuth_deg}
        }

    def publish_from_carla(self, data: dict):
        self.publish(self.from_carla(data))
