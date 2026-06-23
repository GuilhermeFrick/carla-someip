#!/usr/bin/env python3
"""
Coleta logs de trafego SOME/IP via tcpdump no container ids_monitor.

Analogo ao collect_traffic_logs.py do yes-carla-can (candump),
mas para SOME/IP UDP multicast em ambiente Docker.

Uso:
    python collect_traffic_logs.py --duration 180 --output traffic_logs/normal_01.pcap
    python collect_traffic_logs.py --duration 60  --output traffic_logs/dos_01.pcap --label dos
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


CONTAINER    = 'ids_monitor'
IFACE        = 'eth0'
CAPTURE_PORT = 30490    # SOME/IP UDP


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Coleta trafego SOME/IP via tcpdump no container ids_monitor.'
    )
    parser.add_argument('-d', '--duration', type=float, required=True,
                        help='Tempo de coleta em segundos.')
    parser.add_argument('-o', '--output',   default=None,
                        help='Arquivo PCAP de saida (padrao: traffic_logs/someip_<ts>.pcap).')
    parser.add_argument('--label',          default='normal',
                        choices=['normal', 'dos', 'fuzzy', 'replay', 'spoof'],
                        help='Rotulo do trafego capturado (salvo no nome do arquivo).')
    parser.add_argument('--container',      default=CONTAINER,
                        help=f'Nome do container Docker (padrao: {CONTAINER}).')
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.duration <= 0:
        print('Erro: duration deve ser maior que 0.', file=sys.stderr)
        return 1

    logs_dir = Path('traffic_logs')
    logs_dir.mkdir(parents=True, exist_ok=True)

    if args.output:
        out_path = Path(args.output)
    else:
        ts       = time.strftime('%Y%m%d_%H%M%S')
        out_path = logs_dir / f'someip_{args.label}_{ts}.pcap'

    container_pcap = f'/app/traffic_logs/{out_path.name}'

    cmd = [
        'docker', 'exec', args.container,
        'tcpdump', '-i', IFACE,
        f'udp port {CAPTURE_PORT}',
        '-w', container_pcap,
    ]

    print(f"Capturando SOME/IP UDP:{CAPTURE_PORT} por {args.duration}s → {out_path}")
    print(f"Label: {args.label}")

    proc = subprocess.Popen(cmd)
    try:
        proc.wait(timeout=args.duration)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait()
        print('Coleta interrompida pelo usuario.')
        return 130

    # copia o pcap do container para o host
    cp_cmd = ['docker', 'cp', f'{args.container}:{container_pcap}', str(out_path)]
    subprocess.run(cp_cmd, check=True)

    print(f'Coleta concluida → {out_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
