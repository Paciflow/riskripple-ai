# Ingestion Pipeline

How real data gets from a public source into this system. See
`docs/DATA_SOURCES.md` for the list of sources with URLs/licenses, and
`docs/KNOWN_LIMITATIONS.md` for what's rough-edged about each adapter. This doc is
about the *pipeline mechanics* — how a source becomes a frozen, provenance-tagged
fixture.

## The pattern: fetch once, freeze, hash

Every adapter in `backend/src/riskripple/ingestion/` follows the same shape:

```
fetch_X(...) -> (data, SourceMetadata)
```

`SourceMetadata` (`backend/src/riskripple/schemas/provenance.py`) is mandatory, not
optional, on every ingested dataset:

```python
class SourceMetadata(BaseModel):
    source_name: str
    source_url: str
    retrieved_at: datetime
    observation_date: date | None
    publication_date: date | None
    currency: str | None
    data_version: str
    content_hash: str
    license_or_restriction: str
```

`scripts/build_demo_snapshot.py` calls every adapter once, writes the result under
`data/fixtures/`, and writes a `manifest.json` recording the content hash and row
count of everything it pulled. This is the only ingestion that runs before the
demo — nothing in the demo path calls a live source at presentation time (see
`docs/TRADEOFFS.md` for why: Yahoo Finance's unofficial API returned HTTP 429 under
bursty requests during development, which is an unacceptable risk live in front of
judges).

```bash
python3 scripts/build_demo_snapshot.py
```

Re-running it refreshes every fixture and recomputes every hash — the snapshot is
fully reproducible from source, not hand-maintained.

## Adapters

| Adapter | Source | What it is |
|---|---|---|
| `market_data.fetch_price_history_yahoo` | Yahoo Finance chart API (unofficial, undocumented) | Daily close/adj_close for the 8-asset demo universe (SPY, QQQ, AGG, GLD, BIL, NVDA, AMD, INTC). |
| `sanctions_ofac.fetch_sdn_list` | OFAC Specially Designated Nationals CSV (`sanctionslistservice.ofac.treas.gov`) | ~19,500 rows, classic 12-column SDN schema. |
| `sanctions_gac.fetch_consolidated_list` | Global Affairs Canada consolidated sanctions XML (bilingual export) | ~5,800 entity/individual records. |
| `macro_fred.fetch_series` | FRED `fredgraph.csv` endpoint (no API key required) | Treasury yield series (10Y, 3M) used for risk-free-rate context. |
| `filings_sec.fetch_company_submissions` / `fetch_filing_text` | SEC EDGAR `data.sec.gov/submissions` + `sec.gov/Archives` | Filing index + up to 200,000 characters of extracted 10-K text (HTML stripped via BeautifulSoup/lxml). Requires an identifying `User-Agent` per SEC's fair-access policy — see the contact-placeholder note below. |
| `regulatory_events.search_documents` | Federal Register API (`federalregister.gov/api/v1`) | BIS (Bureau of Industry and Security) export-control documents, filtered to the semiconductor/advanced-computing topic area used in the demo scenario. |

## A real compliance gap, left visible rather than fixed with a placeholder

`filings_sec.py` and `regulatory_events.py` both send an identifying contact string
in their request headers, as SEC's and (implicitly) Federal Register's fair-access
expectations call for. Right now that contact is a placeholder
(`SEC_EDGAR_CONTACT` env var, defaulting to a fictional address), because this is
development/testing volume, not production ingestion. **This must be set to a real
team contact — never a personal email — via the environment variable before any
ingestion volume beyond light testing.** It's called out here and in
`docs/SECURITY.md` and `docs/KNOWN_LIMITATIONS.md` on purpose: a fake contact string
is a genuine compliance gap, not a cosmetic one, and leaving three separate honest
flags for it beats hiding it behind a plausible-looking default.

## Known truncation, by design, not oversight

`fetch_filing_text` caps extracted text at 200,000 characters per filing. Real
10-Ks run longer than that, and the extracted text includes a block of raw XBRL tag
soup before the readable narrative sections. This was confirmed to work well enough
for retrieval in practice (real queries against the real NVDA/AMD/INTC filings
correctly surface the actual risk-factor paragraphs — see `docs/EVALUATION.md`), but
a production version should skip to Item 1/Item 1A before chunking rather than
truncating by raw character count. Not fixed yet because the current truncation
point hasn't caused a single observed retrieval miss in testing; flagged here so
it doesn't get mistaken for an oversight if it does.

## What's NOT covered by this pipeline

- No ingestion of news/social sentiment data — out of scope for this build; the
  regulatory/sanctions/filing sources above were judged more defensible for
  evidence-grounded citations than scraped news (see `docs/DATA_SOURCES.md` for the
  GDELT evaluation-and-rejection reasoning).
- No incremental/delta ingestion — every run of `build_demo_snapshot.py` re-fetches
  everything from scratch. Fine at this data volume; would need pagination/delta
  logic at real production scale (especially for OFAC/GAC, which are full-list
  exports, not deltas).
- The EventBridge-scheduled ingestion Lambda (`api/handlers/ingest.py`,
  `infrastructure/cdk/lib/ingestion-stack.ts`) exists and is written against this
  same adapter layer, but has never run in AWS — see `docs/KNOWN_LIMITATIONS.md`.
