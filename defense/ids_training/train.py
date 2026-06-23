"""
Treina XGBoost para deteccao de intrusao SOME/IP.

Analogo ao defense/ids_training/train.py do yes-carla-can (Isolation Forest),
mas usando XGBoost com features comportamentais e split temporal.

Features extraidas de janelas temporais de 1s:
  - tx_rate: pacotes por segundo por servico
  - inter_arrival_mean/std: intervalo medio entre pacotes
  - payload_len_mean/std: tamanho medio do payload
  - unique_sessions: sessoes unicas no intervalo
  - service_entropy: entropia de distribuicao de servicos
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
from xgboost import XGBClassifier
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder


FEATURES = [
    'tx_rate', 'inter_arrival_mean', 'inter_arrival_std',
    'payload_len_mean', 'payload_len_std',
    'unique_sessions', 'service_entropy',
]

WINDOW_S = 1.0   # janela temporal em segundos


def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extrai features comportamentais por janela temporal."""
    df = df.sort_values('ts').reset_index(drop=True)
    df['window'] = (df['ts'] // WINDOW_S).astype(int)

    rows = []
    for (window, label), g in df.groupby(['window', 'label']):
        g = g.sort_values('ts')
        inter = g['ts'].diff().dropna()
        svc_counts = g['service_id'].value_counts(normalize=True)
        entropy = -float((svc_counts * np.log2(svc_counts + 1e-9)).sum())
        rows.append({
            'window':              window,
            'label':               label,
            'tx_rate':             len(g) / WINDOW_S,
            'inter_arrival_mean':  inter.mean() if len(inter) else 0,
            'inter_arrival_std':   inter.std()  if len(inter) else 0,
            'payload_len_mean':    g['payload_len'].mean(),
            'payload_len_std':     g['payload_len'].std(ddof=0),
            'unique_sessions':     g['session_id'].nunique(),
            'service_entropy':     entropy,
        })
    return pd.DataFrame(rows)


def train(data_path: str, model_path: str) -> None:
    df_raw = pd.read_csv(data_path)
    df     = extract_features(df_raw)

    # split temporal: 80% treino, 20% teste
    split  = int(len(df) * 0.8)
    df_tr  = df.iloc[:split]
    df_te  = df.iloc[split:]

    le = LabelEncoder()
    y_tr = le.fit_transform(df_tr['label'])
    y_te = le.transform(df_te['label'])

    clf = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        use_label_encoder=False,
        eval_metric='mlogloss',
        random_state=42,
    )
    clf.fit(df_tr[FEATURES], y_tr,
            eval_set=[(df_te[FEATURES], y_te)],
            verbose=False)

    y_pred = clf.predict(df_te[FEATURES])
    print(classification_report(y_te, y_pred, target_names=le.classes_))

    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({'clf': clf, 'le': le, 'features': FEATURES}, model_path)
    print(f'Modelo salvo em {model_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data',  required=True)
    parser.add_argument('--model', default='defense/models/xgb_someip.pkl')
    args = parser.parse_args()
    train(args.data, args.model)
