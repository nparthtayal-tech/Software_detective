"""
CBCA EVIDENCE ANALYSIS MODULE

FOLDER LOCATION
---------------
IDP/
└── modules/
    └── cbca/
        ├── cbca.py
        ├── criteria.py
        └── __init__.py

INPUT JSON
----------
{
    "statement": "Verbatim statement/transcript to analyze.",
    "criterion_annotations": {
        "logical_structure": {
            "present": true,
            "strength": 0.82,
            "evidence": ["The account follows a coherent sequence."]
        },
        "quantity_of_details": {
            "present": true,
            "strength": 0.74,
            "evidence": ["The speaker gives several concrete details."]
        }
    }
}

Only "statement" is required. criterion_annotations is optional and
represents observations supplied by a human coder or a separately validated
extraction component.

OUTPUT JSON
-----------
{
    "method": "CBCA",
    "analysis_type": "evidence_analysis",
    "criteria": {
        "logical_structure": {
            "id": 1,
            "name": "Logical structure",
            "category": "general_characteristics",
            "observed": true,
            "evidence_strength": 0.82,
            "evidence": ["..."],
            "research_direction": "supportive_of_CBCA_characteristic",
            "interpretation": "...",
            "caution": "..."
        }
    },
    "findings": [
        {
            "type": "cbca_characteristic",
            "criterion": "logical_structure",
            "evidence_strength": 0.82,
            "what_was_observed": "...",
            "why_it_matters": "...",
            "what_it_does_not_establish": "..."
        }
    ],
    "summary": {
        "observed_criteria": 2,
        "evidence_profile": "descriptive_only"
    },
    "limitations": ["..."]
}

IMPORTANT
---------
This module deliberately does NOT output a truth/deception probability,
truthfulness label, or arbitrary CBCA cutoff.
"evidence_strength" means strength of the observed textual characteristic,
NOT probability that the statement is true.

RESEARCH BASIS
--------------
Steller, M., & Köhnken, G. (1989). Criteria-Based Content Analysis.
In D. C. Raskin (Ed.), Psychological Methods in Criminal Investigation
and Evidence.

Later work informing the design includes:
- Amado et al. (2016), International Journal of Clinical and Health Psychology.
- Hauch et al. (2017), Psychological Assessment, 29, 819–834.
- Oberlader et al. (2021), Applied Cognitive Psychology.

The implementation is a research-grounded software operationalization,
not an official CBCA software package.
"""

from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from .criteria import CRITERIA

LIMITATIONS = [
    "CBCA is not a standalone lie detector.",
    "Presence of a criterion does not establish truthfulness.",
    "Absence of a criterion does not establish deception.",
    "No universal diagnostic cutoff is implemented.",
    "Criterion reliability and validity vary across criteria and contexts.",
    "Evidence strength is not a probability of truth or deception.",
    "Interview conditions, memory, culture, age, language, and context can affect criterion expression.",
]


def _annotation(value: Any) -> dict[str, Any]:
    if isinstance(value, bool):
        return {"present": value, "strength": None, "evidence": []}
    if not isinstance(value, Mapping):
        raise TypeError("Each criterion annotation must be a bool or object.")
    present = value.get("present")
    if present is not None and not isinstance(present, bool):
        raise TypeError("'present' must be true, false, or null.")
    strength = value.get("strength")
    if strength is not None:
        strength = float(strength)
        if not 0.0 <= strength <= 1.0:
            raise ValueError("'strength' must be between 0 and 1.")
    evidence = value.get("evidence", [])
    if isinstance(evidence, str): evidence = [evidence]
    elif evidence is None: evidence = []
    elif not isinstance(evidence, list): raise TypeError("'evidence' must be a string, list, or null.")
    return {"present": present, "strength": strength, "evidence": [str(x) for x in evidence]}


def analyze(statement: str, criterion_annotations: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(statement, str):
        raise TypeError("statement must be a string.")
    annotations = criterion_annotations or {}
    known = {c["key"] for c in CRITERIA}
    unknown = set(annotations) - known
    if unknown:
        raise ValueError("Unknown CBCA criterion(s): " + ", ".join(sorted(unknown)))

    criteria_result = {}
    findings = []
    for c in CRITERIA:
        key = c["key"]
        item = {
            "id": c["id"], "name": c["name"], "category": c["category"],
            "observed": None, "evidence_strength": None, "evidence": [],
            "research_direction": "supportive_of_CBCA_characteristic",
            "interpretation": None,
            "caution": "This characteristic must not be interpreted independently as evidence of truth or deception."
        }
        if key in annotations:
            obs = _annotation(annotations[key])
            item.update({"observed": obs["present"], "evidence_strength": obs["strength"], "evidence": obs["evidence"]})
            if obs["present"] is True:
                item["interpretation"] = f"{c['name']} was observed. {c['description']} Its presence is a research-related characteristic, not proof that the account is truthful."
                findings.append({
                    "type": "cbca_characteristic", "criterion": key,
                    "evidence_strength": obs["strength"],
                    "what_was_observed": " ".join(obs["evidence"]) if obs["evidence"] else c["description"],
                    "why_it_matters": "This is a characteristic considered in CBCA analysis.",
                    "what_it_does_not_establish": "It does not establish truthfulness, deception, or intent. Alternative explanations remain possible."
                })
        criteria_result[key] = item

    return {
        "method": "CBCA", "analysis_type": "evidence_analysis",
        "criteria": criteria_result, "findings": findings,
        "summary": {"observed_criteria": sum(x["observed"] is True for x in criteria_result.values()), "evidence_profile": "descriptive_only"},
        "limitations": deepcopy(LIMITATIONS),
    }


def criteria_catalog() -> list[dict[str, Any]]:
    return deepcopy(CRITERIA)
