# Data Sources

Every source below was actually queried (not assumed) while building this project.
Each entry states what was verified, when, and what the known caveats are.

## OFAC Specially Designated Nationals (SDN) List

- **URL:** https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV
  (the URL named in the challenge, `ofac.treasury.gov/sanctions-list-service`,
  redirects here)
- **Format:** CSV, classic 12-column SDN schema (`ent_num, sdn_name, sdn_type,
  program, title, call_sign, vess_type, tonnage, grt, vess_flag, vess_owner, remarks`)
- **Verified:** 19,563 records fetched successfully (2026-11-10)
- **License:** U.S. government public data; official sanctions screening source
- **Caveat:** used for structured name/program screening only, never as a sole
  determination of sanctioned status (see `tools/regulatory_tools.search_sanctions_records`)

## Global Affairs Canada — Consolidated Autonomous Sanctions List

- **Source page:** https://www.international.gc.ca/world-monde/international_relations-relations_internationales/sanctions/consolidated-consolide.aspx?lang=eng
- **Structured data file:** https://www.international.gc.ca/world-monde/assets/office_docs/international_relations-relations_internationales/sanctions/sema-lmes.xml
- **Format:** bilingual XML (`Country-Pays`, `LastName-NomDeFamille`,
  `Schedule-Annexe`, `DateOfListing-DateDinscription`, etc.)
- **Verified:** 5,781 records fetched successfully (2026-11-10)
- **License:** Government of Canada open data
- **Caveat:** informational screening source, not a complete substitute for the
  applicable regulations

## Federal Register API (Bureau of Industry and Security)

- **URL:** https://www.federalregister.gov/api/v1/documents.json
- **Format:** JSON, filterable by agency slug and keyword
- **Verified:** querying `term=semiconductor export`,
  `agencies[]=industry-and-security-bureau` returns real, current results
  ("Additions and Revisions to the Entity List," "Revision to License Review
  Policy for Advanced Computing Commodities," etc.)
- **License:** U.S. government public domain
- **Why this over GDELT:** GDELT was evaluated and rejected for the current scope
  — it rate-limits aggressively (HTTP 429 under light testing) and its schema is
  much noisier; Federal Register gives official, citable, dated government
  actions directly on-topic for the demo scenario.

## FRED (Federal Reserve Economic Data)

- **URL:** https://fred.stlouisfed.org/graph/fredgraph.csv?id=\<series\>
- **Format:** 2-column CSV (`observation_date`, value), no API key required
- **Series used:** `DGS10` (10-year Treasury), `DGS3MO` (3-month Treasury)
- **Verified:** 16,199 and 11,297 observations respectively (2026-11-10)
- **License:** public domain / free with attribution per FRED's terms

## SEC EDGAR

- **Company index:** https://data.sec.gov/submissions/CIK\<10-digit\>.json
- **Filing documents:** https://www.sec.gov/Archives/edgar/data/\<cik\>/\<accession-no-dashes\>/\<document\>
- **Format:** JSON index + HTML/iXBRL filing documents
- **Verified:** real 10-K filings fetched for NVIDIA (CIK 0001045810), AMD (CIK
  0000002488), and Intel (CIK 0000050863) — NVIDIA's actual contains literal
  export-control risk-factor language (A100/H100, China restrictions) used
  directly in the RAG demo
- **Requires:** an identifying `User-Agent` per SEC's fair-access policy. Currently
  a placeholder (`SEC_EDGAR_CONTACT` env var) — **replace with a real team contact
  before any ingestion volume beyond light testing.**
- **License:** U.S. public filings

## Yahoo Finance (chart API)

- **URL:** https://query1.finance.yahoo.com/v8/finance/chart/\<symbol\>
- **Format:** JSON, includes adjusted-close series
- **Verified:** 2-year daily history for SPY, QQQ, AGG, GLD, BIL, NVDA, AMD, INTC
- **Caveat:** unofficial, undocumented endpoint with no published SLA or terms for
  programmatic access. Observed HTTP 429 under bursty requests with a generic
  User-Agent; a short delay between requests resolved it. **The demo deliberately
  runs off the frozen snapshot, not live calls, for this reason.**
- **Rejected alternative:** Stooq, which returns a JavaScript proof-of-work
  challenge to automated clients and cannot be scraped without a headless browser.

## Investment universe (demo)

SPY (broad market), QQQ (tech-heavy Nasdaq-100), AGG (broad bond), GLD (gold), BIL
(T-bill cash proxy), NVDA/AMD/INTC (semiconductor equities for direct exposure to
the export-restriction scenario). All labeled fictional in the UI; the $100,000
starting value is a simulation input, not a real account.
