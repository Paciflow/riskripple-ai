"""RAG retrieval evaluation benchmark (master spec section 16.2).

Builds a corpus from the real demo fixtures (3 SEC 10-K filings + 20 real Federal
Register BIS documents), runs a hand-written set of grounded queries against
`LocalLexicalRetriever`, and reports retrieval quality metrics.

Every query below is grounded in content actually present in the fixtures — found by
grepping the real filing text and reading the real Federal Register abstracts, not
invented. Expected answers were verified against the source documents at write time;
see each `EvalCase.note` for how.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from riskripple.rag.chunking import DocumentChunk, chunk_document
from riskripple.rag.retrieval import LocalLexicalRetriever, RetrievedChunk


@dataclass(frozen=True)
class EvalCase:
    query: str
    expected_document_ids: frozenset[str]
    category: str
    note: str
    metadata_filter: dict | None = None
    required_keyword: str | None = None  # case-insensitive substring the top hit's text must contain


def build_corpus(fixtures_dir: Path) -> list[DocumentChunk]:
    """Chunks the 3 demo 10-Ks and the 20 real Federal Register BIS documents."""
    chunks: list[DocumentChunk] = []

    filings_dir = fixtures_dir / "filings"
    for symbol in ("NVDA", "AMD", "INTC"):
        text = (filings_dir / f"{symbol}_10K.txt").read_text(encoding="utf-8")
        metadata = json.loads((filings_dir / f"{symbol}_10K.metadata.json").read_text(encoding="utf-8"))
        chunks.extend(
            chunk_document(
                document_id=f"{symbol}_10K",
                text=text,
                title=f"{symbol} 10-K ({metadata.get('publication_date', 'n/a')})",
                source_url=metadata.get("source_url"),
            )
        )

    regulatory_path = fixtures_dir / "regulatory" / "federal_register_bis_semiconductor.json"
    documents = json.loads(regulatory_path.read_text(encoding="utf-8"))
    for doc in documents:
        body = doc.get("title", "") + "\n\n" + doc.get("abstract", "")
        chunks.extend(
            chunk_document(
                document_id=doc["document_number"],
                text=body,
                title=doc.get("title"),
                source_url=doc.get("document_url"),
            )
        )

    return chunks


# --- Category 1: unique Federal Register documents (unscoped retrieval) ---------
_UNIQUE_FR_CASES = [
    EvalCase(
        "removing United Arab Emirates from stricter export control country group",
        frozenset({"2026-14132"}), "federal_register_unique",
        "Title: 'Enhanced Favorable Treatment for the United Arab Emirates...'",
    ),
    EvalCase(
        "changes to license review policy for advanced computing commodities",
        frozenset({"2026-00789"}), "federal_register_unique",
        "Title: 'Revision to License Review Policy for Advanced Computing Commodities'",
    ),
    EvalCase(
        "revoking validated end-user authorizations in China",
        frozenset({"2025-16735"}), "federal_register_unique",
        "Title: 'Revocation of Validated End-User Authorizations in the People's Republic of China'",
    ),
    EvalCase(
        "national security investigation into semiconductor imports under Section 232",
        frozenset({"2025-06591"}), "federal_register_unique",
        "Title mentions 'Section 232 National Security Investigation of Imports of Semiconductors'",
    ),
    EvalCase(
        "additional due diligence requirements for advanced computing integrated circuits",
        frozenset({"2025-00711"}), "federal_register_unique",
        "Title: 'Implementation of Additional Due Diligence Measures for Advanced Computing Integrated Circuits'",
    ),
    EvalCase(
        "information and communications technology supply chain security for connected vehicles",
        frozenset({"2025-00592"}), "federal_register_unique",
        "Title: 'Securing the ICTS Supply Chain: Connected Vehicles'",
    ),
    EvalCase(
        "framework governing artificial intelligence chip diffusion exports",
        frozenset({"2025-00636"}), "federal_register_unique",
        "Title: 'Framework for Artificial Intelligence Diffusion'",
    ),
    EvalCase(
        "foreign-produced direct product rule for advanced computing and semiconductor manufacturing items",
        frozenset({"2024-28270"}), "federal_register_unique",
        "Title: 'Foreign-Produced Direct Product Rule Additions...'",
    ),
    EvalCase(
        "public briefing on changes to advanced computing semiconductor manufacturing export rules",
        frozenset({"2024-28423"}), "federal_register_unique",
        "Title: 'Public Briefing on Changes to Advanced Computing and Semiconductor Manufacturing Items'",
    ),
    EvalCase(
        "validated end user authorization expansion for data centers",
        frozenset({"2024-22587"}), "federal_register_unique",
        "Title: 'Expansion of Validated End User Authorization: Data Center Validated End User Authorization'",
    ),
    EvalCase(
        "commerce control list additions for advanced technologies aligned with international partners",
        frozenset({"2024-19633"}), "federal_register_unique",
        "Title: 'Commerce Control List Additions and Revisions; Implementation of Controls on Advanced Technologies...'",
    ),
    EvalCase(
        "defense priorities and allocations system regulation updates",
        frozenset({"2024-15370"}), "federal_register_unique",
        "Title: 'Clarifications and Updates to Defense Priorities and Allocations System Regulation'",
    ),
    EvalCase(
        "export controls addressing Iranian aggression against Israel and support for Russia",
        frozenset({"2024-08622"}), "federal_register_unique",
        "Title mentions 'Iranian Aggression Against Israel and Military Support for Russia'",
    ),
    EvalCase(
        "export controls on supercomputer and semiconductor end uses for advanced computing items",
        frozenset({"2024-07004"}), "federal_register_unique",
        "Title: 'Implementation of Additional Export Controls: Certain Advanced Computing Items; Supercomputer and Semiconductor End Use'",
    ),
    EvalCase(
        "restrictions on persons identified on the specially designated nationals SDN list",
        frozenset({"2024-06067"}), "federal_register_unique",
        "Title mentions 'List of Specially Designated Nationals and Blocked Persons (SDN List)'",
    ),
]

# --- Category 2: Entity List family (5 docs share generic title vocabulary) -----
_ENTITY_LIST_FAMILY = frozenset({"2025-17893", "2024-28267", "2024-25411", "2024-19130", "2024-10485"})

_ENTITY_LIST_CASES = [
    EvalCase(
        "additions to the Entity List",  # generic — deliberately ambiguous
        _ENTITY_LIST_FAMILY, "entity_list_generic",
        "5 of the 20 documents share near-identical generic titles about Entity List additions; "
        "a generic query cannot and should not be expected to disambiguate between them.",
    ),
    EvalCase(
        "140 entities added to the Entity List under China Japan South Korea and Singapore",
        frozenset({"2024-28267"}), "entity_list_disambiguated",
        "Abstract: 'adding 140 entities... China, Japan, South Korea, and Singapore'",
    ),
    EvalCase(
        "123 entities added to the Entity List including destinations Russia Kazakhstan Kyrgyzstan and Crimea",
        frozenset({"2024-19130"}), "entity_list_disambiguated",
        "Abstract: 'adding 123 entities... Crimea Region of Ukraine... Kazakhstan... Kyrgyzstan... Russia (63)'",
    ),
    EvalCase(
        "37 entities added to the Entity List all under the destination of China",
        frozenset({"2024-10485"}), "entity_list_disambiguated",
        "Abstract: 'adding 37 entities... listed... under the destinations of the People's Republic of China' (only, no other country)",
    ),
    EvalCase(
        "32 entities added to the Entity List under Taiwan and United Arab Emirates destinations",
        frozenset({"2025-17893"}), "entity_list_disambiguated",
        "Abstract: 'adding 32 entities... Taiwan (1)... United Arab Emirates (UAE) (2)'",
    ),
    EvalCase(
        "40 entities and four addresses added to the Entity List under Malaysia and Turkey",
        frozenset({"2024-25411"}), "entity_list_disambiguated",
        "Abstract: 'adding 40 entities under 42 entries and four addresses... Malaysia (2)... Turkey (14)'",
    ),
]

# --- Category 3: within-filing scoped retrieval (real grepped content) ----------
_FILING_CASES = [
    EvalCase(
        "export controls on advanced computing chips to China risk factor",
        frozenset({"NVDA_10K"}), "filing_scoped", "grep-confirmed: 'export control' x29, 'China' x35 in NVDA_10K.txt",
        metadata_filter={"document_id": "NVDA_10K"}, required_keyword="export control",
    ),
    EvalCase(
        "foundry suppliers Taiwan Semiconductor Samsung and SK Hynix for wafer and memory production",
        frozenset({"NVDA_10K"}), "filing_scoped", "grep-confirmed: NVDA_10K is the only filing mentioning 'SK Hynix'",
        metadata_filter={"document_id": "NVDA_10K"}, required_keyword="sk hynix",
    ),
    EvalCase(
        "cybersecurity incident risk to business operations and data",
        frozenset({"NVDA_10K"}), "filing_scoped", "grep-confirmed: 'cybersecurity' x18 in NVDA_10K.txt (highest of the 3)",
        metadata_filter={"document_id": "NVDA_10K"}, required_keyword="cybersecurity",
    ),
    EvalCase(
        "intellectual property litigation and patent infringement claims",
        frozenset({"AMD_10K"}), "filing_scoped", "grep-confirmed: 'intellectual property' x19 in AMD_10K.txt (highest of the 3)",
        metadata_filter={"document_id": "AMD_10K"}, required_keyword="intellectual property",
    ),
    EvalCase(
        "reliance on Taiwan Semiconductor Manufacturing Company as third-party foundry",
        frozenset({"AMD_10K"}), "filing_scoped", "grep-confirmed: 'TSMC/Taiwan Semiconductor' x4 in AMD_10K.txt",
        metadata_filter={"document_id": "AMD_10K"}, required_keyword="taiwan semiconductor",
    ),
    EvalCase(
        "export administration regulations restricting sales to China",
        frozenset({"AMD_10K"}), "filing_scoped", "grep-confirmed: 'China' x9, 'export control' x4 in AMD_10K.txt",
        metadata_filter={"document_id": "AMD_10K"}, required_keyword="china",
    ),
    EvalCase(
        "Intel Foundry Services manufacturing capacity and external foundry customers",
        frozenset({"INTC_10K"}), "filing_scoped", "grep-confirmed: 'foundry/foundries' x51 in INTC_10K.txt (far highest of the 3)",
        metadata_filter={"document_id": "INTC_10K"}, required_keyword="foundry",
    ),
    EvalCase(
        "export control risk affecting semiconductor sales and licensing",
        frozenset({"INTC_10K"}), "filing_scoped", "grep-confirmed: 'export control' x2 in INTC_10K.txt",
        metadata_filter={"document_id": "INTC_10K"}, required_keyword="export control",
    ),
    EvalCase(
        "China revenue concentration risk to the business",
        frozenset({"INTC_10K"}), "filing_scoped", "grep-confirmed: 'China' x6 in INTC_10K.txt",
        metadata_filter={"document_id": "INTC_10K"}, required_keyword="china",
    ),
]

# --- Category 4: negative controls (nothing in the corpus should match) ---------
_NEGATIVE_CASES = [
    EvalCase("best recipes for sourdough bread baking at home", frozenset(), "negative_control",
              "No ingestion source in this build touches baking."),
    EvalCase("fantasy football draft strategy for quarterbacks", frozenset(), "negative_control",
              "No ingestion source in this build touches sports."),
    EvalCase("renewable solar panel installation costs for homeowners", frozenset(), "negative_control",
              "No ingestion source in this build touches residential solar."),
    EvalCase("backpacking travel itinerary across Europe on a budget", frozenset(), "negative_control",
              "No ingestion source in this build touches leisure travel."),
]

EVAL_CASES: list[EvalCase] = _UNIQUE_FR_CASES + _ENTITY_LIST_CASES + _FILING_CASES + _NEGATIVE_CASES


@dataclass
class CaseResult:
    case: EvalCase
    retrieved: list[RetrievedChunk]
    hit_at_1: bool
    hit_at_3: bool
    reciprocal_rank: float  # 0 if no hit within top_k considered
    keyword_ok: bool


@dataclass
class EvalReport:
    results: list[CaseResult] = field(default_factory=list)

    def summary(self) -> dict:
        n = len(self.results)
        by_category: dict[str, list[CaseResult]] = {}
        for r in self.results:
            by_category.setdefault(r.case.category, []).append(r)
        category_summary = {
            cat: {
                "n": len(rs),
                "hit_rate@1": sum(r.hit_at_1 for r in rs) / len(rs),
                "hit_rate@3": sum(r.hit_at_3 for r in rs) / len(rs),
            }
            for cat, rs in by_category.items()
        }
        return {
            "n_cases": n,
            "hit_rate@1": sum(r.hit_at_1 for r in self.results) / n,
            "hit_rate@3": sum(r.hit_at_3 for r in self.results) / n,
            "mrr": sum(r.reciprocal_rank for r in self.results) / n,
            "keyword_accuracy": sum(r.keyword_ok for r in self.results) / n,
            "by_category": category_summary,
        }


def _is_negative_case(case: EvalCase) -> bool:
    return len(case.expected_document_ids) == 0


def run_eval(
    corpus: list[DocumentChunk], cases: list[EvalCase] = EVAL_CASES, top_k: int = 5, min_score: float = 0.0
) -> EvalReport:
    retriever = LocalLexicalRetriever(corpus)
    report = EvalReport()
    for case in cases:
        retrieved = retriever.retrieve(
            case.query, top_k=top_k, metadata_filter=case.metadata_filter, min_score=min_score
        )

        if _is_negative_case(case):
            hit1 = hit3 = len(retrieved) == 0
            rr = 1.0 if len(retrieved) == 0 else 0.0
            keyword_ok = True
        else:
            doc_ids = [r.chunk.document_id for r in retrieved]
            hit1 = len(doc_ids) > 0 and doc_ids[0] in case.expected_document_ids
            hit3 = any(d in case.expected_document_ids for d in doc_ids[:3])
            rr = 0.0
            for rank, d in enumerate(doc_ids, start=1):
                if d in case.expected_document_ids:
                    rr = 1.0 / rank
                    break
            keyword_ok = True
            if case.required_keyword and retrieved:
                keyword_ok = case.required_keyword.lower() in retrieved[0].chunk.text.lower()

        report.results.append(CaseResult(case=case, retrieved=retrieved, hit_at_1=hit1, hit_at_3=hit3, reciprocal_rank=rr, keyword_ok=keyword_ok))
    return report
