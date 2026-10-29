"""Wikipedia season-page adapter (results matrix style `|match_<HOME>_<AWAY>=score`, English Wikipedia, MediaWiki Action API).

Licence: CC BY-SA 4.0 + GFDL (text). Records are tagged with page title, revision id and a permalink as attribution. Wikipedia-derived records are kept SEPARATE and are NOT promoted to
the official feature store until the owner approves the permitted-use document (docs/02_WIKIPEDIA_LICENSING_AND_USE.md).
Policies followed by the live client: descriptive User-Agent with real contact and the word "bot", serial requests >= 5 s apart (Action API: unauthenticated 1 concurrent request, < 5/s,
wait 5 s after slow requests), `maxlag`, gzip not required for JSON, back-off on 429 with Retry-After, no crawling of non-canonical URLs.
The matrix carries scores only: no dates, no kickoff times. Dates are inherited from the openfootball schedule, explicitly flagged, and never presented as source-stated.
"""
import json
import re
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Optional

from .common import AdapterConfig, HttpClient, SnapshotStore, StagingRecord, utc_now
from .identity import IdentityResolver

SOURCE = "wikipedia"
LICENCE = "CC BY-SA 4.0 (+GFDL)"
API = "https://en.wikipedia.org/w/api.php"
DASH = "[–—−-]"
CELL = re.compile(r"\|\s*match_([A-Z0-9]{2,4})_([A-Z0-9]{2,4})\s*=([^\n]*)")
NAME = re.compile(r"\|\s*name_([A-Z0-9]{2,4})\s*=\s*([^\n]*)")
UPDATE = re.compile(r"\|\s*update\s*=\s*([^\n|]+)")
SCORE = re.compile(rf"^\s*(\d{{1,2}})\s*{DASH}\s*(\d{{1,2}})\s*$")

# 15 researched in-season leagues. Only the page style that was actually inspected is marked verified; others need a stored page fixture before live use.
REGISTRY = {
    "2026–27 Premier League": dict(competition_id="england:1-premierleague", season="2026-27", verified_style=True),
    "2026–27 EFL Championship": dict(competition_id="england:2-championship", season="2026-27", verified_style=False),
    "2026–27 La Liga": dict(competition_id="espana:1-liga", season="2026-27", verified_style=False),
    "2026–27 Serie A": dict(competition_id="italy:1-seriea", season="2026-27", verified_style=False),
    "2026–27 Bundesliga": dict(competition_id="deutschland:1-bundesliga", season="2026-27", verified_style=False),
    "2026–27 Ligue 1": dict(competition_id="europe/france:fr1", season="2026-27", verified_style=False),
    "2026–27 Eredivisie": dict(competition_id="europe/netherlands:nl1", season="2026-27", verified_style=False),
    "2026–27 Primeira Liga": dict(competition_id="europe/portugal:pt1", season="2026-27", verified_style=False),
    "2026–27 Scottish Premiership": dict(competition_id="europe/scotland:sco1", season="2026-27", verified_style=False),
    "2026 Campeonato Brasileiro Série A": dict(competition_id="south-america/brazil:br1", season="2026", verified_style=False),
    "2026–27 Süper Lig": dict(competition_id="europe/turkey:tr1", season="2026-27", verified_style=False),
    "2026–27 Austrian Football Bundesliga": dict(competition_id="austria:1-bundesliga", season="2026-27", verified_style=False),
    "2026–27 Super League Greece": dict(competition_id="europe/greece:gr1", season="2026-27", verified_style=False),
    "2026–27 Swiss Super League": dict(competition_id="europe/switzerland:ch1", season="2026-27", verified_style=False),
    "2026–27 Czech First League": dict(competition_id="europe/czech-republic:cz1", season="2026-27", verified_style=False),
}


class UnsupportedPageStyle(ValueError):
    pass


def permalink(title: str, revid: int) -> str:
    return f"https://en.wikipedia.org/w/index.php?title={urllib.parse.quote(title.replace(' ', '_'))}&oldid={revid}"


