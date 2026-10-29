import hashlib, json, os, sys
import numpy as np
import pandas as pd
P = r"D:\Foot IQ"
PREP = os.path.join(P, "FootIQ_ML_Training_Preparation")
V1 = os.path.join(P, "FootIQ_Club_Model_Baseline_v1")
OUT = os.path.join(P, "FootIQ_Club_Model_Development_v2")
WORK = os.path.join(OUT, "_work")
ART = os.path.join(OUT, "artifacts")
ENC = "utf-8-sig"
SEED = 20261021
CLASSES = ["H", "D", "A"]
DEV_END = "2024-06-30"      # nothing after this date is used for any v2 decision
FOLDS = [
    dict(fold=1, train_end="2021-06-30", val_start="2021-07-01", val_end="2022-06-30"),
    dict(fold=2, train_end="2022-06-30", val_start="2022-07-01", val_end="2023-06-30"),
    dict(fold=3, train_end="2023-06-30", val_start="2023-07-01", val_end="2024-06-30"),
]
TRAIN_START = "2018-08-01"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(1 << 22), b""):
            h.update(ch)
    return h.hexdigest()


def metrics(y, p):
    y = np.asarray(y).astype(int)
    p = np.clip(np.asarray(p, float), 1e-15, 1.0)
    p = p / p.sum(1, keepdims=True)
    pred = p.argmax(1)
    f1 = []
    for k in range(3):
        tp = ((pred == k) & (y == k)).sum(); fp = ((pred == k) & (y != k)).sum(); fn = ((pred != k) & (y == k)).sum()
        f1.append(0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn))
    oh = np.eye(3)[y]
    return dict(n=int(len(y)), log_loss=float(-np.log(p[np.arange(len(y)), y]).mean()), brier=float(((p - oh) ** 2).sum(1).mean()), accuracy=float((pred == y).mean()),
                macro_f1=float(np.mean(f1)), f1_H=f1[0], f1_D=f1[1], f1_A=f1[2], draw_predicted=int((pred == 1).sum()), draw_recall=float(((pred == 1) & (y == 1)).sum() / max((y == 1).sum(), 1)))
