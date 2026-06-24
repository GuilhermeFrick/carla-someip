# Relatório de Implementação — carla-someip

**Projeto:** Geração de Dataset SOME/IP para IDS em Veículos Autônomos  
**Repositório:** github.com/GuilhermeFrick/carla-someip  
**Status atual:** Funcional em Windows (CARLA + HUD + bridge SOME/IP)  
**Última atualização:** 2026-06-24

---

## 1. Trabalho de Referência: yes-carla-can

A implementação foi inspirada no trabalho **"YeS-CARLA-CAN: Yet another Synthetic CARLA CAN Dataset"** (Püllen et al.), que propôs uma metodologia para geração de datasets sintéticos de rede veicular usando o simulador CARLA com protocolo CAN Bus.

### O que yes-carla-can fez

| Componente | Implementação |
|---|---|
| Simulador | CARLA 0.9.x |
| Protocolo de rede | CAN Bus |
| Sensores | Velocidade, aceleração, controle |
| Ataque | Replay attack e spoofing de mensagens CAN |
| IDS | Dois detectores: `id_time` (análise estatística de timing) e `ml` (Isolation Forest) |
| Dataset | Captura de tráfego CAN com labels normal/ataque |
| Estrutura | `can_network/`, `defense/ids_training/`, módulo de ataque |

O projeto fornecia um pipeline fechado: CARLA → CAN bus simulado → IDS. O foco era CAN, protocolo típico de veículos legados (pré-2020).

---

## 2. Nossa Contribuição: carla-someip

Substituímos o CAN Bus por **SOME/IP (Scalable service-Oriented MiddlewarE over IP)**, protocolo da norma AUTOSAR Adaptive Platform, usado em veículos modernos com Ethernet veicular (ADAS, sensores de alto throughput, sistemas autônomos). A mudança é motivada pela relevância crescente do SOME/IP em ataques a sistemas automotivos conectados.

### Diferenças fundamentais em relação ao yes-carla-can

| Aspecto | yes-carla-can | carla-someip (este projeto) |
|---|---|---|
| Protocolo | CAN Bus (ISO 11898) | SOME/IP / UDP Multicast (AUTOSAR AP) |
| Endereçamento | ID de mensagem CAN (11 bits) | Service ID + Method ID (16 bits cada) |
| Transporte | Barramento serial | UDP Multicast `239.0.0.1:30490` |
| Sensores | Velocidade, steering | GNSS, IMU, LiDAR HDL-32E, Dynamics, AEB |
| Serviços AUTOSAR | Não | 5 serviços (0x1001–0x1005) |
| ADAS ground truth | Não | Sim (veículos/pedestres/semáforos) |
| Visualização | Não | HUD pygame 1280×660 + LiDAR top-down |
| Classificador IDS | Isolation Forest | XGBoost com features comportamentais |
| Ataque | CAN spoofing | AEB spoofing (suppress + inject) |
| Containerização | Não | Docker Compose multi-serviço |

---

## 3. Como funciona a API do CARLA

### 3.1 Arquitetura cliente-servidor

O CARLA opera em modelo cliente-servidor. O servidor é o processo UE4 (renderização, física, simulação de atores). O cliente é qualquer processo Python que se conecta via TCP:

```
┌─────────────────────────────────┐        ┌──────────────────────┐
│   CARLA Server (UE4)            │        │   carla_client.py    │
│                                 │        │                      │
│   World · Map · Actors          │◄──────►│   carla.Client()     │
│   Physics · Weather             │  TCP   │   world.tick()       │
│   Sensor rendering              │ :2000  │   actor.get_*()      │
│                                 │        │   sensor.listen()    │
└─────────────────────────────────┘        └──────────────────────┘
         :2000  servidor principal
         :2001  tráfego de sensores (streaming)
         :2002  Traffic Manager
```

### 3.2 Modo síncrono vs assíncrono

**Assíncrono (padrão):** servidor avança em tempo real, cliente lê o estado mais recente disponível. Dados de sensores podem chegar fora de ordem.

**Síncrono (nosso projeto):** o servidor só avança quando o cliente chama `world.tick()`. Garante que cada frame de sensor corresponda exatamente ao estado do mundo naquele tick — essencial para consistência do dataset:

