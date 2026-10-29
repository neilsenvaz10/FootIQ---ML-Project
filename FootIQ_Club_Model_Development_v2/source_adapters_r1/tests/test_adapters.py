"""Offline tests (stdlib unittest, no network). Real inputs: evidence/openligadb_bl1_2026.json and evidence/pl_2026_27.json (snapshots retrieved earlier).
Hand-written inputs below are TEST INPUTS for parser edge cases only; they are never written to any data store and contain no ingested football results."""
import json
import os
import stat
import sys
import tempfile
import unittest
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from footiq_sources import common, openligadb as ol, wikipedia_matrix as wm
from footiq_sources.identity import IdentityResolver
from footiq_sources.reconcile import reconcile_source

import pandas as pd

BL1 = open(os.path.join(ROOT, "evidence", "openligadb_bl1_2026.json"), "rb").read()
PL = json.load(open(os.path.join(ROOT, "evidence", "pl_2026_27.json"), encoding="utf-8"))["query"]["pages"][0]["revisions"][0]
NOW = datetime(2026, 10, 21, 14, 0, tzinfo=timezone.utc)


def cfg(tmp, live=True, contact="mailto:contact@footiq-test.local"):
    return common.AdapterConfig(live_enabled=live, contact=contact, snapshot_dir=os.path.join(tmp, "snap"), ledger_path=os.path.join(tmp, "snap", "ledger.jsonl"))


class TestCommon(unittest.TestCase):
    def test_live_disabled_by_default(self):
        c = common.AdapterConfig()
        with self.assertRaises(common.LiveAccessDenied):
            common.HttpClient(c, "x", 0).get("https://api.invalid/x")

    def test_contact_must_be_real(self):
        for bad in (None, "", "example.org", "withheld", "TODO"):
            with self.assertRaises(common.LiveAccessDenied):
                common.AdapterConfig(live_enabled=True, contact=bad).user_agent("S")
        ua = common.AdapterConfig(live_enabled=True, contact="mailto:contact@footiq-test.local").user_agent("S")
        self.assertIn("Bot", ua); self.assertIn("contact@footiq-test.local", ua)

    def test_backoff_and_retry_after(self):
        with tempfile.TemporaryDirectory() as t:
            calls, sleeps = [], []
            seq = [(429, b"", {"Retry-After": "7"}), (503, b"", {}), (200, b"ok", {"Content-Type": "application/json"})]
            def opener(url, h):
                calls.append(h["User-Agent"]); return seq[len(calls) - 1]
            body, meta = common.HttpClient(cfg(t), "S", 0.0, jitter_s=0.0, opener=opener, sleep=sleeps.append).get("https://api.invalid/x")
            self.assertEqual(body, b"ok"); self.assertEqual(len(calls), 3)
            self.assertIn(7.0, sleeps)                          # Retry-After honoured
            self.assertTrue(any(s >= 10 for s in sleeps))       # exponential back-off after 503
            self.assertEqual(len(open(os.path.join(t, "snap", "ledger.jsonl")).read().splitlines()), 3)

    def test_exhaustion_and_hard_error(self):
        with tempfile.TemporaryDirectory() as t:
            c = common.HttpClient(cfg(t), "S", 0.0, max_retries=2, jitter_s=0.0, opener=lambda u, h: (500, b"", {}), sleep=lambda s: None)
            with self.assertRaises(common.SourceUnavailable):
                c.get("https://api.invalid/x")
            c = common.HttpClient(cfg(t), "S", 0.0, jitter_s=0.0, opener=lambda u, h: (404, b"", {}), sleep=lambda s: None)
            with self.assertRaises(common.SourceUnavailable):
                c.get("https://api.invalid/x")

    def test_snapshots_are_write_once_and_read_only(self):
        with tempfile.TemporaryDirectory() as t:
            s = common.SnapshotStore(os.path.join(t, "s"))
            a = s.save("src", "n", b"1", {}); b = s.save("src", "n", b"2", {})
            self.assertNotEqual(a["snapshot_id"], b["snapshot_id"])
            p = os.path.join(t, "s", "src", a["snapshot_id"])
            self.assertEqual(open(p, "rb").read(), b"1")
            self.assertFalse(os.access(p, os.W_OK))