def _clean(v: str) -> str:
    v = re.sub(r"<!--.*?-->", "", v, flags=re.S)
    v = re.sub(r"<ref[^>/]*/>|<ref[^>]*>.*?</ref>", "", v, flags=re.S)
    v = re.sub(r"\[\[([^\]|]*)\|([^\]]*)\]\]", r"\2", v)         # [[target|text]] -> text
    v = re.sub(r"\[\[([^\]]*)\]\]", r"\1", v)
    return v.strip()


def _display_name(v: str) -> str:
    v = re.sub(r"\{\{nowrap\|([^}]*)\}\}", r"\1", v)
    return _clean(v).strip()


def parse_update_date(wikitext: str) -> Optional[str]:
    m = UPDATE.search(wikitext)
    if not m:
        return None
    for fmt in ("%d %B %Y", "%B %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(m.group(1).strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_wikitext(wikitext: str, title: str, revid: int, rev_timestamp: str, retrieved_utc: str, snapshot_id: str):
    """Returns (records, page_meta). Only unambiguous `home-away` scores become completed records; everything else is kept as `unresolved` with a flag."""
    cells, names = CELL.findall(wikitext), dict((a, _display_name(b)) for a, b in NAME.findall(wikitext))
    if not cells or not names:
        raise UnsupportedPageStyle(f"{title}: no match_/name_ matrix parameters found")
    reg = REGISTRY.get(title, {})
    attribution = f"Match data adapted from English Wikipedia, '{title}', revision {revid} ({rev_timestamp}), CC BY-SA 4.0: {permalink(title, revid)}"
    recs, seen = [], set()
    for h, a, raw in cells:
        if (h, a) in seen:
            raise UnsupportedPageStyle(f"{title}: duplicate cell {h}-{a}")
        seen.add((h, a))
        v = _clean(raw)
        if not v:
            continue                                         # unplayed fixture: no record
        m = SCORE.match(v)
        flags = ["wikipedia_volunteer_edited", "date_not_in_source"]
        if h not in names or a not in names:
            status, rh, ra, flags = "unresolved", None, None, flags + ["team_abbreviation_without_name"]
        elif not m:
            status, rh, ra, flags = "unresolved", None, None, flags + [f"unparsed_cell:{v[:30]}"]
        else:
            status, rh, ra = "completed", int(m.group(1)), int(m.group(2))
        recs.append(StagingRecord(
            source=SOURCE, source_ref=f"{title}@{revid}:match_{h}_{a}", competition_key=title, season=reg.get("season", ""), stage="league", round=None,
            home_raw=names.get(h, h), away_raw=names.get(a, a), status=status, kickoff_utc=None, kickoff_local=None, time_zone=None, time_precision="none", match_date=None,
            date_provenance="none", regulation_home=rh, regulation_away=ra, result_type="wikipedia_matrix_unspecified" if status == "completed" else "none",
            label_eligible_90min=False,                      # set only after dates attach and stability + conflict checks pass (see promote_candidates)
            source_ids=dict(page=title, revid=revid, abbreviations=[h, a]), retrieved_utc=retrieved_utc, source_revision=str(revid), snapshot_id=snapshot_id,
            licence=LICENCE, attribution=attribution, flags=flags))
    meta = dict(title=title, revid=revid, revision_timestamp=rev_timestamp, page_update_date=parse_update_date(wikitext), n_teams=len(names), n_scored=sum(r.status == "completed" for r in recs),
                n_unresolved_cells=sum(r.status == "unresolved" for r in recs), registry=reg, permalink=permalink(title, revid), attribution=attribution)
    return recs, meta


def attach_schedule_dates(recs, schedule, resolver: IdentityResolver, competition_id: str, page_update_date: Optional[str]):
    """schedule: iterable of dict(competition_id, season, match_date, home_entity_id, away_entity_id) taken from the openfootball snapshot (read-only).
    Returns (accepted, rejected[(record, reason)]). Dates are inherited and flagged; ambiguity and conflicts are rejected, never guessed."""
    idx = {}
    for s in schedule:
        if s["competition_id"] == competition_id:
            idx.setdefault((s["season"], s["home_entity_id"], s["away_entity_id"]), []).append(s)
    ok, bad = [], []
    for r in recs:
        if r.status != "completed":
            bad.append((r, "not_a_completed_result"))
            continue
        he, hm = resolver.resolve(SOURCE, competition_id, r.home_raw)
        ae, am = resolver.resolve(SOURCE, competition_id, r.away_raw)
        if not he or not ae:
            bad.append((r, f"team_identity_{hm}_{am}"))
            continue
        rows = idx.get((r.season, he, ae), [])
        if len(rows) == 0:
            bad.append((r, "no_scheduled_fixture_for_pair"))
        elif len(rows) > 1:
            bad.append((r, "ambiguous_multiple_fixtures_for_pair"))
        else:
            d = rows[0]["match_date"]
            if page_update_date and d > page_update_date:
                bad.append((r, "scheduled_date_after_page_update_date"))
                continue
            r.match_date, r.date_provenance, r.time_precision = d, "inherited_from_openfootball_schedule", "inherited_date"
            r.flags = r.flags + ["date_inherited_from_openfootball_schedule", f"home_entity={he}", f"away_entity={ae}"]
            ok.append(r)
    return ok, bad


def confirm_with_older_revision(newer, older):
    """A result is 'stable' when the same pair has the identical score in an older revision (caller supplies a revision >= 24 h older). Returns (stable, changed, new_only)."""
    old = {(r.home_raw, r.away_raw): (r.regulation_home, r.regulation_away) for r in older if r.status == "completed"}
    stable, changed, new_only = [], [], []
    for r in newer:
        if r.status != "completed":
            continue
        k = (r.home_raw, r.away_raw)
        if k not in old:
            new_only.append(r)
        elif old[k] == (r.regulation_home, r.regulation_away):
            stable.append(r)
        else:
            changed.append(r)
    return stable, changed, new_only


class WikipediaAdapter:
    def __init__(self, cfg: Optional[AdapterConfig] = None, client: Optional[HttpClient] = None):
        self.cfg = cfg or AdapterConfig.load()
        self.client = client or HttpClient(self.cfg, "Wikipedia", min_interval_s=5.0, jitter_s=1.0)
        self.store = SnapshotStore(self.cfg.snapshot_dir)

    def _q(self, **p):
        base = dict(action="query", format="json", formatversion="2", maxlag="5", redirects="1")
        base.update(p)
        body, meta = self.client.get(API, base)
        d = json.loads(body)
        if "error" in d and d["error"].get("code") == "maxlag":
            raise RuntimeError("maxlag: servers busy, retry later")
        return d, body, meta

    def revision_older_than(self, title: str, hours: float = 24.0, now: Optional[datetime] = None):
        """Newest revision at least `hours` old (stability rule) -> (revid, timestamp)."""
        now = now or datetime.now(timezone.utc)
        d, _, _ = self._q(prop="revisions", rvprop="ids|timestamp", rvlimit="50", titles=title)
        for rev in d["query"]["pages"][0].get("revisions", []):
            ts = datetime.fromisoformat(rev["timestamp"].replace("Z", "+00:00"))
            if ts <= now - timedelta(hours=hours):
                return rev["revid"], rev["timestamp"]
        raise LookupError(f"no revision of {title} older than {hours} h among the last 50")

    def fetch_revision(self, title: str, revid: int):
        if title not in REGISTRY:
            raise ValueError(f"{title} is not in the reviewed page registry")
        d, body, meta = self._q(prop="revisions", rvprop="content|ids|timestamp", rvslots="main", revids=str(revid))
        page = d["query"]["pages"][0]
        rev = page["revisions"][0]
        info = self.store.save(SOURCE, f"{title}_{rev['revid']}", body, dict(meta, source=SOURCE, licence=LICENCE, title=title, revid=rev["revid"]))
        recs, pm = parse_wikitext(rev["slots"]["main"]["content"], title, rev["revid"], rev["timestamp"], info["saved_utc"], info["snapshot_id"])
        return recs, pm, info
