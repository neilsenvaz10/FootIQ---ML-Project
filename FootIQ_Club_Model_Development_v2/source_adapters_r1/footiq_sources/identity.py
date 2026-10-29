"""Identity resolution against the FROZEN entity map (read-only). New sources never create entities.

Ladder: (1) exact name in the competition, (2) normalised name in the competition, (3) reviewed alias rows (alias CSV), (4) suggestions only (never auto-accepted).
Ambiguity (one normalised name -> several entities in a competition) is returned as ambiguous, never resolved by guessing.
"""
import csv
import os
import re
import unicodedata
from collections import defaultdict

TOKENS = {"fc", "afc", "sv", "vfb", "vfl", "tsg", "bv", "rb", "sc", "ac", "cf", "fk", "sk", "ev", "e", "v", "1", "1899", "1846", "1848", "09", "04", "05", "96", "78", "the"}


def norm(name: str) -> str:
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    parts = [p for p in s.split() if p not in TOKENS]
    return "".join(parts)


class IdentityResolver:
    def __init__(self, frozen_pairs, alias_rows=()):
        """frozen_pairs: iterable of (competition_id, team_name, entity_id) taken from the frozen universe (read-only)."""
        self.exact = defaultdict(set)
        self.normed = defaultdict(set)
        for c, n, e in frozen_pairs:
            self.exact[(c, n)].add(e)
            self.normed[(c, norm(n))].add(e)
        self.alias = {}
        for r in alias_rows:
            self.alias[(r["source"], r["competition_id"], r["source_name"])] = r["entity_id"]

    @staticmethod
    def _prefer_unscoped(ents):
        un = {e for e in ents if not e.startswith("SRCSCOPED|")}
        return un or ents

    def resolve(self, source, competition_id, name):
        """returns (entity_id | None, method) with method in exact|normalised|alias|ambiguous|unresolved"""
        a = self.alias.get((source, competition_id, name))
        if a:
            return a, "alias"
        e = self._prefer_unscoped(self.exact.get((competition_id, name), set()))
        if len(e) == 1:
            return next(iter(e)), "exact"
        if len(e) > 1:
            return None, "ambiguous"
        e = self._prefer_unscoped(self.normed.get((competition_id, norm(name)), set()))
        if len(e) == 1:
            return next(iter(e)), "normalised"
        if len(e) > 1:
            return None, "ambiguous"
        return None, "unresolved"

    @staticmethod
    def load_alias_csv(path):
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8-sig", newline="") as fh:
            return list(csv.DictReader(fh))
