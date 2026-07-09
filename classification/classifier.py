"""
classification/classifier.py

Local, deterministic, rule-based ISIC Rev.5 classifier (no network, no LLM).

How it works
------------
Each ISIC division (2-digit code) is associated with a set of weighted terms:

  1. Auto-seeded terms  -- derived from the division's own official title
                           (weight 1). Guarantees every one of the 87 divisions
                           is reachable.
  2. Curated terms      -- a hand-built map of strong, discriminative signals
                           (weight 3-4) for the topics that dominate qualitative
                           social-science research (health, education, social
                           work, public administration, labour, agriculture ...).

To classify a piece of text we lower-case it, then for every division sum the
weights of the terms that appear (matched on word boundaries; multi-word phrases
matched as phrases). The division with the highest score wins. Score 0 => the
text is left unclassified (division = None).

The classifier is fully deterministic: the same input always yields the same
division, so results are reproducible without caching.

Public API
----------
    clf = Classifier()
    result = clf.classify(text)      # -> ClassResult or None
    result.division                  # '86'
    result.label                     # '86 - Human health activities'
    result.score                     # float
    result.matched                   # {'nurse': 3, 'patient': 3, ...}
"""

from __future__ import annotations

import re
import sys
import pathlib
from collections import Counter
from dataclasses import dataclass, field

_root = pathlib.Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from classification.isic_rev5 import DIVISIONS, DIVISION_TITLE, label as division_label


# ── words that carry no discriminating signal in division titles ──────────────
_TITLE_STOPWORDS = {
    "and", "of", "the", "for", "or", "to", "in", "with", "other", "n.e.c",
    "nec", "except", "related", "activities", "activity", "service", "services",
    "products", "product", "manufacture", "goods", "materials", "material",
    "equipment", "supply", "including", "such", "as", "by", "on", "own", "use",
    "compulsory", "general", "various", "certain", "etc", "producing",
}

# terms that are too generic / ambiguous to be reliable on their own
_BANNED_TERMS = {"care", "work", "social", "data", "study", "research", "public",
                 "management", "support", "production", "primary", "human"}


