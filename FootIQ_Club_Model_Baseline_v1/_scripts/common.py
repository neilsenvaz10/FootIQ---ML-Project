import hashlib, json, os, sys
import numpy as np
import pandas as pd
P = os.environ.get("FOOTIQ_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
PREP = os.path.join(P, "FootIQ_ML_Training_Preparation")
OUT = os.path.join(P, "FootIQ_Club_Model_Baseline_v1")
ART = os.path.join(OUT, "artifacts")
ENC = "utf-8-sig"
SEED = 20261020
CLASSES = ["H", "D", "A"]
BOUNDS = {"train": ("2018-08-01", "2023-06-30"), "validation": ("2023-07-01", "2024-06-30"), "test": ("2024-07-01", "2025-06-30"), "forward_holdout": ("2025-07-01", "2026-09-30")}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(1 << 22), b""):
            h.update(ch)
    return h.hexdigest()


def sha_list(ids):
    return hashlib.sha256("\n".join(sorted(map(str, ids))).encode()).hexdigest()


def metrics(y_idx, proba):
    """y_idx: ints 0/1/2 (H,D,A); proba: n x 3. Returns dict of accuracy, macro F1, log loss, Brier."""
    y = np.asarray(y_idx)
    p = np.clip(np.asarray(proba, float), 1e-15, 1.0)
    p = p / p.sum(axis=1, keepdims=True)
    pred = p.argmax(1)
    acc = float((pred == y).mean())
    f1s = []
    for k in range(3):
        tp = ((pred == k) & (y == k)).sum(); fp = ((pred == k) & (y != k)).sum(); fn = ((pred != k) & (y == k)).sum()
        f1s.append(0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn))
    onehot = np.eye(3)[y]
    return dict(n=int(len(y)), accuracy=acc, macro_f1=float(np.mean(f1s)), log_loss=float(-np.log(p[np.arange(len(y)), y]).mean()),
                brier=float(((p - onehot) ** 2).sum(1).mean()))
