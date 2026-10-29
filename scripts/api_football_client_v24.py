#!/usr/bin/env python3
"""Small API-Football client for model v2.4.

The client is intentionally boring:
- reads the API key from .env
- never logs the key
- caches JSON responses
- tracks requests against a daily budget
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
CACHE_ROOT = ROOT / "data" / "provider_cache" / "api_football"
LEDGER_PATH = CACHE_ROOT / "request_ledger.jsonl"
BASE_URL = "https://v3.football.api-sports.io"
LOCAL_TZ = ZoneInfo("America/New_York")


class APIFootballError(RuntimeError):
    """Base error for provider failures."""


class MissingAPIKeyError(APIFootballError):
    """Raised when API_FOOTBALL_KEY is unavailable."""


class RequestBudgetError(APIFootballError):
    """Raised when the local request budget would be exceeded."""


@dataclass
class ProviderResult:
    endpoint: str
    params: dict[str, Any]
    data: dict[str, Any]
    cache_hit: bool
    request_counted: bool
    cache_path: Path

    @property
    def response_rows(self) -> list[Any]:
        response = self.data.get("response", [])
        return response if isinstance(response, list) else []


def load_dotenv(path: Path = ENV_PATH) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get_api_key() -> str:
    key = os.environ.get("API_FOOTBALL_KEY") or load_dotenv().get("API_FOOTBALL_KEY", "")
    key = key.strip()
    if not key:
        raise MissingAPIKeyError("API_FOOTBALL_KEY is missing. Add it to .env before provider fetches.")
    return key


def today_key() -> str:
    return datetime.now(LOCAL_TZ).date().isoformat()


def stable_cache_key(endpoint: str, params: dict[str, Any]) -> str:
    payload = json.dumps({"endpoint": endpoint, "params": params}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def cache_path(endpoint: str, params: dict[str, Any]) -> Path:
    safe_endpoint = endpoint.strip("/").replace("/", "__")
    return CACHE_ROOT / safe_endpoint / f"{stable_cache_key(endpoint, params)}.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def cache_is_fresh(path: Path, ttl_hours: float) -> bool:
    if not path.exists():
        return False
    if ttl_hours <= 0:
        return False
    age_seconds = time.time() - path.stat().st_mtime
    return age_seconds <= ttl_hours * 3600


def api_error_text(payload: dict[str, Any]) -> str:
    errors = payload.get("errors")
    if not errors:
        return ""
    if isinstance(errors, dict):
        return "; ".join(f"{key}: {value}" for key, value in errors.items())
    if isinstance(errors, list):
        return "; ".join(str(item) for item in errors)
    return str(errors)


def api_rate_limited(payload: dict[str, Any]) -> bool:
    errors = payload.get("errors")
    return isinstance(errors, dict) and bool(errors.get("rateLimit"))


def iter_ledger_rows() -> list[dict[str, Any]]:
    if not LEDGER_PATH.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def requests_used_today(date_key: str | None = None) -> int:
    date_key = date_key or today_key()
    return sum(1 for row in iter_ledger_rows() if row.get("date") == date_key and row.get("request_counted"))


def append_ledger(row: dict[str, Any]) -> None:
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    with LEDGER_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def provider_get(
    endpoint: str,
    params: dict[str, Any] | None = None,
    *,
    ttl_hours: float = 6.0,
    force_refresh: bool = False,
    daily_limit: int = 100,
    reserve_requests: int = 15,
    timeout_seconds: int = 20,
) -> ProviderResult:
    params = {key: value for key, value in (params or {}).items() if value not in ("", None)}
    endpoint = endpoint.strip("/")
    path = cache_path(endpoint, params)
    if not force_refresh and cache_is_fresh(path, ttl_hours):
        cached = read_json(path)
        if not api_rate_limited(cached.get("data", {})):
            return ProviderResult(endpoint, params, cached["data"], True, False, path)

    used = requests_used_today()
    usable_limit = max(0, daily_limit - reserve_requests)
    if used >= usable_limit:
        raise RequestBudgetError(
            f"Local API-Football budget reached: {used}/{daily_limit} used with {reserve_requests} reserved."
        )

    key = get_api_key()
    query = urllib.parse.urlencode(params, doseq=True)
    url = f"{BASE_URL}/{endpoint}"
    if query:
        url = f"{url}?{query}"
    request = urllib.request.Request(url, headers={"x-apisports-key": key})

    started = datetime.now(LOCAL_TZ).isoformat()
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                status_code = response.status
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 429 and attempt == 0:
                time.sleep(65)
                started = datetime.now(LOCAL_TZ).isoformat()
                continue
            raise APIFootballError(f"API-Football HTTP {exc.code} on /{endpoint}: {body[:500]}") from exc
        except urllib.error.URLError as exc:
            raise APIFootballError(f"API-Football network error on /{endpoint}: {exc.reason}") from exc

        if api_rate_limited(payload) and attempt == 0:
            time.sleep(65)
            started = datetime.now(LOCAL_TZ).isoformat()
            continue
        break

    error_text = api_error_text(payload)
    if error_text and not payload.get("response"):
        raise APIFootballError(f"API-Football error on /{endpoint}: {error_text}")

    wrapped = {
        "fetched_at": started,
        "endpoint": endpoint,
        "params": params,
        "data": payload,
    }
    write_json(path, wrapped)
    append_ledger(
        {
            "date": today_key(),
            "timestamp": started,
            "endpoint": endpoint,
            "params": params,
            "cache_key": path.stem,
            "cache_path": str(path.relative_to(ROOT)),
            "request_counted": True,
            "status_code": status_code,
            "response_count": len(payload.get("response", [])) if isinstance(payload.get("response"), list) else "",
        }
    )
    return ProviderResult(endpoint, params, payload, False, True, path)


def budget_snapshot(daily_limit: int = 100, reserve_requests: int = 15) -> dict[str, Any]:
    used = requests_used_today()
    usable = max(0, daily_limit - reserve_requests)
    return {
        "date": today_key(),
        "daily_limit": daily_limit,
        "reserve_requests": reserve_requests,
        "usable_before_stop": usable,
        "used_today": used,
        "remaining_before_stop": max(0, usable - used),
    }