# ── curated strong signals: division_code -> list of terms (weight applied below)
# Terms may be single words or multi-word phrases. Phrases are matched verbatim.
CURATED: dict[str, list[str]] = {
    # A. Agriculture, forestry and fishing
    "01": ["farming", "farmer", "farmers", "agriculture", "agricultural", "crop",
           "crops", "livestock", "cattle", "dairy", "harvest", "smallholder",
           "peasant", "cultivation", "rural livelihood"],
    "02": ["forestry", "logging", "deforestation", "forest management"],
    "03": ["fishing", "fishery", "fisheries", "fishermen", "aquaculture"],
    # B. Mining and quarrying
    "05": ["coal mining", "lignite"],
    "06": ["crude petroleum", "natural gas extraction", "oil extraction"],
    "07": ["metal ore", "metal mining"],
    "08": ["quarrying", "quarry"],
    # C. Manufacturing (selected)
    "10": ["food processing", "food production", "food manufacturing"],
    "11": ["brewing", "beverage production", "winery"],
    "13": ["textile", "textiles", "weaving", "spinning"],
    "14": ["garment", "clothing manufacture", "apparel"],
    "21": ["pharmaceutical", "pharmaceuticals", "drug manufacturing"],
    "26": ["semiconductor", "electronics manufacturing"],
    "29": ["automotive", "car manufacturing", "motor vehicle"],
    # D/E. Utilities, water, waste
    "35": ["electricity supply", "power generation", "energy grid", "renewable energy"],
    "36": ["water supply", "drinking water", "water treatment"],
    "37": ["sewerage", "wastewater"],
    "38": ["waste collection", "recycling", "waste management"],
    "39": ["remediation", "environmental cleanup"],
    # F. Construction
    "41": ["building construction", "housing construction", "residential building"],
    "42": ["civil engineering", "infrastructure construction"],
    "43": ["plumbing", "electrical installation", "construction site"],
    # G. Trade
    "46": ["wholesale", "wholesaler"],
    "47": ["retail", "retailer", "shop", "supermarket", "consumer shopping"],
    # H. Transport
    "49": ["road transport", "railway", "trucking", "bus transport"],
    "50": ["shipping", "maritime transport", "water transport"],
    "51": ["aviation", "airline", "air transport"],
    "52": ["warehousing", "logistics"],
    "53": ["postal", "courier"],
    # I. Accommodation and food service
    "55": ["hotel", "hostel", "accommodation"],
    "56": ["restaurant", "catering", "hospitality"],
    # J. Publishing, broadcasting, content
    "58": ["publishing", "book publishing", "newspaper publishing"],
    "59": ["film", "cinema", "motion picture", "video production", "music recording"],
    "60": ["broadcasting", "television programme", "radio broadcasting", "news agency"],
    # K. Telecom / IT
    "61": ["telecommunications", "mobile network", "telecom"],
    "62": ["software", "programming", "software development", "coding"],
    "63": ["data processing", "web hosting", "cloud computing", "computing infrastructure"],
    # L. Finance
    "64": ["banking", "bank", "financial services", "lending", "credit"],
    "65": ["insurance", "pension fund", "reinsurance"],
    "66": ["financial intermediation", "brokerage"],
    # M. Real estate
    "68": ["real estate", "housing", "tenancy", "landlord", "property market", "rental housing"],
    # N. Professional / scientific / technical
    "69": ["legal", "lawyer", "law firm", "accounting", "auditing", "notary"],
    "70": ["management consultancy", "head office"],
    "71": ["architecture", "architectural", "engineering services", "technical testing"],
    "72": ["scientific research", "research and development", "laboratory research"],
    "73": ["advertising", "market research", "public relations", "marketing"],
    "75": ["veterinary", "animal health"],
    # O. Administrative and support
    "77": ["rental service", "leasing"],
    "78": ["recruitment", "employment agency", "temporary staffing"],
    "79": ["tourism", "tourist", "travel agency", "tour operator"],
    "80": ["security service", "private security", "investigation service"],
    "81": ["cleaning service", "landscaping", "facility management"],
    "82": ["call centre", "office administration", "business support"],
    # P. Public administration and defence
    "84": ["government", "governance", "public policy", "public administration",
            "policy making", "election", "voting", "democracy", "citizenship",
            "welfare state", "military", "defence", "police", "immigration policy",
            "asylum", "refugee", "migration policy", "taxation", "civil service"],
    # Q. Education
    "85": ["education", "school", "schooling", "teacher", "teachers", "teaching",
            "student", "students", "pupil", "pupils", "classroom", "curriculum",
            "pedagogy", "pedagogical", "university", "higher education", "learning",
            "literacy", "vocational training", "kindergarten", "e-learning"],
    # R. Human health and social work
    "86": ["health", "healthcare", "health care", "hospital", "patient", "patients",
            "clinical", "clinic", "nurse", "nurses", "nursing", "physician", "doctor",
            "medical", "medicine", "mental health", "psychiatric", "disease",
            "illness", "diagnosis", "therapy", "treatment", "public health",
            "epidemic", "pandemic", "covid", "disability", "well-being", "wellbeing"],
    "87": ["nursing home", "residential care", "care home", "elderly care"],
    "88": ["social work", "social worker", "social services", "child protection",
            "welfare service", "counselling", "youth work", "community care"],
    # S. Arts, sports, recreation
    "90": ["performing arts", "theatre", "dance", "visual arts", "artist"],
    "91": ["museum", "library", "archive", "cultural heritage", "heritage"],
    "92": ["gambling", "betting", "lottery"],
    "93": ["sport", "sports", "athletics", "recreation", "fitness", "leisure"],
    # 94 membership organizations / religion
    "94": ["trade union", "labour union", "religion", "religious", "church",
            "mosque", "faith", "ngo", "civil society", "association", "political party"],
    # T. Other services
    "96": ["hairdressing", "beauty salon", "funeral", "personal services"],
    # U. households as employers
    "97": ["domestic worker", "domestic service", "household employee"],
}

# labour / employment cuts across activities but maps best to employment services
CURATED.setdefault("78", []).extend(
    ["labour market", "employment", "unemployment", "worker", "workers",
     "workplace", "job", "jobs", "occupation", "working conditions"]
)

# gender / family / migration studies -> most often social/public-administration framed
CURATED.setdefault("84", []).extend(
    ["migration", "migrant", "migrants", "integration policy", "gender policy"]
)


# ── weights ───────────────────────────────────────────────────────────────────
_CURATED_WEIGHT = 3.0
_TITLE_WEIGHT = 1.0
_MAX_OCCURRENCE = 5   # cap the contribution of any single repeated term


def _tokenize_title(title: str) -> list[str]:
    """Pull discriminating single words out of an official division title."""
    words = re.findall(r"[a-z]+", title.lower())
    return [w for w in words
            if len(w) > 3 and w not in _TITLE_STOPWORDS and w not in _BANNED_TERMS]


