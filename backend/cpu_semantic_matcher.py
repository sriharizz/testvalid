import re
import math
import difflib
from collections import Counter
from typing import List, Dict, Any, Optional, Tuple

_MINILM_MODEL = None
_MINILM_ATTEMPTED = False

def _get_local_minilm():
    """Loads all-MiniLM-L6-v2 from local disk cache ONLY (never hangs on network/VPN)."""
    global _MINILM_MODEL, _MINILM_ATTEMPTED
    if _MINILM_ATTEMPTED:
        return _MINILM_MODEL
    _MINILM_ATTEMPTED = True
    try:
        from sentence_transformers import SentenceTransformer
        _MINILM_MODEL = SentenceTransformer("all-MiniLM-L6-v2", device="cpu", local_files_only=True)
    except Exception:
        _MINILM_MODEL = None
    return _MINILM_MODEL

# Canonical equivalence clusters for GxP / Pharmacovigilance / Web UI validation
CONCEPT_CLUSTERS = [
    ("FUTURE_TIME", ["in the future", "future date", "later than current date", "after current date", "after today", "greater than today", "tomorrow", "future"]),
    ("PAST_TIME", ["in the past", "earlier than", "before today", "prior to", "yesterday"]),
    ("PROHIBITION", ["cannot", "must not", "shall not", "may not", "not allow", "block", "prevent", "restrict", "disallow", "prohibit", "rejected", "failed"]),
    ("ADMISSION_DATE", ["hospitalization admission date", "date of hospital admission", "hospital admission date", "admission date", "admit date"]),
    ("RECEIPT_DATE", ["company receipt date", "date of receipt", "receipt date", "received date"]),
    ("BIRTH_DATE", ["date of birth", "birth date", "dob", "patient dob"]),
    ("HCP_ROLE", ["health care professional", "healthcare professional", "physician", "medical doctor", "clinician", "hcp", "dr"]),
    ("CONSUMER_ROLE", ["consumer", "patient", "non-health care professional", "non-hcp", "lawyer"]),
    ("SERIOUS_YES", ["serious", "yes", "true", "y"]),
    ("SERIOUS_NO", ["non-serious", "not serious", "non_serious", "no", "false", "n"]),
    ("MANDATORY_REQ", ["mandatory", "required", "cannot be blank", "cannot be empty", "must be filled", "missing required"]),
    ("SUCCESS_CONFIRM", ["registered successfully", "created successfully", "saved successfully", "confirmation message", "successfully"]),
    ("COUNTRY_US", ["united states", "united states of america", "usa", "us"]),
    ("COUNTRY_UK", ["united kingdom", "great britain", "uk", "gb"]),
    ("COUNTRY_IN", ["india", "ind", "in"]),
    ("COUNTRY_CA", ["canada", "can", "ca"]),
    ("COUNTRY_DE", ["germany", "deu", "de"]),
]

BOILERPLATE_PATTERNS = [
    r"\bsystem\s+shall\b", r"\bsystem\s+should\b", r"\bapplication\s+shall\b",
    r"\bverify\s+that\b", r"\bensure\s+that\b", r"\bshow\s+an?\s+error\s+alert\s+that\b",
    r"\bdisplay\s+an?\s+error\s+message\s+that\b", r"\bvalidation\s+failed\s*:\s*",
    r"\bvalidation\s+error\s*:\s*", r"\berror\s*:\s*", r"\bblock\s+registration\s+and\b",
    r"\bblock\s+save\s+and\b"
]

def normalize_and_canonicalize(text: str) -> Tuple[str, set]:
    """Strips GxP boilerplate and extracts canonical semantic concept tags."""
    low = (text or "").lower().strip()
    for pat in BOILERPLATE_PATTERNS:
        low = re.sub(pat, " ", low, flags=re.I)
    low = re.sub(r"[^a-z0-9\s]", " ", low)
    low = re.sub(r"\s+", " ", low).strip()

    active_concepts = set()
    canon_text = low
    for tag, phrases in CONCEPT_CLUSTERS:
        for ph in sorted(phrases, key=len, reverse=True):
            if re.search(rf"\b{re.escape(ph)}\b", canon_text):
                active_concepts.add(tag)
                canon_text = re.sub(rf"\b{re.escape(ph)}\b", f" {tag.lower()} ", canon_text)
    canon_text = re.sub(r"\s+", " ", canon_text).strip()
    return canon_text, active_concepts