```python
settings = world.get_settings()
settings.synchronous_mode    = True
settings.fixed_delta_seconds = 1.0 / 20   # 20 Hz fixo
world.apply_settings(settings)

world.tick()   # avança exatamente 50ms
dados = _ler_telemetria(...)
```

### 3.3 Blueprint Library — sistema de atores

Todo ator no CARLA (veículo, sensor, pedestre) é instanciado a partir de um blueprint:

```python
lib = world.get_blueprint_library()

# Veículo
bp = lib.find('vehicle.tesla.model3')
bp.set_attribute('color', '255,0,0')
veiculo = world.spawn_actor(bp, spawn_point)

# Sensor — sempre attached a um ator pai
bp_lidar = lib.find('sensor.lidar.ray_cast')
bp_lidar.set_attribute('channels', '32')
lidar = world.spawn_actor(bp_lidar,
            carla.Transform(carla.Location(z=2.5)),
            attach_to=veiculo)
```

### 3.4 Sistema de sensores e callbacks

Sensores no CARLA funcionam por callback assíncrono. O callback roda em thread separada e o buffer de dados é liberado após o retorno — por isso a cópia imediata é obrigatória:

```python
def _on_lidar(data):
    # CRÍTICO: copiar antes de sair do callback
    pts = np.frombuffer(data.raw_data, dtype=np.float32).copy()
    pts = pts.reshape((-1, 4))   # [x, y, z, intensity]

lidar.listen(_on_lidar)
```

**Sensores disponíveis relevantes para ADAS:**

| Sensor | Blueprint | Dados |
|---|---|---|
| LiDAR ray cast | `sensor.lidar.ray_cast` | Nuvem de pontos XYZ + intensidade |
| GNSS | `sensor.other.gnss` | Latitude, longitude, altitude |
| IMU | `sensor.other.imu` | Aceleração 3D, giroscópio 3D |
| Câmera RGB | `sensor.camera.rgb` | Frame RGBA 32-bit |
| Radar | `sensor.other.radar` | Pontos com velocidade radial |
| Collision | `sensor.other.collision` | Evento de colisão + impulso |

### 3.5 Traffic Manager

Componente interno do CARLA que controla NPCs em autopilot. Opera na porta `:2002`:

```python
tm = client.get_trafficmanager()
tm.set_synchronous_mode(True)           # obrigatório em modo síncrono
tm.set_global_distance_to_leading_vehicle(2.0)
npc.set_autopilot(True, tm.get_port())
```

### 3.6 Ground Truth via API

A API Python expõe o estado completo do mundo sem custo de rendering. Usamos isso para ADAS ground truth (posição, distância, classificação de atores):

```python
for ator in world.get_actors().filter('vehicle.*'):
    loc  = ator.get_location()
    dist = ego_loc.distance(loc)
    bb   = ator.bounding_box
```

Isso representa o que um sensor perfeito enxergaria. Com Autoware, substituímos por percepção real baseada em LiDAR.

### 3.7 Debug Drawing (UE4 viewport)

Desenha geometria diretamente no viewport do UE4 sem sensor adicional:

```python
world.debug.draw_box(
    carla.BoundingBox(location, extent), rotation,
    thickness=0.08,
    color=carla.Color(0, 255, 0),
    life_time=max(0.12, 2.0/fps)
)
world.debug.draw_string(location, "19.7m", color=carla.Color(255,255,0))
```

---

## 4. Arquitetura do Sistema — Estado Atual

