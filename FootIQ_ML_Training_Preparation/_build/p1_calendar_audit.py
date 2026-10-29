"""P1: source-level calendar verification of every openfootball match date (read-only on sources).
A date is 'verified' only if the source line printed an explicit year, or printed a weekday that equals the weekday of the
resolved date. Dotted dates (DD.MM.) carry neither, so they are unverifiable. The file's declared '# Date' window is an extra check."""
import os, re, sys
from datetime import datetime
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
P = r"D:\Foot IQ"
SUB = os.path.join(P, "FootIQ_Dataset_Submission")
OUT = os.path.join(P, "FootIQ_ML_Training_Preparation", "_build", "work")
sys.path.insert(0, os.path.join(SUB, "_build"))
import footballtxt as ft  # read-only import of the original parser

cm = pd.read_csv(os.path.join(SUB, "_build", "work", "club_matches_all.csv"), low_memory=False, keep_default_na=False, na_values=[""])
cm["season"] = cm.season.astype(str)
LOG = []
_orig = ft._resolve_date


def wrapped(mon, day, yr, prev, title, season_start_year, issues, ln, line):
    d = _orig(mon, day, yr, prev, title, season_start_year, issues, ln, line)
    dm = re.search(ft.DOW, line)
    if yr:
        st = "explicit_year"
    elif d is None:
        st = "unresolvable"
    elif dm and d.strftime("%a") == dm.group(0):
        st = "weekday_verified"
    elif dm:
        st = "weekday_mismatch"
    else:
        st = "no_weekday_no_year_UNVERIFIED"
    LOG.append((ln, st))
    return d


ft._resolve_date = wrapped
RE = re.compile(r"#\s*Dates?\s+(?:\w{3}\s+)?(\w{3})\s+(\d{1,2})(?:\s+(\d{4}))?\s*-\s*(?:\w{3}\s+)?(\w{3})\s+(\d{1,2})\s+(\d{4})")
MN = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
rows, files = [], []
for f, g in cm.groupby("source_file"):
    text = open(os.path.join(SUB, "_raw_sources", f), encoding="utf-8").read()
    season = g.season.iloc[0]
    LOG.clear()
    title, matches, issues = ft.parse_text(text, int(season[:4]))
    logs = list(LOG)
    m = RE.search(text[:3000])
    ws = we = None
    if m:
        y2 = int(m.group(6)); we = datetime(y2, MN[m.group(4)], int(m.group(5)))
        y1 = int(m.group(3)) if m.group(3) else (y2 if MN[m.group(1)] <= we.month else y2 - 1)
        ws = datetime(y1, MN[m.group(1)], int(m.group(2)))
    ln_status = {}
    for mt in matches:
        prev = [s for l, s in logs if l < mt["line_no"]]
        ln_status[mt["line_no"]] = (prev[-1] if prev else "no_date_line", mt["date"])
    stored = dict(zip(g.source_line, g.match_date))
    same = sum(1 for k, (s, d) in ln_status.items() if stored.get(k) == d)
    tm = re.search(r"(\d{4})(?:/(\d{2,4}))?\s*$", title or "")
    files.append(dict(source_file=f, competition_id=g.competition_id.iloc[0], season_label=season, title=title, rows=len(g), parsed=len(ln_status),
                      reproduced_dates=same, win_start=ws, win_end=we, win_span_days=(we - ws).days if ws else None,
                      n_date_lines=len(logs), n_unverified=sum(1 for _, s in logs if s in ("no_weekday_no_year_UNVERIFIED", "weekday_mismatch", "unresolvable"))))
    for k, (s, d) in ln_status.items():
        rows.append((f, k, d, s, ws, we))
rr = pd.DataFrame(rows, columns=["source_file", "source_line", "reparsed_date", "date_status", "win_start", "win_end"])
rr["in_declared_window"] = [(ws is None) or (pd.Timestamp(d) >= pd.Timestamp(ws) and pd.Timestamp(d) <= pd.Timestamp(we)) if d else False for d, ws, we in zip(rr.reparsed_date, rr.win_start, rr.win_end)]
fd = pd.DataFrame(files)
fd.to_csv(os.path.join(OUT, "calendar_audit_files.csv"), index=False)
rr.to_pickle(os.path.join(OUT, "calendar_audit_rows.pkl"))
print("files", len(fd), "rows", len(rr), "reproduced original dates", int(fd.reproduced_dates.sum()), "of", int(fd.parsed.sum()))
print(rr.date_status.value_counts().to_string())
bad = rr[rr.date_status.isin(["no_weekday_no_year_UNVERIFIED", "weekday_mismatch", "unresolvable", "no_date_line"])]
print("unverified rows:", len(bad)); print(bad.merge(fd[["source_file", "competition_id"]], on="source_file").groupby("competition_id").size().sort_values(ascending=False).head(15).to_string())
print("rows outside declared window:", int((~rr.in_declared_window).sum()))
