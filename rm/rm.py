"""
REALITY MONITORING (RM) EVIDENCE ANALYSIS MODULE

FOLDER LOCATION
---------------
IDP/
└── modules/
    └── rm/
        ├── rm.py
        ├── criteria.py
        └── __init__.py

INPUT JSON
----------
{
    "statement": "Verbatim statement/transcript to analyze.",
    "criterion_annotations": {
        "sensory_information": {
            "observed": true,
            "strength": 0.81,
            "frequency": 3,
            "evidence": ["I heard music", "the room was dark"]
        },
        "clarity_vividness": {
            "observed": true,
            "strength": 0.65,
            "intensity": 2,
            "evidence": ["The speaker gives a vivid description."]
        }
    }
}

Only "statement" is required. criterion_annotations is optional.
Frequency is a count of observed relevant instances, not a probability.
Intensity uses a 0-2 scale for clarity/vividness, reconstructability,
and realism in the research-style operationalization used here.

OUTPUT JSON
-----------
{
    "method": "Reality Monitoring",
    "analysis_type": "evidence_analysis",
    "criteria": {
        "sensory_information": {
            "model_family": "Sporer_Kupper",
            "observed": true,
            "evidence_strength": 0.81,
            "frequency": 3,
            "intensity": null,
            "evidence": ["..."],
            "research_direction": "external_memory_characteristic",
            "finding": {
                "what_was_observed": "...",
                "why_it_matters": "...",
                "what_it_does_not_establish": "..."
            }
        }
    },
    "findings": ["..."],
    "summary": {
        "external_memory_profile": {},
        "internal_memory_profile": {},
        "contextual_profile": {},
        "evidence_profile": "descriptive_only"
    },
    "limitations": ["..."]
}

IMPORTANT
---------
This module does NOT output truthfulness/deception probability, a lie score,
or a diagnostic cutoff. evidence_strength is the strength of the observed
textual characteristic, NOT probability that the memory is true or externally
generated.

RESEARCH BASIS
--------------
Johnson, M. K., & Raye, C. L. (1981). Reality monitoring. Psychological
Review, 88(1), 67–85.
Sporer & Küpper operationalizations of Reality Monitoring.
Masip et al. (2005). The detection of deception with the reality-monitoring
approach: A review of empirical evidence.
Gancedo et al. (2021). A meta-analysis of the reality monitoring approach
to deception detection. European Journal of Psychology Applied to Legal
Context, 13(2), 99–110. DOI: 10.5093/ejpalc2021a10

The implementation is a research-grounded software operationalization,
not an official RM software package.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from .criteria import CRITERIA

LIMITATIONS = [
    "Reality Monitoring is a source-memory framework, not a standalone lie detector.",
    "RM characteristics are probabilistic research signals, not proof of truth or deception.",
    "Different studies operationalize RM criteria differently.",
    "Evidence strength is not a probability of external memory or truthfulness.",
    "Interview conditions, memory quality, event type, language, culture, and individual differences can affect observed features.",
    "A low feature level does not establish fabrication.",
    "A high feature level does not establish truthfulness.",
]


def _annotation(value: Any) -> dict[str, Any]:
    if isinstance(value, bool):
        return {"observed": value, "strength": None, "frequency": None, "intensity": None, "evidence": []}
    if not isinstance(value, Mapping):
        raise TypeError("Each RM annotation must be a bool or object.")
    observed = value.get("observed", value.get("present"))
    if observed is not None and not isinstance(observed, bool):
        raise TypeError("'observed' must be true, false, or null.")
    strength = value.get("strength")
    if strength is not None:
        strength = float(strength)
        if not 0 <= strength <= 1: raise ValueError("'strength' must be between 0 and 1.")
    frequency = value.get("frequency")
    if frequency is not None:
        frequency = int(frequency)
        if frequency < 0: raise ValueError("'frequency' cannot be negative.")
    intensity = value.get("intensity")
    if intensity is not None:
        intensity = int(intensity)
        if intensity not in (0, 1, 2): raise ValueError("'intensity' must be 0, 1, or 2.")
    evidence = value.get("evidence", [])
    if isinstance(evidence, str): evidence = [evidence]
    elif evidence is None: evidence = []
    elif not isinstance(evidence, list): raise TypeError("'evidence' must be a string, list, or null.")
    return {"observed": observed, "strength": strength, "frequency": frequency, "intensity": intensity, "evidence": [str(x) for x in evidence]}


def analyze(statement: str, criterion_annotations: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(statement, str): raise TypeError("statement must be a string.")
    annotations = criterion_annotations or {}
    known = {c["key"] for c in CRITERIA}
    unknown = set(annotations) - known
    if unknown: raise ValueError("Unknown RM criterion(s): " + ", ".join(sorted(unknown)))

    results, findings = {}, []
    for c in CRITERIA:
        key = c["key"]
        item = {"model_family": c["model_family"], "observed": None, "evidence_strength": None, "frequency": None, "intensity": None, "evidence": [], "research_direction": c["research_direction"], "finding": None}
        if key in annotations:
            obs = _annotation(annotations[key])
            item.update({"observed": obs["observed"], "evidence_strength": obs["strength"], "frequency": obs["frequency"], "intensity": obs["intensity"], "evidence": obs["evidence"]})
            if obs["observed"] is True:
                direction = c["research_direction"]
                why = ("This characteristic has been associated in RM research with externally derived/perceptual memories." if direction == "external_memory_characteristic" else "This characteristic has traditionally been associated with internally generated/cognitive memory information." if direction == "internal_memory_characteristic" else "This is a contextual RM characteristic whose empirical discriminative value varies across studies.")
                finding = {"what_was_observed": " ".join(obs["evidence"]) if obs["evidence"] else c["description"], "why_it_matters": why, "what_it_does_not_establish": "It does not establish that the statement is true, false, externally generated, or intentionally fabricated."}
                item["finding"] = finding
                findings.append({"type": "rm_characteristic", "criterion": key, "evidence_strength": obs["strength"], **finding})
        results[key] = item

    external, internal, contextual = {}, {}, {}
    for c in CRITERIA:
        item = results[c["key"]]
        if item["observed"] is not True: continue
        payload = {"evidence_strength": item["evidence_strength"], "frequency": item["frequency"], "intensity": item["intensity"]}
        target = external if c["research_direction"] == "external_memory_characteristic" else internal if c["research_direction"] == "internal_memory_characteristic" else contextual
        target[c["key"]] = payload

    return {"method": "Reality Monitoring", "analysis_type": "evidence_analysis", "criteria": results, "findings": findings, "summary": {"external_memory_profile": external, "internal_memory_profile": internal, "contextual_profile": contextual, "evidence_profile": "descriptive_only"}, "limitations": deepcopy(LIMITATIONS)}
