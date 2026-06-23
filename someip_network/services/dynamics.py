"""
VehicleDynamicsService — AUTOSAR AP VehicleDynamics interface.

Service ID : 0x1001
Frequência : 50 Hz (todo tick a 50 Hz) / 20 Hz (todo tick a 20 Hz)

Campos baseados em:
  AUTOSAR AP SWS CommunicationManagement — VehicleSpeed, SteeringAngle, Powertrain signals
"""

from someip_network.services.base import SomeIPService
from someip_network import SERVICE_DYNAMICS


class VehicleDynamicsService(SomeIPService):
    service_id = SERVICE_DYNAMICS

    def from_carla(self, data: dict) -> dict:
        steer_norm = data.get('steering', 0.0)   # CARLA: -1..+1
        gear       = data.get('gear', 0)
        reverse    = data.get('marcha_re', False)

        return {
            'vehicle_speed_kmh':      data.get('velocidade_kmh'),
            'steering_angle_deg':     round(steer_norm * 540.0, 1),  # mapeado para graus reais
            'longitudinal_accel_ms2': data.get('acel_x'),
            'lateral_accel_ms2':      data.get('acel_y'),
            'throttle_pct':           round((data.get('throttle', 0.0)) * 100.0, 1),
            'brake_pct':              round((data.get('brake',    0.0)) * 100.0, 1),
            'gear':                   gear,
            'drive_mode':             'R' if reverse else ('N' if gear == 0 else 'D'),
        }

    def publish_from_carla(self, data: dict):
        self.publish(self.from_carla(data))