class TestContactHandling(unittest.TestCase):
    SECRET = "mailto:pilot.contact@footiq-test.local"

    def test_contact_not_read_from_tracked_json_and_loaded_from_env_or_local_file(self):
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, "adapters.json")
            json.dump({"live_enabled": False, "contact": "someone@real.org"}, open(p, "w"))
            old = os.environ.pop("FOOTIQ_CONTACT", None)
            old_file = os.environ.pop("FOOTIQ_CONTACT_FILE", None)
            try:
                self.assertIsNone(common.AdapterConfig.load(p).contact)             # 'contact' key in the JSON is ignored
                with open(os.path.join(t, "contact.local"), "w") as fh:
                    fh.write(self.SECRET)
                self.assertEqual(common.AdapterConfig.load(p).contact, self.SECRET)
                os.environ["FOOTIQ_CONTACT"] = "mailto:env@footiq-test.local"
                self.assertEqual(common.AdapterConfig.load(p).contact, "mailto:env@footiq-test.local")
            finally:
                os.environ.pop("FOOTIQ_CONTACT", None)
                if old: os.environ["FOOTIQ_CONTACT"] = old
                if old_file: os.environ["FOOTIQ_CONTACT_FILE"] = old_file

    def test_contact_never_printed_or_stored(self):
        with tempfile.TemporaryDirectory() as t:
            c = cfg(t, contact=self.SECRET)
            self.assertNotIn("footiq-test.local", repr(c))
            self.assertNotIn("footiq-test.local", c.redact("failed for " + self.SECRET + " at x"))
            sent = []
            def opener(url, h):
                sent.append(h["User-Agent"]); return 200, b"[]", {"Content-Type": "application/json"}
            body, meta = common.HttpClient(c, "S", 0.0, jitter_s=0.0, opener=opener, sleep=lambda s: None).get("https://api.invalid/x")
            self.assertIn("footiq-test.local", sent[0])                                  # the header carries it (required by the terms) ...
            info = common.SnapshotStore(c.snapshot_dir).save("S", "n", body, meta)
            for f in (os.path.join(c.snapshot_dir, "S", info["snapshot_id"] + ".meta.json"), c.ledger_path):
                self.assertNotIn("footiq-test.local", open(f, encoding="utf-8").read())  # ... but no log, ledger or metadata does
            with self.assertRaises(common.SourceUnavailable) as cm:
                common.HttpClient(c, "S", 0.0, max_retries=0, jitter_s=0.0, opener=lambda u, h: (500, b"", {}), sleep=lambda s: None).get("https://api.invalid/x")
            self.assertNotIn("footiq-test.local", str(cm.exception))