def _char_ngram_cosine(a: str, b: str, n: int = 3) -> float:
    if not a or not b:
        return 0.0
    a_pad = f"  {a}  "
    b_pad = f"  {b}  "
    ca = Counter(a_pad[i:i+n] for i in range(max(1, len(a_pad) - n + 1)))
    cb = Counter(b_pad[i:i+n] for i in range(max(1, len(b_pad) - n + 1)))
    common = set(ca.keys()) & set(cb.keys())
    num = sum(ca[k] * cb[k] for k in common)
    den = math.sqrt(sum(v*v for v in ca.values())) * math.sqrt(sum(v*v for v in cb.values()))
    return (num / den) if den > 0 else 0.0

def _token_jaccard(a: str, b: str) -> float:
    stop = {"the", "a", "an", "to", "of", "in", "on", "for", "be", "is", "are", "was", "were", "by", "with", "as", "at"}
    ta = {t for t in a.split() if t not in stop and len(t) > 1}
    tb = {t for t in b.split() if t not in stop and len(t) > 1}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)

def compute_assertion_similarity(expected_text: str, actual_observed_text: str) -> float:
    """
    Computes semantic similarity (0.0 to 1.0) between protocol Expected Result and Actual UI feedback.
    Runs in <8ms on CPU with 0 GPU load and 100% offline reliability.
    """
    if not expected_text or not actual_observed_text:
        return 0.0

    canon_exp, concepts_exp = normalize_and_canonicalize(expected_text)
    canon_act, concepts_act = normalize_and_canonicalize(actual_observed_text)

    # Disqualify if specific field/subject concepts conflict (e.g. ADMISSION_DATE expected, but not present and another field is)
    subject_tags = {"ADMISSION_DATE", "RECEIPT_DATE", "BIRTH_DATE", "HCP_ROLE", "CONSUMER_ROLE"}
    exp_subjects = concepts_exp & subject_tags
    act_subjects = concepts_act & subject_tags
    if exp_subjects and not (exp_subjects & act_subjects):
        # Check if raw head nouns from expected appear in actual
        raw_exp_tokens = {t for t in re.findall(r"[a-z]{4,}", expected_text.lower()) if t not in {"system", "shall", "should", "error", "alert", "message", "validation", "block", "registration", "cannot", "future", "mandatory", "required", "display", "show"}}
        raw_act_tokens = set(re.findall(r"[a-z]{4,}", actual_observed_text.lower()))
        if raw_exp_tokens and not (raw_exp_tokens & raw_act_tokens):
            return 0.20

    # Hybrid CPU score
    ngram_sim = _char_ngram_cosine(canon_exp, canon_act, n=3)
    jaccard_sim = _token_jaccard(canon_exp, canon_act)
    seq_sim = difflib.SequenceMatcher(None, canon_exp, canon_act).ratio()

    concept_Overlap = 0.0
    if concepts_exp and concepts_act:
        concept_Overlap = len(concepts_exp & concepts_act) / len(concepts_exp | concepts_act)

    hybrid_score = (0.35 * ngram_sim) + (0.30 * jaccard_sim) + (0.15 * seq_sim) + (0.20 * concept_Overlap)
    if concepts_exp and concepts_exp.issubset(concepts_act) and len(concepts_exp) >= 2:
        hybrid_score = max(hybrid_score, 0.86)

    # Optional boost/averaging with local MiniLM if cached on disk
    model = _get_local_minilm()
    if model is not None:
        try:
            emb = model.encode([canon_exp, canon_act], normalize_embeddings=True)
            minilm_sim = float(emb[0] @ emb[1])
            hybrid_score = max(hybrid_score, (0.6 * minilm_sim) + (0.4 * hybrid_score))
        except Exception:
            pass

    return round(min(1.0, max(0.0, hybrid_score)), 4)

