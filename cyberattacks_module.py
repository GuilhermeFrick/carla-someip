#!/usr/bin/env python3
"""
Orquestra ataques SOME/IP via container Docker (attacker).

Analogo ao cyberattacks_module.py do yes-carla-can,
mas para ataques em rede SOME/IP ao inves de CAN bus.

Uso:
    python cyberattacks_module.py dos    --rate 500 --duration 30
    python cyberattacks_module.py fuzzy  --duration 30
    python cyberattacks_module.py replay --pcap traffic_logs/someip_normal_01.pcap
    python cyberattacks_module.py spoof  --duration 30 --speed 200.0
"""

import argparse
import subprocess
import sys


COMPOSE_FILE = 'docker/docker-compose.yml'
SERVICE      = 'attacker'


def _run_attack(attack_args: list[str]) -> int:
    cmd = [
        'docker', 'compose',
        '-f', COMPOSE_FILE,
        '--profile', 'attack',
        'run', '--rm', SERVICE,
        'python',
    ] + attack_args

    print(f'[ATAQUE] {" ".join(attack_args)}')
    proc = subprocess.run(cmd)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Orquestra ataques SOME/IP no container attacker.'
    )
    sub = parser.add_subparsers(dest='attack', required=True)

    # DoS
    p_dos = sub.add_parser('dos', help='Flood de notificacoes SOME/IP')
    p_dos.add_argument('--rate',     type=int,   default=500, help='Pacotes por segundo (padrao: 500)')
    p_dos.add_argument('--duration', type=float, default=30,  help='Duracao em segundos (padrao: 30)')

    # Fuzzy
    p_fuz = sub.add_parser('fuzzy', help='Pacotes com campos aleatorios')
    p_fuz.add_argument('--duration', type=float, default=30, help='Duracao em segundos (padrao: 30)')

    # Replay
    p_rep = sub.add_parser('replay', help='Reenvio de pacotes de uma captura anterior')
    p_rep.add_argument('--pcap', required=True, help='Arquivo PCAP a ser reproduzido')
    p_rep.add_argument('--loop', action='store_true', help='Repetir em loop')

    # Spoof
    p_sp = sub.add_parser('spoof', help='Injecao de dados ADAS falsos')
    p_sp.add_argument('--duration', type=float, default=30,    help='Duracao em segundos (padrao: 30)')
    p_sp.add_argument('--speed',    type=float, default=200.0, help='Velocidade falsa km/h (padrao: 200.0)')

    args = parser.parse_args()

    if args.attack == 'dos':
        return _run_attack([
            'attacks/dos.py',
            '--rate',     str(args.rate),
            '--duration', str(args.duration),
        ])

    if args.attack == 'fuzzy':
        return _run_attack([
            'attacks/fuzzy.py',
            '--duration', str(args.duration),
        ])

    if args.attack == 'replay':
        loop_flag = ['--loop'] if args.loop else []
        return _run_attack([
            'attacks/replay.py',
            '--pcap', args.pcap,
        ] + loop_flag)

    if args.attack == 'spoof':
        return _run_attack([
            'attacks/spoof.py',
            '--duration', str(args.duration),
            '--speed',    str(args.speed),
        ])

    return 1


if __name__ == '__main__':
    raise SystemExit(main())