```
╔══════════════════════════════════════════════════════════════╗
║                    WINDOWS (Máquina local)                   ║
║                                                              ║
║  ┌─────────────────────────────────────────────────────┐    ║
║  │              CARLA 0.9.15 (UE4)                     │    ║
║  │   Tesla Model3 ego  ·  30 NPCs  ·  Town10HD_Opt     │    ║
║  │   LiDAR HDL-32E  ·  GNSS  ·  IMU                   │    ║
║  └──────────────────────┬──────────────────────────────┘    ║
║                          │ Python API  TCP :2000             ║
║  ┌──────────────────────▼──────────────────────────────┐    ║
║  │              carla_client.py                        │    ║
║  │  ┌──────────────────┐  ┌──────────────────────────┐ │    ║
║  │  │  HUD pygame      │  │  ADAS Ground Truth        │ │    ║
║  │  │  1280×660        │  │  (veíc / ped / semáf)     │ │    ║
║  │  │  LiDAR top-down  │  │  raio 50 m                │ │    ║
║  │  │  velocímetro     │  │  TTC → AEB state          │ │    ║
║  │  └──────────────────┘  └──────────────────────────┘ │    ║
║  └──────────────────────┬──────────────────────────────┘    ║
║                          │ TCP JSON lines  :5000             ║
║  ┌──────────────────────▼──────────────────────────────┐    ║
║  │              ecu_bridge  (SOME/IP publisher)         │    ║
║  │  0x1001 VehicleDynamics  20 Hz                      │    ║
║  │  0x1002 GNSS              5 Hz                      │    ║
║  │  0x1003 IMU              20 Hz                      │    ║
║  │  0x1004 LiDAR            10 Hz                      │    ║
║  │  0x1005 AEB              20 Hz                      │    ║
║  └──────────────────────┬──────────────────────────────┘    ║
║                          │ UDP Multicast 239.0.0.1:30490     ║
║           ┌──────────────┼───────────────────┐              ║
║  ┌────────▼──────┐  ┌────▼──────────────┐                   ║
║  │ ids_monitor   │  │ attacker          │                   ║
║  │ .jsonl logs   │  │ spoof.py          │                   ║
║  └────────┬──────┘  │ suppress / inject │                   ║
║           │         └───────────────────┘                   ║
║  ┌────────▼──────┐                                          ║
║  │ XGBoost IDS   │  (dataset ainda não coletado)            ║
║  │ training      │                                          ║
║  └───────────────┘                                          ║
╚══════════════════════════════════════════════════════════════╝
```

**Limitação atual:** o fluxo é unidirecional. O ataque injeta pacotes SOME/IP, mas nenhum componente age sobre eles para controlar o veículo. O loop está aberto — serve para geração de dataset, não para demonstração de impacto físico.

---

## 5. Protocolo SOME/IP

### 5.1 Packet format implementado

```
Offset  Tamanho  Campo
  0        2     Service ID
  2        2     Method ID
  4        4     Length (payload + 8)
  8        2     Client ID
 10        2     Session ID
 12        1     Protocol Version (0x01)
 13        1     Interface Version (0x01)
 14        1     Message Type (0x02 = NOTIFICATION)
 15        1     Return Code (0x00 = OK)
 16+       N     Payload (JSON)
```

### 5.2 Serviços implementados (AUTOSAR AP SWS)

| Service ID | Nome | Frequência | Conteúdo principal |
|---|---|---|---|
| `0x1001` | VehicleDynamicsService | 20 Hz | velocidade, steering_deg, throttle_pct, brake_pct, gear, drive_mode |
| `0x1002` | GNSSService | 5 Hz | latitude, longitude, altitude, heading_deg |
| `0x1003` | IMUService | 20 Hz | acel_xyz (m/s²), gyro_xyz (rad/s) |
| `0x1004` | LiDARService | 10 Hz | n_points, nearest_m, objects list (class, distance, azimuth) |
| `0x1005` | AEBService | 20 Hz | aeb_state, ttc_s, lead_vehicle_detected, emergency_brake_active |

### 5.3 AEB State Machine (ISO 15623)

```
TTC > 5.0s  →  INACTIVE
TTC < 5.0s  →  MONITORING
TTC < 3.5s  →  PREFILL        (freio pré-pressurizado)
TTC < 2.5s  →  PARTIAL_BRAKE  (frenagem parcial)
TTC < 1.5s  →  FULL_BRAKE     (frenagem máxima autônoma)
```

---

## 6. Sensores Implementados

### 6.1 LiDAR Velodyne HDL-32E

| Parâmetro | Valor |
|---|---|
| Canais | 32 |
| Points/segundo | 700.000 |
| Alcance | 120 m |
| FOV vertical | −30° a +10° |
| Frequência rotação | 10 Hz |
| Noise stddev | 0,02 m |
| Dropoff geral | 45% |

**Bug crítico resolvido:** buffer `raw_data` liberado após callback. Solução: `.copy()` imediato dentro do callback.

### 6.2 GNSS
Sensor nativo CARLA → latitude, longitude, altitude a 5 Hz.

