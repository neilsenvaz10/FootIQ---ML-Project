"""Shared building blocks for the FootIQ results-source adapters (standard library only).

Design rules enforced here
  * Live access is OFF unless config/adapters.json has live_enabled=true AND a real contact string (required by the OpenLigaDB terms and the Wikimedia User-Agent policy).
  * Every response is stored as an immutable raw snapshot (read-only file + sha256 + request metadata) and never overwritten.
  * Requests are rate limited with jitter, retried with exponential back-off on 429/5xx/network errors (Retry-After honoured), and written to a request ledger.
  * Staging records are source-independent; they never touch the frozen training data or the model artifacts.
"""
import dataclasses
import hashlib
import json
import os
import random
import stat
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONFIG_PATH = os.path.join(ROOT, "config", "adapters.json")
ADAPTER_VERSION = "1.0.0"


class LiveAccessDenied(RuntimeError):
    """Raised when a live request is attempted without enabled config / contact string."""


class SourceUnavailable(RuntimeError):
    """Raised when retries are exhausted."""


@dataclass
class AdapterConfig:
    live_enabled: bool = False
    contact: Optional[str] = field(default=None, repr=False)   # never stored in adapters.json, never printed/logged; comes from env FOOTIQ_CONTACT or config/contact.local
    app_name: str = "FootIQ-ResultsAdapters"
    snapshot_dir: str = os.path.join(ROOT, "snapshots")
    ledger_path: str = os.path.join(ROOT, "snapshots", "request_ledger.jsonl")

    @staticmethod
    def load(path: str = CONFIG_PATH, contact_file: Optional[str] = None) -> "AdapterConfig":
        """Settings come from adapters.json (any 'contact' key there is IGNORED so personal data cannot sit in tracked configuration);
        the contact comes from env FOOTIQ_CONTACT or the untracked config/contact.local file."""
        raw = {}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                raw = json.load(fh)
        raw.pop("contact", None)
        cfg = AdapterConfig(**{k: v for k, v in raw.items() if k in AdapterConfig.__dataclass_fields__})
        cf = contact_file or os.environ.get("FOOTIQ_CONTACT_FILE") or os.path.join(os.path.dirname(path), "contact.local")
        env = os.environ.get("FOOTIQ_CONTACT", "").strip()
        if env:
            cfg.contact = env
        elif os.path.exists(cf):
            with open(cf, encoding="utf-8") as fh:
                cfg.contact = fh.read().strip() or None
        return cfg

    def contact_configured(self) -> bool:
        c = (self.contact or "").strip()
        return bool(c) and "example" not in c.lower() and c.lower() not in ("none", "todo", "withheld")

    def redact(self, text: str) -> str:
        """Remove the contact string from any text before it is printed or stored."""
        c = (self.contact or "").strip()
        out = text
        if c:
            out = out.replace(c, "[contact-redacted]")
            for part in c.replace("mailto:", "").split():
                if len(part) > 5:
                    out = out.replace(part, "[contact-redacted]")
        return out

    def user_agent(self, source: str) -> str:
        if not self.contact_configured():
            raise LiveAccessDenied("no real contact configured: set env FOOTIQ_CONTACT or create config/contact.local (required by the source terms)")
        c = self.contact.strip()
        return f"{self.app_name}-{source}Bot/{ADAPTER_VERSION} (+local research project; {c})"