class TestOpenLigaDB(unittest.TestCase):
    def test_real_bundesliga_snapshot(self):
        recs = ol.parse_payload(BL1, "2026-10-21T00:00:00Z", "snap", NOW, "deutschland:1-bundesliga")
        self.assertEqual(len(recs), 306)
        comp = [r for r in recs if r.status == "completed"]
        self.assertEqual(len(comp), 54)
        self.assertTrue(all(r.result_type == "after90_explicit" and r.label_eligible_90min for r in comp))
        self.assertTrue(all(r.kickoff_utc and r.time_precision == "utc" and r.date_provenance == "source_stated" for r in recs))
        self.assertTrue(all(r.licence == "ODbL-1.0" and "OpenLigaDB" in r.attribution for r in recs))
        self.assertEqual(max(r.match_date for r in comp), "2026-10-18")
        self.assertTrue(all(r.regulation_home is None for r in recs if r.status != "completed"))
        self.assertTrue(all("user_entered_source_no_editorial_review" in r.flags for r in recs))

    def _m(self, **kw):
        base = dict(matchID=1, matchDateTimeUTC="2026-10-01T15:30:00Z", matchDateTime="2026-10-01T17:30:00", timeZoneID="W. Europe Standard Time", leagueId=1, leagueShortcut="bl1", leagueSeason=2026,
                    group={"groupName": "9. Spieltag", "groupOrderID": 9, "groupID": 3}, team1={"teamId": 1, "teamName": "A"}, team2={"teamId": 2, "teamName": "B"}, lastUpdateDateTime="2026-10-01T18:00:00",
                    matchIsFinished=True, matchResults=[])
        base.update(kw); return base

    def test_result_types_are_explicit(self):
        r = lambda kind, a, b: {"resultTypeKind": kind, "pointsTeam1": a, "pointsTeam2": b}
        rec = lambda m: ol.parse_match(m, "t", "s", NOW)
        a = rec(self._m(matchResults=[r("HalfTime", 0, 1), r("After90Minutes", 1, 2), r("AfterExtraTime", 2, 2)]))
        self.assertEqual((a.status, a.regulation_home, a.regulation_away, a.result_type), ("completed", 1, 2, "after90_explicit"))
        b = rec(self._m(matchResults=[r("AfterExtraTime", 3, 2)]))                       # final score only after ET: not a regulation score
        self.assertEqual((b.status, b.regulation_home, b.label_eligible_90min), ("completed_unclassified_score", None, False))
        c = rec(self._m(matchResults=[r("Unknown", 2, 0)]))                              # bare final score: never assumed to be 90 minutes
        self.assertEqual((c.status, c.regulation_home, c.result_type, c.label_eligible_90min), ("completed_unclassified_score", None, "unclassified_final", False))
        d = rec(self._m(matchResults=[r("After90Minutes", 1, 0), r("After90Minutes", 0, 0)]))
        self.assertIn("multiple_after90_results", d.flags); self.assertFalse(d.label_eligible_90min)

    def test_status_logic(self):
        past = ol.parse_match(self._m(matchIsFinished=False, matchDateTimeUTC="2026-10-10T15:30:00Z"), "t", "s", NOW)
        live = ol.parse_match(self._m(matchIsFinished=False, matchDateTimeUTC="2026-10-21T13:00:00Z"), "t", "s", NOW)
        fut = ol.parse_match(self._m(matchIsFinished=False, matchDateTimeUTC="2026-10-30T15:30:00Z"), "t", "s", NOW)
        none = ol.parse_match(self._m(matchIsFinished=False, matchDateTimeUTC=None), "t", "s", NOW)
        self.assertEqual([past.status, live.status, fut.status, none.status], ["past_date_no_result", "in_progress", "upcoming", "unresolved"])
        self.assertTrue(none.time_precision == "none" and none.kickoff_utc is None)

    def test_unverified_league_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            ad = ol.OpenLigaDBAdapter(cfg(t), client=common.HttpClient(cfg(t), "o", 0, opener=lambda u, h: (200, b"[]", {}), sleep=lambda s: None))
            with self.assertRaises(ValueError):
                ad.fetch_season("bl2", "2026")

    def test_change_date_polling(self):
        with tempfile.TemporaryDirectory() as t:
            md = json.loads(BL1)[:2]
            state = {"change": "2026-10-18T20:00:00"}
            seen = []
            def opener(url, h):
                seen.append(url.replace("https://api.openligadb.de", ""))
                if "getcurrentgroup" in url: return 200, json.dumps({"groupOrderID": 8}).encode(), {}
                if "getlastchangedate" in url: return 200, json.dumps(state["change"]).encode(), {}
                if "getmatchdata" in url: return 200, json.dumps(md).encode(), {}
                return 404, b"", {}
            c = cfg(t); ad = ol.OpenLigaDBAdapter(c, client=common.HttpClient(c, "o", 0, jitter_s=0, opener=opener, sleep=lambda s: None))
            recs, infos = ad.poll("bl1", "2026", NOW)
            self.assertEqual(len(infos), 2)                                          # first poll fetches matchdays 7 and 8
            seen.clear(); recs, infos = ad.poll("bl1", "2026", NOW)
            self.assertEqual(infos, []); self.assertFalse(any("getmatchdata" in s for s in seen))   # unchanged -> only cheap polls
            state["change"] = "2026-10-19T09:00:00"; seen.clear()
            recs, infos = ad.poll("bl1", "2026", NOW)
            self.assertEqual(len(infos), 2); self.assertTrue(any("getmatchdata" in s for s in seen))


