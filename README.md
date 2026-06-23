# carla-someip

**SOME/IP IDS Dataset Generator** — extensão do [yes-carla-can](https://github.com/luigiluz/yes-carla-can) para o protocolo SOME/IP.

Plataforma open-source que conecta o simulador CARLA a uma rede SOME/IP virtualizada em containers Docker, gerando datasets rotulados para pesquisa de Intrusion Detection Systems em redes veiculares modernas.

## Arquitetura

```
Windows
├── CARLA 0.9.15 (simulador)
└── bridge_sender.py ──TCP:5000──►┐
                                   │
Docker (someip-net)                │
├── ecu_bridge    ◄────────────────┘  SOME/IP publisher
├── ids_monitor                        captura PCAP + IDS
└── attacker      (profile: attack)    DoS / Fuzzy / Replay / Spoof
```

## Serviços SOME/IP

| Service ID | Serviço       | Frequência |
|------------|---------------|-----------|
| `0x1001`   | Dinâmica      | 50 Hz     |
| `0x1002`   | GNSS          | 5 Hz      |
| `0x1003`   | IMU           | 50 Hz     |
| `0x1004`   | LiDAR         | 10 Hz     |
| `0x1005`   | ADAS          | 25 Hz     |

## Módulos de Ataque

| Ataque  | Descrição                                      |
|---------|------------------------------------------------|
| DoS     | Flood de notificações acima da frequência      |
| Fuzzy   | Service ID / Method ID / payload aleatórios    |
| Replay  | Reenvio de pacotes capturados anteriormente    |
| Spoof   | Injeção de dados ADAS falsos                   |

## Como rodar

### 1. Iniciar CARLA (Windows)
```powershell
F:\Mestrado\CARLA\WindowsNoEditor\CarlaUE4.exe -quality-level=Low -dx11
```

### 2. Subir containers
```bash
docker compose -f docker/docker-compose.yml up
```

### 3. Rodar simulação (Windows)
```powershell
cd F:\Mestrado\CARLA\carla-someip
F:\Mestrado\CARLA\venv37\Scripts\python.exe carla_client.py
```

### 4. Gerar trafego de ataque
```bash
docker compose -f docker/docker-compose.yml --profile attack run attacker \
  python attacks/dos.py --rate 500 --duration 30
```

## Baseline

Este projeto usa [yes-carla-can](https://github.com/luigiluz/yes-carla-can) (SBRC 2026) como referência arquitetural,
estendendo o protocolo de CAN bus para SOME/IP e o IDS de Isolation Forest para XGBoost com features comportamentais.

## Referências

- Luo et al. (2023) — dataset de referência (Prescan + CANoe)
- Kim et al. (2026) — dataset SOME/IP público (figshare)
- yes-carla-can — CARLA + CAN bus (SBRC 2026, UFPE)
