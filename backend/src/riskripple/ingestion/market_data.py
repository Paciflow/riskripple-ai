"""Market data ingestion: adjusted-close price history for the investment universe.

Live provider: Yahoo Finance's public chart endpoint (query1.finance.yahoo.com). This is
an unofficial, undocumented API with no SLA, no published terms for programmatic access,
and real rate limits (observed HTTP 429 under bursty requests with a generic client
User-Agent). It is used here read-only, for historical price retrieval, at low request
volume with backoff -- not for redistribution or commercial use. Document this caveat
wherever this provider is referenced (see docs/DATA_SOURCES.md).

For the reproducible datathon demo, do not call this live during a presentation: use
SnapshotMarketDataProvider against the frozen CSVs in data/fixtures/market/, built once by
scripts/build_demo_snapshot.py and committed to the repo.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

from riskripple.schemas.provenance import SourceMetadata

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
# Generic, non-identifying client label -- this is a public, unauthenticated, undocumented
# endpoint; there is no vendor-assigned contact string to supply here.
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-script/1.0)"}


class MarketDataError(RuntimeError):
    pass


@dataclass
class PriceHistoryResult:
    symbol: str
    prices: pd.DataFrame  # columns: date (index, DatetimeIndex), close, adj_close
    metadata: SourceMetadata


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fetch_price_history_yahoo(
    symbol: str,
    *,
    range_: str = "2y",
    interval: str = "1d",
    max_retries: int = 3,
    backoff_seconds: float = 2.0,
    client: httpx.Client | None = None,
) -> PriceHistoryResult:
    """Fetch adjusted-close daily price history for one symbol.

    Raises MarketDataError on anything other than a 200 after retries, rather than
    silently returning partial or unadjusted data.
    """
    own_client = client is None
    client = client or httpx.Client(timeout=15.0, headers=_HEADERS)
    url = YAHOO_CHART_URL.format(symbol=symbol)
    params = {"range": range_, "interval": interval}

    last_error: Exception | None = None
    try:
        for attempt in range(max_retries):
            try:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    break
                last_error = MarketDataError(f"{symbol}: HTTP {resp.status_code} from Yahoo chart API")
            except httpx.HTTPError as exc:
                last_error = exc
            time.sleep(backoff_seconds * (attempt + 1))
        else:
            raise last_error or MarketDataError(f"{symbol}: unknown fetch failure")
    finally:
        if own_client:
            client.close()

    raw = resp.content
    payload = resp.json()
    result = payload.get("chart", {}).get("result")
    if not result:
        raise MarketDataError(f"{symbol}: empty chart result (symbol may be invalid or delisted)")

    r = result[0]
    meta = r["meta"]
    timestamps = r.get("timestamp")
    if not timestamps:
        raise MarketDataError(f"{symbol}: no price observations returned")

    quote = r["indicators"]["quote"][0]
    adjclose = r["indicators"].get("adjclose", [{}])[0].get("adjclose")
    if adjclose is None:
        raise MarketDataError(
            f"{symbol}: no adjusted-close series in response; refusing to silently "
            "substitute unadjusted close"
        )

    df = pd.DataFrame(
        {
            "close": quote["close"],
            "adj_close": adjclose,
        },
        index=pd.to_datetime(timestamps, unit="s", utc=True).tz_convert(meta["exchangeTimezoneName"]).normalize().tz_localize(None),
    )
    df.index.name = "date"
    df = df.dropna(how="any")

    source_metadata = SourceMetadata(
        source_name="Yahoo Finance (query1.finance.yahoo.com chart API)",
        source_url=resp.url.__str__(),
        retrieved_at=datetime.now(timezone.utc),
        observation_date=df.index.max().date(),
        currency=meta.get("currency"),
        data_version=_sha256(raw)[:16],
        content_hash=_sha256(raw),
        license_or_restriction=(
            "Unofficial public endpoint, no documented SLA or terms for programmatic "
            "access; rate-limited (HTTP 429 observed under bursty requests). "
            "Read-only historical retrieval; not for redistribution."
        ),
    )
    return PriceHistoryResult(symbol=symbol, prices=df, metadata=source_metadata)


class SnapshotMarketDataProvider:
    """Reads a previously-frozen snapshot from disk instead of calling a live API.

    This is the default provider for the datathon demo: reproducible even if Yahoo
    Finance is unreachable, rate-limiting, or has changed its response shape live
    during a presentation.
    """

    def __init__(self, snapshot_dir: Path | str):
        self.snapshot_dir = Path(snapshot_dir)

    def load(self, symbol: str) -> PriceHistoryResult:
        price_path = self.snapshot_dir / f"{symbol}.csv"
        meta_path = self.snapshot_dir / f"{symbol}.metadata.json"
        if not price_path.exists() or not meta_path.exists():
            raise MarketDataError(
                f"no snapshot for {symbol} in {self.snapshot_dir}; run "
                "scripts/build_demo_snapshot.py first"
            )
        df = pd.read_csv(price_path, parse_dates=["date"], index_col="date")
        metadata = SourceMetadata.model_validate_json(meta_path.read_text())
        return PriceHistoryResult(symbol=symbol, prices=df, metadata=metadata)


def save_snapshot(result: PriceHistoryResult, snapshot_dir: Path | str) -> None:
    snapshot_dir = Path(snapshot_dir)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    result.prices.to_csv(snapshot_dir / f"{result.symbol}.csv")
    (snapshot_dir / f"{result.symbol}.metadata.json").write_text(
        result.metadata.model_dump_json(indent=2)
    )
