"""
NLP ENGINE — Gemini API natural-language → structured JSON converter.

Takes raw witness/suspect/victim statements in natural language and uses the
Gemini API to extract the exact JSON structures that the six investigation
algorithms expect:

  1. timeline_events       → per-statement event list
  2. cbca_annotations      → criterion_annotations for the CBCA module
  3. rm_annotations        → criterion_annotations for the RM module
  4. conflicts             → cross-statement event conflicts for Conflict Graph MIS
  5. corroborations        → cross-statement event agreements for PageRank
  6. contested_facts       → fact → version → count for Entropy
  7. precedence            → temporal ordering pairs for Topological Sort

INPUT
-----
A Python list of dicts:
[
    {
        "speaker_name": "Rajesh Mehta",
        "speaker_role": "victim",
        "statement_text": "I was closing up the store..."
    },
    ...
]

OUTPUT
------
A single unified dict ready for main.py to dispatch to every algorithm.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def _get_api_keys() -> list[str]:
    """Retrieve all configured Gemini API keys from .env."""
    load_dotenv(override=True)
    keys = []
    primary = os.getenv("GEMINI_API_KEY", "").strip()
    if primary and primary != "YOUR_GEMINI_API_KEY_HERE":
        keys.append(primary)
    for idx in range(2, 10):
        k = os.getenv(f"GEMINI_API_KEY_{idx}", "").strip()
        if k and k != "YOUR_GEMINI_API_KEY_HERE" and k not in keys:
            keys.append(k)
    return keys


def _get_client(api_key: str | None = None):
    """Lazy-init the Gemini client."""
    from google import genai

    if not api_key:
        keys = _get_api_keys()
        if not keys:
            raise RuntimeError(
                "GEMINI_API_KEY is not set in .env. "
                "Please add your Gemini API key to .env."
            )
        api_key = keys[0]
    return genai.Client(api_key=api_key)


# ---------------------------------------------------------------------------
# The master prompt
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = r"""
You are a forensic-linguistics extraction engine.  You will receive a JSON
array of witness/victim/suspect statements.  Your job is to return a SINGLE
valid JSON object (no markdown fences, no commentary) with the keys described
below.

────────────────────────────────────────────────
1.  "statements"  — one object per input statement, keyed by a sequential ID
    like STMT_01, STMT_02, etc.  Each object has:

    "speaker_name":  string
    "speaker_role":  string (victim | witness | suspect | informant)
    "statement_text": the original text verbatim
    "statement_id":  the STMT_XX key

    "timeline_events": a list of events extracted from the statement.  Each:
        "event_id":     "E1", "E2", …  (sequential within the statement)
        "description":  short label (≤8 words)
        "actors":       list of participant names/labels
        "location":     where it happened (short)
        "time_start":   "HH:MM"  24-hour format.  Estimate if approximate.
        "time_end":     "HH:MM"  24-hour format.
        "action":       what happened (short phrase)

    "cbca_annotations": criterion_annotations for the CBCA module.
        Use ONLY these keys:
            logical_structure, unstructured_production, quantity_of_details,
            contextual_embedding, descriptions_of_interactions,
            reproduction_of_conversation, unexpected_complications,
            unusual_details, superfluous_details,
            accurately_reported_misunderstood_details,
            related_external_associations, subjective_mental_state,
            attribution_of_others_mental_state, spontaneous_corrections,
            admitting_lack_of_memory, raising_doubts_about_own_testimony,
            self_deprecation, pardoning_other_participant,
            offense_specific_elements
        For each key that IS observed in the text, provide:
            { "present": true, "strength": 0.0-1.0, "evidence": ["quote/paraphrase from text"] }
        Omit keys that are not observed.

    "rm_annotations": criterion_annotations for the Reality Monitoring module.
        Use ONLY these keys:
            clarity_vividness, sensory_information, spatial_information,
            temporal_information, affective_information, reconstructability,
            realism, cognitive_operations
        For each key that IS observed:
            { "observed": true, "strength": 0.0-1.0,
              "frequency": <int count of instances>,
              "intensity": <0|1|2> (only for clarity_vividness/reconstructability/realism),
              "evidence": ["quote/paraphrase"] }
        Omit keys that are not observed.

────────────────────────────────────────────────
2.  "conflicts"  — a list of objects, each:
    {
        "event_a_id":  "STMT_XX.EY",
        "event_b_id":  "STMT_XX.EY",
        "fact_category": short label (vehicle | direction | count | time | alibi …),
        "description": one-sentence explanation of the contradiction,
        "version_a": what event_a claims,
        "version_b": what event_b claims
    }

────────────────────────────────────────────────
3.  "corroborations"  — a list of objects, each:
    {
        "event_a_id":  "STMT_XX.EY",
        "event_b_id":  "STMT_XX.EY",
        "description": one-sentence explanation of the agreement,
        "weight": 0.0-1.0 (how strong the agreement is)
    }

────────────────────────────────────────────────
4.  "contested_facts"  — a list of objects, each:
    {
        "fact": short label (e.g. "Escape vehicle type"),
        "versions": { "version_label": <count of statements supporting it>, ... }
    }

────────────────────────────────────────────────
5.  "precedence"  — a list of [before_event_full_id, after_event_full_id] pairs
    expressing "event A must have happened before event B" based on the combined
    accounts.  Use full IDs like "STMT_01.E1".

────────────────────────────────────────────────
RULES
• Return ONLY the JSON object.  No markdown, no explanation, no extra text.
• event full IDs are always "STMT_XX.EY" (statement id dot event id).
• strength / weight values must be between 0 and 1.
• Do NOT invent facts not in the statements.
• If a criterion is not observed, do NOT include it in annotations.
• Be conservative: only flag conflicts where statements genuinely contradict.
"""


def extract(statements: list[dict[str, str]]) -> dict[str, Any]:
    """
    Convert natural-language statements into structured JSON.

    Parameters
    ----------
    statements : list of dict
        Each dict must have keys: speaker_name, speaker_role, statement_text.

    Returns
    -------
    dict
        The unified extraction ready for the orchestrator.
    """
    # Validate input
    for i, s in enumerate(statements):
        for key in ("speaker_name", "speaker_role", "statement_text"):
            if key not in s:
                raise ValueError(f"Statement {i} is missing '{key}'.")

    keys = _get_api_keys()
    if not keys:
        raise RuntimeError("No GEMINI_API_KEY found in .env.")

    user_payload = json.dumps(statements, indent=2, ensure_ascii=False)
    last_err = None

    for api_key in keys:
        try:
            client = _get_client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=[
                    {"role": "user", "parts": [{"text": _SYSTEM_PROMPT + "\n\nSTATEMENTS:\n" + user_payload}]}
                ],
            )
            raw = response.text.strip()
            # Strip markdown code fences if Gemini wraps the response.
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            result = json.loads(raw)
            # Light validation of top-level keys.
            for key in ("statements", "conflicts", "corroborations", "contested_facts", "precedence"):
                if key not in result:
                    result[key] = [] if key != "statements" else {}
            return result
        except Exception as exc:
            last_err = exc
            print(f"Gemini key attempt failed: {exc}")
            continue

    raise RuntimeError(f"Gemini extraction failed: {last_err}")