MINI = """{{Infobox}}
|update=19 October 2026
|name_AAA=[[Alpha F.C.|Alpha]]
|name_BBB=[[Beta United]]
|name_CCC={{nowrap|[[Gamma City F.C.|Gamma City]]}}
|match_AAA_BBB=2–1
|match_AAA_CCC=
|match_BBB_AAA=[[Rivalry page|0–0]]<ref>note</ref>
|match_BBB_CCC=PP
|match_CCC_AAA=3-3
|match_CCC_BBB=1–0 (awd.)
"""


class TestWikipedia(unittest.TestCase):
    def test_real_premier_league_page(self):
        recs, meta = wm.parse_wikitext(PL["slots"]["main"]["content"], "2026–27 Premier League", PL["revid"], PL["timestamp"], "t", "s")
        comp = [r for r in recs if r.status == "completed"]
        self.assertEqual(len(comp), 70); self.assertEqual(meta["n_teams"], 20); self.assertEqual(meta["page_update_date"], "2026-10-19")
        self.assertTrue(all(r.kickoff_utc is None and r.kickoff_local is None and r.match_date is None and r.date_provenance == "none" for r in recs))
        self.assertTrue(all(str(PL["revid"]) in r.attribution and "CC BY-SA 4.0" in r.attribution for r in recs))
        self.assertFalse(any(r.label_eligible_90min for r in recs))                 # nothing is label-eligible before dates, stability and conflict checks

    def test_cell_parsing_edge_cases(self):
        recs, meta = wm.parse_wikitext(MINI, "2026–27 Premier League", 1, "2026-10-19T00:00:00Z", "t", "s")
        by = {r.source_ref.split(":")[1]: r for r in recs}
        self.assertEqual(len(recs), 5)                                              # empty cell skipped
        self.assertEqual((by["match_AAA_BBB"].regulation_home, by["match_AAA_BBB"].regulation_away), (2, 1))
        self.assertEqual(by["match_BBB_AAA"].status, "completed")                   # wikilink + ref stripped
        self.assertEqual(by["match_BBB_CCC"].status, "unresolved")                  # 'PP' is not a result
        self.assertEqual(by["match_CCC_AAA"].regulation_home, 3)
        self.assertEqual(by["match_CCC_BBB"].status, "unresolved")                  # annotated score is rejected, not guessed
        self.assertEqual(by["match_CCC_AAA"].home_raw, "Gamma City")

    def test_unsupported_and_duplicate(self):
        with self.assertRaises(wm.UnsupportedPageStyle):
            wm.parse_wikitext("== plain article ==", "x", 1, "t", "t", "s")
        with self.assertRaises(wm.UnsupportedPageStyle):
            wm.parse_wikitext(MINI + "|match_AAA_BBB=1–1\n", "x", 1, "t", "t", "s")

    def _setup(self):
        V = pd.DataFrame(dict(competition_id=["c"] * 3, home_team_name=["Alpha", "Beta United", "Gamma City"], home_entity_id=["E1", "E2", "E3"], away_team_name=["Beta United", "Gamma City", "Alpha"], away_entity_id=["E2", "E3", "E1"]))
        pairs = set(zip(V.competition_id, V.home_team_name, V.home_entity_id)) | set(zip(V.competition_id, V.away_team_name, V.away_entity_id))
        return IdentityResolver(pairs)

    def test_schedule_date_attachment_and_rejections(self):
        res = self._setup()
        recs, meta = wm.parse_wikitext(MINI, "2026–27 Premier League", 1, "2026-10-19T00:00:00Z", "t", "s")
        sched = [dict(competition_id="c", season="2026-27", match_date="2026-10-03", home_entity_id="E1", away_entity_id="E2"),
                 dict(competition_id="c", season="2026-27", match_date="2026-10-04", home_entity_id="E2", away_entity_id="E1"),
                 dict(competition_id="c", season="2026-27", match_date="2026-10-25", home_entity_id="E3", away_entity_id="E1"),   # after page update date
                 dict(competition_id="c", season="2026-27", match_date="2026-09-01", home_entity_id="E3", away_entity_id="E2"),
                 dict(competition_id="c", season="2026-27", match_date="2026-09-20", home_entity_id="E3", away_entity_id="E2")]   # second fixture for the same pair -> ambiguous
        for r in recs: r.season = "2026-27"
        ok, bad = wm.attach_schedule_dates(recs, sched, res, "c", meta["page_update_date"])
        self.assertEqual(sorted(r.source_ref.split(":")[1] for r in ok), ["match_AAA_BBB", "match_BBB_AAA"])
        self.assertTrue(all(r.date_provenance == "inherited_from_openfootball_schedule" and r.time_precision == "inherited_date" and r.kickoff_utc is None for r in ok))
        reasons = {r.source_ref.split(":")[1]: why for r, why in bad}
        self.assertEqual(reasons["match_CCC_AAA"], "scheduled_date_after_page_update_date")
        self.assertIn(reasons["match_CCC_BBB"], ("not_a_completed_result",))

    def test_older_revision_confirmation(self):
        new, _ = wm.parse_wikitext(MINI.replace("2–1", "3–1"), "t", 2, "x", "t", "s")
        old, _ = wm.parse_wikitext(MINI, "t", 1, "x", "t", "s")
        stable, changed, new_only = wm.confirm_with_older_revision(new, old)
        self.assertEqual([r.source_ref.split(":")[1] for r in changed], ["match_AAA_BBB"])
        self.assertEqual(len(stable), 2)

    def test_live_requires_registry_and_config(self):
        with tempfile.TemporaryDirectory() as t:
            ad = wm.WikipediaAdapter(cfg(t, live=False))
            with self.assertRaises(common.LiveAccessDenied):
                ad.revision_older_than("2026–27 Premier League")
            ad2 = wm.WikipediaAdapter(cfg(t), client=common.HttpClient(cfg(t), "W", 0, opener=lambda u, h: (200, b"{}", {}), sleep=lambda s: None))
            with self.assertRaises(ValueError):
                ad2.fetch_revision("Some random page", 1)


