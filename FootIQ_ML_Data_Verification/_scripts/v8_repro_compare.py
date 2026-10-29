"""Stage 8: compare the isolated rebuild (scratchpad copy of the readiness pipeline) with the existing outputs."""
import hashlib
import json
import os
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
P = r"D:\Foot IQ"
OLD = os.path.join(P, "FootIQ_ML_Data_Readiness")
NEW = r"C:\Users\DELL\AppData\Local\Temp\claude\D--Foot-IQ\6f3c799b-eb7a-4487-a086-4747b01b4f7a\scratchpad\repro\FootIQ_ML_Data_Readiness"
EV = os.path.join(P, "FootIQ_ML_Data_Verification", "_evidence")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 22), b""):
            h.update(ch)
    return h.hexdigest()


rows = []
for f in sorted(os.listdir(NEW)):
    pn = os.path.join(NEW, f)
    if not os.path.isfile(pn):
        continue
    po = os.path.join(OLD, f)
    if not os.path.exists(po):
        rows.append(dict(file=f, status="new_only"))
        continue
    a, b = sha(pn), sha(po)
    rows.append(dict(file=f, bytes_new=os.path.getsize(pn), bytes_old=os.path.getsize(po), identical_bytes=a == b, sha_new=a[:16], sha_old=b[:16]))
df = pd.DataFrame(rows)
df.to_csv(os.path.join(EV, "repro_file_hash_comparison.csv"), index=False)
print(df.to_string())
# row-level canonical comparison where bytes differ (only CSV)
detail = []
for r in df[(df.identical_bytes == False)].itertuples():
    if r.file.endswith(".csv"):
        a = pd.read_csv(os.path.join(NEW, r.file), low_memory=False, encoding="utf-8-sig")
        b = pd.read_csv(os.path.join(OLD, r.file), low_memory=False, encoding="utf-8-sig")
        same_shape = a.shape == b.shape
        eq = a.equals(b) if same_shape else False
        detail.append(dict(file=r.file, same_shape=same_shape, frames_equal=eq, rows_new=len(a), rows_old=len(b)))
pd.DataFrame(detail).to_csv(os.path.join(EV, "repro_row_level_comparison.csv"), index=False)
print(pd.DataFrame(detail).to_string())
pn = pd.read_pickle(os.path.join(NEW, "_build", "work", "data_all.pkl"))
po = pd.read_pickle(os.path.join(OLD, "_build", "work", "data_all.pkl"))
cols = ["record_id", "match_date", "home_elo", "away_elo", "home_n_prior", "away_n_prior", "y90", "label_90_status", "train_eligible_strict", "train_eligible_extended", "suggested_split"]
a = pn[cols].sort_values("record_id").reset_index(drop=True)
b = po[cols].sort_values("record_id").reset_index(drop=True)
res = dict(rows_new=len(a), rows_old=len(b), key_columns_equal=bool(a.equals(b)))
json.dump(res, open(os.path.join(EV, "repro_pickle_comparison.json"), "w"))
print(res)
