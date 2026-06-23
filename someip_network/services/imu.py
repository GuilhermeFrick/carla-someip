"""
IMUService — AUTOSAR AP InertialSensorService interface.

Service ID : 0x1003
Frequência : 50 Hz

Campos baseados em:
  AUTOSAR AP SWS SensorFusion — IMU6DOF (accelerometer + gyroscope)
  + orientação (roll/pitch/yaw) derivada do IMU ou do ground truth CARLA
"""

from someip_network.services.base import SomeIPService
from someip_network import SERVICE_IMU


class IMUService(SomeIPService):
    service_id = SERVICE_IMU

    def from_carla(self, data: dict) -> dict:
        return {
            'accel_x_ms2': data.get('acel_x'),   # eixo longitudinal (frente/trás)
            'accel_y_ms2': data.get('acel_y'),   # eixo lateral (esq/dir)
            'accel_z_ms2': data.get('acel_z'),   # eixo vertical
            'gyro_x_rads': data.get('giro_x'),   # roll rate
            'gyro_y_rads': data.get('giro_y'),   # pitch rate
            'gyro_z_rads': data.get('giro_z'),   # yaw rate
            'roll_deg':    data.get('roll_deg'),
            'pitch_deg':   data.get('pitch_deg'),
            'yaw_deg':     data.get('yaw_deg'),
        }

    def publish_from_carla(self, data: dict):
        self.publish(self.from_carla(data))