class TestReconcile(unittest.TestCase):
    def test_agree_conflict_recovered_unresolved(self):
        V = pd.DataFrame(dict(competition_id=["c", "c"], season_corrected=["2026-27"] * 2, match_date=["2026-09-01", "2026-09-02"], home_team_name=["Alpha", "Beta"], home_entity_id=["E1", "E2"],
                              away_team_name=["Beta", "Gamma"], away_entity_id=["E2", "E3"], gh=[1.0, 2.0], ga=[0.0, 2.0]))
        pairs = set(zip(V.competition_id, V.home_team_name, V.home_entity_id)) | set(zip(V.competition_id, V.away_team_name, V.away_entity_id))
        res = IdentityResolver(pairs)
        miss = pd.DataFrame(dict(home_entity_id=["E3"], away_entity_id=["E1"], match_date=["2026-10-10"]))
        mk = lambda ref, h, a, hg, ag, d: ol.parse_match(dict(matchID=ref, matchDateTimeUTC=d, matchDateTime=d, timeZoneID="x", leagueId=1, leagueShortcut="c", leagueSeason=2026, group={"groupName": "g", "groupOrderID": 1},
                                                                  team1={"teamId": 1, "teamName": h}, team2={"teamId": 2, "teamName": a}, matchIsFinished=True,
                                                                  matchResults=[{"resultTypeKind": "After90Minutes", "pointsTeam1": hg, "pointsTeam2": ag}]), "t", "s", NOW)
        recs = [mk(1, "Alpha", "Beta", 1, 0, "2026-09-01T15:00:00Z"), mk(2, "Beta", "Gamma", 3, 2, "2026-09-02T15:00:00Z"), mk(3, "Gamma", "Alpha", 0, 0, "2026-10-10T15:00:00Z"), mk(4, "Zeta", "Alpha", 1, 1, "2026-10-11T15:00:00Z")]
        out = reconcile_source(recs, "openligadb", "c", "2026-27", V, miss, res, "2026-10-21")
        s = out["summary"]
        self.assertEqual((s["exact_score_agreements"], s["conflicts"], s["newly_recovered"], s["unresolved_team_identities"]), (1, 1, 1, 1))
        self.assertEqual(len(out["conflicts"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
