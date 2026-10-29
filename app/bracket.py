"""2026 World Cup knockout bracket built ONLY from the repository's own files:
fixtures (data/processed/worldcup_2026_matches.csv: round, date, venue and the slot each team comes from) and the verified results
(data/processed/worldcup_2026_knockout_results_verified.csv). Nothing is simulated or invented; matches without a result are marked as such.
"""
import csv
import re
from functools import lru_cache

import config as C
import names

FIXTURES = C.ROOT / "data" / "processed" / "worldcup_2026_matches.csv"
RESULTS = C.ROOT / "data" / "processed" / "worldcup_2026_knockout_results_verified.csv"
ROUNDS = ["Round of 32", "Round of 16", "Quarter-final", "Semi-final", "Final"]
THIRD = "Match for third place"


def _read(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _pair(text):
    m = re.fullmatch(r"\s*(\d+)\s*-\s*(\d+)\s*", text or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


@lru_cache(maxsize=1)
def build() -> dict:
    fixtures = {int(r["fixture_id"]): r for r in _read(FIXTURES) if r["round"] in ROUNDS + [THIRD]}
    results = {int(r["fixture_id"]): r for r in _read(RESULTS)}
    matches: dict[int, dict] = {}
    for fid in sorted(fixtures):
        f, r = fixtures[fid], results.get(fid)
        m = dict(id=fid, round=f["round"], date=f["date"], venue=f["ground"], slots=[f["team1"], f["team2"]], team1=None, team2=None, score=None, shootout=None, winner=None,
                 status="result not in the dataset", source=None)
        if r:
            m["team1"], m["team2"] = names.canon_intl(r["team1"]), names.canon_intl(r["team2"])
            sc, so = _pair(r["score_after_extra_time"]), _pair(r["shootout_score"])
            m["score"] = dict(team1=sc[0], team2=sc[1]) if sc else None
            m["shootout"] = dict(team1=so[0], team2=so[1]) if so else None
            m["winner"] = names.canon_intl(r["winner"]) if r["winner"] else None
            m["status"] = "played"
            m["source"] = r["verification_source"]
        matches[fid] = m
    # a match without a result still has known teams when both feeder matches have a winner (e.g. the final)
    for m in matches.values():
        for i, slot in enumerate(m["slots"]):
            k = f"team{i + 1}"
            ref = re.fullmatch(r"([WL])(\d+)", slot)
            if m[k] is None and ref and int(ref.group(2)) in matches:
                src = matches[int(ref.group(2))]
                if src["winner"]:
                    loser = src["team2"] if src["winner"] == src["team1"] else src["team1"]
                    m[k] = src["winner"] if ref.group(1) == "W" else loser
    # order every round so that matches 2i and 2i+1 feed match i of the next round (draw the tree from the final backwards)
    ordered = {ROUNDS[-1]: [m for m in matches.values() if m["round"] == ROUNDS[-1]]}
    for n, nxt in zip(reversed(ROUNDS[:-1]), reversed(ROUNDS[1:])):
        feeders = []
        for m in ordered[nxt]:
            for slot in m["slots"]:
                ref = re.fullmatch(r"W(\d+)", slot)
                if ref and int(ref.group(1)) in matches and matches[int(ref.group(1))]["round"] == n:
                    feeders.append(matches[int(ref.group(1))])
        ordered[n] = feeders
    rounds = [dict(name=n, matches=ordered[n]) for n in ROUNDS]
    third = [m for m in matches.values() if m["round"] == THIRD]
    return dict(
        rounds=rounds, third_place=third[0] if third else None,
        note="Real 2026 results from the repository's verified file; this is not a simulation or a prediction. Matches without a result are shown as such (the final is not in the dataset).",
        sources=[FIXTURES.relative_to(C.ROOT).as_posix(), RESULTS.relative_to(C.ROOT).as_posix()])