### 6.3 IMU
Acelerômetro + giroscópio em 3 eixos a 20 Hz.

### 6.4 ADAS Ground Truth
Função `_adas_ground_truth()` usa API Python do CARLA diretamente — sem sensor adicional, sem custo de rendering. Detecta veículos/pedestres no cone frontal (raio 50 m) e semáforos (raio 30 m), calculando distância mínima e azimute.

---

## 7. Visualização (HUD pygame)

Dashboard 1280×660 com dois painéis:

**Esquerdo (640px) — Telemetria:**
- Radar ADAS top-down (50 m)
- Badges de detecção: VEICULO / PEDESTRE / SEMAFORO
- Velocímetro analógico (verde→amarelo→vermelho)
- Volante com ângulo de steering
- Barras de throttle e brake
- Dados IMU em tempo real
- Posição GNSS
- Indicador SOME/IP bridge status

**Direito (640px) — LiDAR top-down:**
- Nuvem de pontos 2D vista de cima
- Coloração por altura z via HSV rainbow: azul=chão, ciano=médio, vermelho=alto
- Circunferências de referência: 20, 40, 60, 80, 100, 120 m
- Escala: 4 px/metro, subsampling para 3.000 pts/frame

---

## 8. Módulo de Ataque

### `attacks/spoof.py` — AEB Spoofing

Dois modos baseados em cenários reais de segurança ADAS:

**Modo `suppress` (Falso Negativo):**
- Contexto: veículo à frente real
- Ataque: reporta `INACTIVE` + `lead_vehicle_detected=False`
- Efeito esperado (com loop fechado): AEB não dispara → colisão potencial

**Modo `inject` (Falso Positivo — Phantom Braking):**
- Contexto: via livre
- Ataque: reporta `FULL_BRAKE` + `lead_vehicle_distance=5m`
- Efeito esperado (com loop fechado): freio de emergência espúrio

O atacante injeta pacotes SOME/IP no multicast `239.0.0.1:30490` com Service ID `0x1005` a 25 Hz, sobrepondo os pacotes legítimos do ecu_bridge.

---

## 9. IDS — Detecção de Intrusão

### `defense/ids_training/train.py` — XGBoost

Diferentemente do yes-carla-can (Isolation Forest não supervisionado), usamos **XGBoost supervisionado** com labels do dataset coletado.

**Features comportamentais por janela temporal de 1s:**

| Feature | Descrição |
|---|---|
| `tx_rate` | Pacotes/segundo por serviço |
| `inter_arrival_mean` | Intervalo médio entre pacotes |
| `inter_arrival_std` | Desvio padrão do inter-arrival |
| `payload_len_mean` | Tamanho médio do payload |
| `payload_len_std` | Variância do tamanho |
| `unique_sessions` | Sessões únicas no intervalo |
| `service_entropy` | Entropia da distribuição de serviços |

**Pipeline:** split temporal 80/20 → XGBoost 300 estimators, max_depth=6 → `classification_report` → modelo salvo com `joblib`.

---

## 10. Histórico de Commits

| Commit | Descrição |
|---|---|
| `30832af` | Estrutura base do projeto |
| `c050b56` | CARLA client, HUD, IDS — espelhando yes-carla-can |
| `84c5ca1` | Refactor: serviços SOME/IP por classe (padrão AUTOSAR AP) |
| `70a925a` | Revert: remove camera sensor (crash CARLA 0.9.15 Windows) |
| `7400ef1` | Visualização LiDAR top-down no HUD (sem camera) |
| `81768e0` | Fix: cópia buffer LiDAR no callback (access violation) |
| `de26889` | Bounding boxes 3D no UE4 (veículos, pedestres, ego) |
| `69db9c1` | Fix: debug boxes sem transform() inválido |
| `e38021b` | LiDAR HDL-32E: 700k pts, 120m, FOV −30/+10 |
| `bc024b6` | Ruído realista HDL-32E: dropoff + noise_stddev |
| `0b62773` | Modo headless + script setup_runpod.sh |
| `d80f6e2` | Fix Python 3.7: `Optional[socket]` compatível |
| `2df131c` | Arquitetura 100% Docker (refactor completo) |
| `1b8410d` | Atualiza CARLA para 0.9.16 |

---

## 11. Status Atual

