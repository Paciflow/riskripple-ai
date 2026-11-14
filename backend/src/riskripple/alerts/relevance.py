"""Deterministic relevance check: does a new regulatory/export-control document
connect to a tracked portfolio, directly (names a held company) or indirectly
(names a known supplier already present in that portfolio's real exposure graph)?

Reuses the exact same literal-keyword-match methodology as
`graph.company_graph.extract_supplier_edges_from_filing_text` -- a document is only
ever "relevant" because a real name was found in its text, never because it shares a
sector or an LLM judged it similar. The one correction versus that existing
function: here we use word-boundary matching (`\\bIntel\\b`), not a bare substring
check, because this module's alias set includes short company names ("Intel") that
are also substrings of unrelated words ("Artificial Intelligence") -- confirmed by
testing against the real Federal Register fixture, where naive substring matching
produced 3 false positives out of 5 "Intel" hits before this fix.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from riskripple.graph.company_graph import KNOWN_SUPPLIER_ALIASES
from riskripple.tools.exposure_tools import KNOWN_COMPANY_NAMES

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# KNOWN_COMPANY_NAMES (exposure_tools.py) maps a ticker to its full legal name
# ("NVIDIA Corporation"), tuned for fuzzy-matching user input -- but real
# regulatory text uses short brand names ("Nvidia H200") or subsidiary names
# ("Intel Semiconductor (Dalian) Ltd"), not the full legal name. This is a
# separate, explicit seed list for literal matching against external document
# text, same spirit as KNOWN_SUPPLIER_ALIASES: a small curated list, not NER.
PORTFOLIO_COMPANY_ALIASES: dict[str, list[str]] = {
    "NVDA": ["NVIDIA", "NVDA"],
    "AMD": ["Advanced Micro Devices", "AMD"],
    "INTC": ["Intel", "INTC"],
}


@dataclass
class RelevanceMatch:
    symbol: str  # the portfolio holding this match is relevant to
    relationship: str  # "direct" | "supply_chain"
    node_id: str  # the canonical exposure-graph node that matched (== symbol for "direct")
    matched_entity: str  # the literal alias text actually found in the document
    evidence_snippet: str


def _word_match(alias: str, text: str) -> re.Match | None:
    return re.search(rf"\b{re.escape(alias)}\b", text, re.IGNORECASE)


def _sentence_containing(text: str, match: re.Match) -> str:
    # Split on blank lines first (title vs. abstract are joined with "\n\n" by
    # callers) so an untitled, punctuation-less title never bleeds into the first
    # sentence of the abstract -- confirmed necessary: without this, a match deep in
    # the abstract returned a snippet starting from the title.
    for paragraph in text.split("\n\n"):
        if match.group(0).lower() not in paragraph.lower():
            continue
        for sentence in _SENTENCE_SPLIT_RE.split(paragraph):
            if match.group(0).lower() in sentence.lower():
                return sentence.strip()
    return text[max(0, match.start() - 80) : match.end() + 80].strip()


def _aliases_for_node(node_id: str) -> list[str]:
    if node_id in PORTFOLIO_COMPANY_ALIASES:
        return PORTFOLIO_COMPANY_ALIASES[node_id]
    if node_id in KNOWN_COMPANY_NAMES:
        return [node_id, KNOWN_COMPANY_NAMES[node_id]]
    if node_id in KNOWN_SUPPLIER_ALIASES:
        return KNOWN_SUPPLIER_ALIASES[node_id]
    return [node_id]


def check_relevance(document_text: str, graph_json: dict, portfolio_symbols: list[str]) -> list[RelevanceMatch]:
    """`graph_json` is the output of `tools.exposure_tools.load_company_graph` for
    this portfolio -- the real graph built from literal keyword matches in the
    actual held companies' 10-K filings, not a new/separate relationship model.
    """
    portfolio_set = set(portfolio_symbols)
    matches: list[RelevanceMatch] = []
    seen: set[tuple[str, str]] = set()

    for node in graph_json.get("nodes", []):
        node_id = node["id"]
        hit = None
        matched_alias = None
        for alias in _aliases_for_node(node_id):
            hit = _word_match(alias, document_text)
            if hit:
                matched_alias = alias
                break
        if not hit:
            continue

        if node_id in portfolio_set:
            key = (node_id, "direct")
            if key not in seen:
                seen.add(key)
                matches.append(
                    RelevanceMatch(
                        symbol=node_id,
                        relationship="direct",
                        node_id=node_id,
                        matched_entity=matched_alias,
                        evidence_snippet=_sentence_containing(document_text, hit),
                    )
                )
        else:
            # Not a portfolio symbol itself -- a supplier node. Find which held
            # companies have a real, extracted edge pointing to it.
            for edge in graph_json.get("edges", []):
                if edge["target"] == node_id and edge["source"] in portfolio_set:
                    key = (edge["source"], "supply_chain")
                    if key in seen:
                        continue
                    seen.add(key)
                    matches.append(
                        RelevanceMatch(
                            symbol=edge["source"],
                            relationship="supply_chain",
                            node_id=node_id,
                            matched_entity=matched_alias,
                            evidence_snippet=_sentence_containing(document_text, hit),
                        )
                    )
    return matches
