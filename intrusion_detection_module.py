#!/usr/bin/env python3
"""
Modulo de deteccao de intrusao SOME/IP (XGBoost).

Analogo ao intrusion_detection_module.py do yes-carla-can (Isolation Forest),
mas usando XGBoost com features comportamentais temporais.

Uso:
    # Treinar modelo
    python intrusion_detection_module.py train --data traffic_logs/someip_labeled.csv

    # Avaliar em PCAP
    python intrusion_detection_module.py eval  --pcap traffic_logs/someip_dos_01.pcap

    # Monitoramento em tempo real (requer container ids_monitor rodando)
    python intrusion_detection_module.py live  --model defense/models/xgb_someip.pkl
"""

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description='IDS SOME/IP baseado em XGBoost com features comportamentais.'
    )
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_train = sub.add_parser('train', help='Treinar modelo XGBoost')
    p_train.add_argument('--data',  required=True, help='CSV com trafego rotulado')
    p_train.add_argument('--model', default='defense/models/xgb_someip.pkl',
                         help='Caminho de saida do modelo')

    p_eval = sub.add_parser('eval', help='Avaliar modelo em arquivo PCAP')
    p_eval.add_argument('--pcap',  required=True, help='Arquivo PCAP a avaliar')
    p_eval.add_argument('--model', default='defense/models/xgb_someip.pkl')

    p_live = sub.add_parser('live', help='Monitoramento em tempo real')
    p_live.add_argument('--model', default='defense/models/xgb_someip.pkl')
    p_live.add_argument('--log',   default='traffic_logs/',
                        help='Diretorio com logs JSONL do ids_monitor')

    args = parser.parse_args()

    # importa so quando necessario para nao exigir dependencias no ambiente CARLA
    if args.cmd == 'train':
        from defense.ids_training.train import train
        train(args.data, args.model)

    elif args.cmd == 'eval':
        from defense.ids_eval import eval_pcap
        eval_pcap(args.pcap, args.model)

    elif args.cmd == 'live':
        from defense.ids_live import monitor
        monitor(args.log, args.model)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
