"""
AEBService — AUTOSAR AP AEB / PerceptionService interface.

Service ID : 0x1005
Frequência : 25 Hz

Campos baseados em:
  AUTOSAR AP SWS ADAS — AEBServiceInterface
  ISO 22737 / ISO 15623 — forward collision warning e AEB state machine

Estados AEB (aeb_state):
  INACTIVE       — sem ameaça detectada
  MONITORING     — veículo à frente, TTC > 3.5 s
  PREFILL        — TTC 2.5–3.5 s, freio pré-pressurizado
  PARTIAL_BRAKE  — TTC 1.5–2.5 s, frenagem parcial ativa
  FULL_BRAKE     — TTC < 1.5 s, frenagem máxima autônoma
"""

from someip_network.services.base import SomeIPService
from someip_network import SERVICE_ADAS   # 0x1005 — mantido para compatibilidade

# Limiares de TTC (time-to-collision) em segundos — ISO 15623
_TTC_FULL_BRAKE    = 1.5
_TTC_PARTIAL_BRAKE = 2.5
_TTC_PREFILL       = 3.5
_TTC_MONITORING    = 5.0


def _aeb_state(ttc_s) -> str:
    if ttc_s is None:
        return 'INACTIVE'
    if ttc_s < _TTC_FULL_BRAKE:
        return 'FULL_BRAKE'
    if ttc_s < _TTC_PARTIAL_BRAKE:
        return 'PARTIAL_BRAKE'
    if ttc_s < _TTC_PREFILL:
        return 'PREFILL'
    if ttc_s < _TTC_MONITORING:
        return 'MONITORING'
    return 'INACTIVE'


class AEBService(SomeIPService):
    service_id = SERVICE_ADAS

    def from_carla(self, data: dict) -> dict:
        dist_m   = data.get('dist_frente_m')
        speed_ms = (data.get('velocidade_kmh') or 0.0) / 3.6

        # TTC simplificado: assume veículo à frente estacionário
        if dist_m is not None and speed_ms > 0.5:
            ttc_s = round(dist_m / speed_ms, 2)
        else:
            ttc_s = None

        state = _aeb_state(ttc_s)

        return {
            'aeb_state':               state,
            'ttc_s':                   ttc_s,
            'lead_vehicle_detected':   data.get('adas_veiculo', False),
            'lead_vehicle_distance_m': dist_m,
            'lead_vehicle_speed_kmh':  data.get('lead_speed_kmh'),      # None se indisponível
            'pedestrian_detected':     data.get('adas_pedestre', False),
            'pedestrian_distance_m':   data.get('dist_pedestre_m'),
            'traffic_light_detected':  data.get('adas_semaforo', False),
            'lane_departure_warning':  False,                            # sensor futuro
            'emergency_brake_active':  state == 'FULL_BRAKE',
        }

    def publish_from_carla(self, data: dict):
        self.publish(self.from_carla(data))