### Funcional (Windows)
- CARLA 0.9.15 + Tesla Model3 + 30 NPCs em autopilot
- LiDAR HDL-32E com visualização top-down rainbow
- Bounding boxes 3D no viewport UE4
- GNSS + IMU a 5 Hz / 20 Hz
- ADAS ground truth (veículos, pedestres, semáforos)
- Bridge TCP → SOME/IP publicando 5 serviços
- HUD pygame 1280×660 em tempo real
- Módulo de ataque AEB spoofing (suppress + inject)
- Docker Compose configurado (pendente servidor GPU)

### Pendente
- Servidor cloud (DigitalOcean GPU Droplet em avaliação)
- Label de ataque no `ids_monitor.py`
- Coleta de dataset com sessões normal + ataque
- Treinamento do XGBoost IDS
- **Fechar o loop AEB** (próximo passo imediato)
- Conversão JSONL → CSV

---

## 12. Próximo Passo — Fluxo Bidirecional SOME/IP + Autoware

### 12.1 Por que o loop precisa ser fechado

Atualmente o ataque existe na rede mas não produz consequência física. Em um veículo real, o ECU de freio escuta o serviço AEB e age sobre ele. Na simulação, esse papel é do `carla_client.py` — que ainda não subscreve SOME/IP.

### 12.2 Arquitetura alvo (bidirecional)

```
┌─────────────────────────────────────────────────────────────────┐
│                      SENTIDO 1 — Sensores                       │
│                                                                 │
│  CARLA ──► carla_client ──► ecu_bridge ──► SOME/IP multicast   │
│                                                ↑                │
│                                          attacker               │
│                                          injeta dados           │
│                                          de sensor falsos       │
│                                                ↓                │
│                                    someip_ros2_gateway          │
│                                    (novo componente)            │
│                                                ↓                │
│                                          ROS2 topics            │
│                                    /sensing/lidar/objects       │
│                                    /sensing/gnss/fix            │
│                                    /sensing/imu/data            │
│                                                ↓                │
│                                         AUTOWARE                │
│                                    Perception → Planning        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      SENTIDO 2 — Controle                       │
│                                                                 │
│                         AUTOWARE                                │
│                    Control → /control/command                   │
│                                    ↓                            │
│                              ros2_someip_gateway                │
│                              publica 0x1005 AEB                 │
│                                    ↓                            │
│                              SOME/IP multicast                  │
│                                    ↓                            │
│                         carla_client subscriber                 │
│                         aplica VehicleControl no CARLA          │
│                                    ↓                            │
│                              CARLA executa                      │
└─────────────────────────────────────────────────────────────────┘
```

### 12.3 Novos componentes

| Componente | Função |
|---|---|
| `someip_ros2_gateway.py` | Escuta SOME/IP → publica ROS2 topics para o Autoware |
| `ros2_someip_gateway.py` | Escuta `/control/command` ROS2 → publica SOME/IP 0x1005 |
| Subscriber AEB em `carla_client.py` | Escuta 0x1005 → aplica `VehicleControl` no CARLA |

### 12.4 Cenários de ataque demonstráveis com loop fechado

**Cenário 1 — Supressão de obstáculo:**
```
Situação real: veículo à frente a 12m
Ataque: spoof injeta LiDAR sem objetos + AEB INACTIVE
Efeito: Autoware não freia → colisão registrada no CARLA
```

**Cenário 2 — Obstáculo fantasma (Phantom Braking):**
```
Situação real: pista livre
Ataque: spoof injeta objeto a 5m no LiDAR
Efeito: Autoware freia bruscamente → risco de colisão traseira
```

**Cenário 3 — GNSS spoofing:**
```
Situação real: ego na faixa correta
Ataque: spoof injeta coordenadas deslocadas
Efeito: Autoware replaneja rota → ego invade faixa contrária
```

### 12.5 Valor para o IDS

Com o fluxo bidirecional e Autoware integrado, o dataset coletado terá:
- Tráfego SOME/IP com timing realista (variabilidade de percepção real)
- Padrões de ataque com consequência física verificável no simulador
- Labels precisos: ecu_bridge = `normal`, spoof.py = `attack`

O XGBoost treinado nesse dataset será capaz de distinguir tráfego legítimo de sensor de tráfego de ataque — que é a **contribuição central da tese**.