_WORD_RE = re.compile(r"[a-z]+")


def _build_indexes():
    """
    Build two reverse indexes for fast scoring (same scoring as a per-term
    word-boundary regex, but computed in a single pass over the text):

      word_index[word]   -> list of (division_code, weight)   single alpha words
      phrase_terms       -> list of (division_code, phrase, weight)  multi-word /
                            hyphenated / non-pure-alpha terms
    """
    word_index: dict[str, list[tuple[str, float]]] = {}
    phrase_terms: list[tuple[str, str, float]] = []

    def add(code: str, term: str, weight: float):
        term = term.strip().lower()
        if not term or term in _BANNED_TERMS:
            return
        if term.isalpha():                       # single pure-alpha word
            word_index.setdefault(term, []).append((code, weight))
        else:                                    # phrase / hyphenated / has digits
            phrase_terms.append((code, term, weight))

    # 1. auto-seed from official titles
    for code, title, _sec, _sect in DIVISIONS:
        for w in set(_tokenize_title(title)):
            add(code, w, _TITLE_WEIGHT)

    # 2. curated strong signals
    for code, terms in CURATED.items():
        for t in terms:
            add(code, t, _CURATED_WEIGHT)

    return word_index, phrase_terms


@dataclass
class ClassResult:
    division: str
    label: str
    score: float
    matched: dict[str, float] = field(default_factory=dict)


class Classifier:
    def __init__(self):
        self._word_index, self._phrase_terms = _build_indexes()

    def _score(self, text: str):
        """Return (scores, matched) dicts over division codes."""
        hay = text.lower()
        scores: dict[str, float] = {}
        matched: dict[str, dict[str, float]] = {}

        # single-word terms: one tokenization, then O(1) lookups
        counts = Counter(_WORD_RE.findall(hay))
        for word, cnt in counts.items():
            entries = self._word_index.get(word)
            if not entries:
                continue
            capped = min(cnt, _MAX_OCCURRENCE)
            for code, weight in entries:
                contrib = weight * capped
                scores[code] = scores.get(code, 0.0) + contrib
                m = matched.setdefault(code, {})
                m[word] = m.get(word, 0.0) + contrib

        # phrase / hyphenated terms: direct substring count
        for code, phrase, weight in self._phrase_terms:
            n = hay.count(phrase)
            if n:
                contrib = weight * min(n, _MAX_OCCURRENCE)
                scores[code] = scores.get(code, 0.0) + contrib
                m = matched.setdefault(code, {})
                m[phrase] = m.get(phrase, 0.0) + contrib

        return scores, matched

    def classify(self, text: str) -> ClassResult | None:
        if not text or not text.strip():
            return None
        scores, matched = self._score(text)
        if not scores:
            return None
        # deterministic: highest score, tie-break by lowest division code
        best_code = min(scores, key=lambda c: (-scores[c], c))
        return ClassResult(
            division=best_code,
            label=division_label(best_code),
            score=round(scores[best_code], 2),
            matched=matched.get(best_code, {}),
        )

    def classify_ranked(self, text: str, n: int = 2) -> list[ClassResult]:
        """Return up to n best divisions, highest score first (deterministic)."""
        if not text or not text.strip():
            return []
        scores, matched = self._score(text)
        if not scores:
            return []
        ordered = sorted(scores, key=lambda c: (-scores[c], c))[:n]
        return [
            ClassResult(
                division=code,
                label=division_label(code),
                score=round(scores[code], 2),
                matched=matched.get(code, {}),
            )
            for code in ordered
        ]


# quick manual check:  python -m classification.classifier
if __name__ == "__main__":
    clf = Classifier()
    samples = [
        "Semi-structured interviews with nurses about patient care in hospitals",
        "A qualitative study of teachers and classroom pedagogy in primary schools",
        "Focus groups with smallholder farmers on crop cultivation and livestock",
        "Interviews on asylum seekers and refugee migration policy",
        "Ethnography of software developers and programming practices",
        "zzzz nothing matches here 123",
    ]
    for s in samples:
        r = clf.classify(s)
        if r:
            top = sorted(r.matched.items(), key=lambda x: -x[1])[:4]
            print(f"[{r.division}] {r.label}  score={r.score}  {top}")
            print(f"    <- {s}")
        else:
            print(f"[--] UNCLASSIFIED  <- {s}")