@dataclass
class StagingRecord:
    """One match as reported by one source. Dates/times keep their provenance; nothing is guessed."""
    source: str
    source_ref: str                          # e.g. OpenLigaDB matchID, "<page>@<revid>:<cell>"
    competition_key: str                     # source-side competition identifier (league shortcut / page title)
    season: str
    stage: Optional[str]
    round: Optional[str]
    home_raw: str
    away_raw: str
    status: str                              # completed | completed_unclassified_score | upcoming | past_date_no_result | postponed | cancelled | abandoned | awarded | unresolved
    kickoff_utc: Optional[str]               # ISO UTC, only when the source states it
    kickoff_local: Optional[str]
    time_zone: Optional[str]
    time_precision: str                      # utc | local_with_zone | date_only | none | inherited_date
    match_date: Optional[str]                # YYYY-MM-DD
    date_provenance: str                     # source_stated | inherited_from_openfootball_schedule | none
    regulation_home: Optional[int]
    regulation_away: Optional[int]
    result_type: str                         # after90_explicit | after_et | after_pens | unclassified_final | wikipedia_matrix_unspecified | none
    label_eligible_90min: bool               # may serve as confirmed 90-minute 1X2 label
    source_ids: dict = field(default_factory=dict)
    retrieved_utc: str = ""
    source_revision: str = ""                # Wikipedia revid / API lastUpdateDateTime / git commit
    snapshot_id: str = ""
    licence: str = ""
    attribution: str = ""
    flags: list = field(default_factory=list)

    def to_dict(self):
        return dataclasses.asdict(self)


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class SnapshotStore:
    """Write-once raw snapshots: <dir>/<source>/<UTC>_<name>.<ext> + .meta.json (both read-only)."""

    def __init__(self, base: str):
        self.base = base

    def save(self, source: str, name: str, payload: bytes, meta: dict, ext: str = "json") -> dict:
        d = os.path.join(self.base, source)
        os.makedirs(d, exist_ok=True)
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
        path = os.path.join(d, f"{stamp}_{safe}.{ext}")
        n = 1
        while os.path.exists(path):                       # never overwrite
            n += 1
            path = os.path.join(d, f"{stamp}_{safe}_{n}.{ext}")
        with open(path, "wb") as fh:
            fh.write(payload)
        info = dict(meta, snapshot_id=os.path.basename(path), sha256=sha256_bytes(payload), bytes=len(payload), saved_utc=utc_now(), adapter_version=ADAPTER_VERSION)
        with open(path + ".meta.json", "w", encoding="utf-8") as fh:
            json.dump(info, fh, indent=1)
        os.chmod(path, stat.S_IREAD)
        os.chmod(path + ".meta.json", stat.S_IREAD)
        return info


class HttpClient:
    """Polite GET client. `opener` is injectable so tests never touch the network."""

    def __init__(self, cfg: AdapterConfig, source: str, min_interval_s: float, max_retries: int = 4, jitter_s: float = 1.0, opener: Optional[Callable] = None, sleep: Callable = time.sleep):
        self.cfg, self.source, self.min_interval, self.max_retries, self.jitter = cfg, source, min_interval_s, max_retries, jitter_s
        self._opener, self._sleep, self._last = opener, sleep, 0.0

    def _ledger(self, rec: dict):
        os.makedirs(os.path.dirname(self.cfg.ledger_path), exist_ok=True)
        with open(self.cfg.ledger_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")

    def get(self, url: str, params: Optional[dict] = None, headers: Optional[dict] = None) -> tuple:
        if not self.cfg.live_enabled:
            raise LiveAccessDenied("live access disabled in config (live_enabled=false)")
        ua = self.cfg.user_agent(self.source)
        full = url + ("?" + urllib.parse.urlencode(params) if params else "")
        delay = 0.0
        for attempt in range(self.max_retries + 1):
            wait = self.min_interval + random.uniform(0, self.jitter) - (time.time() - self._last)
            if wait > 0 or delay > 0:
                self._sleep(max(wait, delay, 0))
            self._last = time.time()
            status, body, hdrs = None, b"", {}
            try:
                if self._opener:
                    status, body, hdrs = self._opener(full, dict(headers or {}, **{"User-Agent": ua, "Accept-Encoding": "identity"}))
                else:
                    req = urllib.request.Request(full, headers=dict(headers or {}, **{"User-Agent": ua}))
                    with urllib.request.urlopen(req, timeout=60) as r:
                        status, body, hdrs = r.status, r.read(), dict(r.headers)
            except urllib.error.HTTPError as e:
                status, hdrs = e.code, dict(e.headers or {})
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                status = None
            self._ledger(dict(ts=utc_now(), source=self.source, url=full, status=status, attempt=attempt))
            if status == 200:
                return body, dict(url=full, status=status, retrieved_utc=utc_now(), headers={k: v for k, v in hdrs.items() if k.lower() in ("etag", "last-modified", "date", "content-type")})
            if status in (429, 500, 502, 503, 504, None):
                ra = hdrs.get("Retry-After") if hdrs else None
                delay = float(ra) if ra and str(ra).isdigit() else min(2 ** (attempt + 1) * 5, 300)
                continue
            raise SourceUnavailable(f"{full} -> HTTP {status} (not retried)")
        raise SourceUnavailable(f"{full}: retries exhausted")