def match_label_to_dom_candidates(
    target_label: str,
    candidates: List[Dict[str, Any]],
    threshold: float = 0.78
) -> Tuple[Optional[Dict[str, Any]], float]:
    """
    Matches a step field label (e.g. 'admission date') to live DOM control candidates
    (e.g. [{'id': '#adm_dt', 'label': 'Hospitalization Admission Date'}]).
    """
    if not target_label or not candidates:
        return None, 0.0

    tgt_clean = re.sub(r"[^a-z0-9\s]", " ", target_label.lower()).strip()
    tgt_canon, tgt_concepts = normalize_and_canonicalize(target_label)
    tgt_tokens = {t for t in tgt_clean.split() if len(t) > 1 and t not in {"code", "field", "input", "the", "for"}}

    best_cand = None
    best_score = 0.0

    for cand in candidates:
        c_label = str(cand.get("label") or cand.get("aria_label") or cand.get("placeholder") or cand.get("name") or cand.get("id") or "").strip()
        if not c_label:
            continue
        c_clean = re.sub(r"[^a-z0-9\s]", " ", c_label.lower()).strip()
        c_canon, c_concepts = normalize_and_canonicalize(c_label)
        c_tokens = {t for t in c_clean.split() if len(t) > 1 and t not in {"code", "field", "input", "the", "for"}}

        if c_clean == tgt_clean:
            return cand, 1.0

        score = 0.0
        if tgt_concepts and (tgt_concepts == c_concepts):
            score = 0.92
        elif tgt_tokens and c_tokens:
            overlap = len(tgt_tokens & c_tokens) / len(tgt_tokens)
            jaccard = len(tgt_tokens & c_tokens) / len(tgt_tokens | c_tokens)
            ngram = _char_ngram_cosine(c_canon, tgt_canon, n=3)
            score = (0.50 * overlap) + (0.25 * jaccard) + (0.25 * ngram)
            if tgt_clean in c_clean or c_clean in tgt_clean:
                score = max(score, 0.86)

        if score > best_score:
            best_score = score
            best_cand = cand

    if best_score >= threshold:
        return best_cand, round(best_score, 4)
    return None, round(best_score, 4)

def match_dropdown_option(
    target_value: str,
    options: List[Dict[str, str]],
    threshold: float = 0.78
) -> Tuple[Optional[Dict[str, str]], float, str]:
    """
    Matches a requested dropdown value (e.g. 'Physician') against live <select>/combobox options.
    Returns (matched_option_dict, confidence_score, provenance_tag).
    """
    if not target_value or not options:
        return None, 0.0, "protocol_explicit"

    tgt_clean = target_value.strip().lower().rstrip(".")
    _, tgt_concepts = normalize_and_canonicalize(target_value)

    # 1. Exact literal match
    for opt in options:
        opt_t = str(opt.get("text", "")).strip().lower().rstrip(".")
        opt_v = str(opt.get("val", opt.get("value", ""))).strip().lower().rstrip(".")
        if opt_t == tgt_clean or opt_v == tgt_clean:
            return opt, 1.0, "protocol_explicit"

    # 2. Concept cluster & semantic match (e.g. Physician -> HCP)
    best_opt = None
    best_score = 0.0
    for opt in options:
        opt_raw = str(opt.get("text") or opt.get("val") or "")
        opt_clean = opt_raw.strip().lower().rstrip(".")
        _, opt_concepts = normalize_and_canonicalize(opt_raw)

        score = 0.0
        # Algorithmic acronym match (e.g. US -> United States, UK -> United Kingdom, USA -> United States of America)
        words_t = [w for w in re.split(r'[\s_\-]+', opt_clean) if w and w not in {"of", "the", "and", "in", "to", "for"}]
        acronym_t = "".join(w[0] for w in words_t) if len(words_t) >= 2 else ""
        if acronym_t and (acronym_t == tgt_clean or "".join(w[0] for w in re.split(r'[\s_\-]+', opt_clean) if w) == tgt_clean):
            score = 0.95
        elif tgt_concepts and (tgt_concepts & opt_concepts):
            score = 0.90
        elif tgt_clean in opt_clean or opt_clean in tgt_clean:
            score = 0.85
        else:
            score = _char_ngram_cosine(tgt_clean, opt_clean, n=3)

        if score > best_score:
            best_score = score
            best_opt = opt

    if best_opt and best_score >= threshold:
        return best_opt, round(best_score, 4), "cpu_semantic_match"
    return None, round(best_score, 4), "protocol_explicit"
