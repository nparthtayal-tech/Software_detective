"""
Investigation Pipeline — Multi-Statement Analysis Orchestrator.

Reads a case_input.json, uses Groq LLM to extract structured data from each
statement, runs all five analysis modules (CBCA, RM, Conflict-Graph-MIS,
PageRank, Entropy), and generates a consolidated JSON result + HTML report.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from copy import deepcopy
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Path setup — allow importing sibling packages
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from cbca.cbca import analyze as cbca_analyze
from cbca.criteria import CRITERIA as CBCA_CRITERIA
from rm.rm import analyze as rm_analyze
from rm.criteria import CRITERIA as RM_CRITERIA
from conflict_graph_mis.algorithm import greedy_mis
from pagerank.algorithm import pagerank as run_pagerank
from entropy.algorithm import calculate_entropy

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"
MAX_RETRIES = 4
RETRY_BASE_DELAY = 2  # seconds


# ═══════════════════════════════════════════════════════════════════════════
# API helpers
# ═══════════════════════════════════════════════════════════════════════════

def load_api_key() -> str:
    """Load GROQ_API_KEY from .env or environment."""
    env_path = ROOT / ".env"
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GROQ_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    os.environ["GROQ_API_KEY"] = key
                    return key
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY not found in .env or environment.")
    return key


def _clean_json_string(raw: str) -> str:
    """Best-effort cleanup of LLM JSON output."""
    # Strip markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE)
    return raw.strip()


def call_groq(api_key: str, messages: list, temperature: float = 0.05,
              max_tokens: int = 8192) -> dict:
    """Call Groq chat completions API with automatic retries."""
    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(
                GROQ_API_URL, data=payload, headers=headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                content = body["choices"][0]["message"]["content"]
                cleaned = _clean_json_string(content)
                return json.loads(cleaned)

        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                wait = RETRY_BASE_DELAY * (2 ** attempt)
                print(f"    ⏳ Rate-limited. Waiting {wait}s …")
                time.sleep(wait)
                continue
            err_body = exc.read().decode("utf-8") if exc.fp else ""
            raise RuntimeError(f"Groq API HTTP {exc.code}: {err_body}") from exc

        except json.JSONDecodeError:
            if attempt < MAX_RETRIES - 1:
                print(f"    ⚠ JSON parse error on attempt {attempt+1}, retrying …")
                time.sleep(RETRY_BASE_DELAY)
                continue
            raise

    raise RuntimeError("Groq API: max retries exceeded.")


# ═══════════════════════════════════════════════════════════════════════════
# Prompt builders
# ═══════════════════════════════════════════════════════════════════════════

def _cbca_criteria_block() -> str:
    lines = []
    for c in CBCA_CRITERIA:
        lines.append(f'  - "{c["key"]}": {c["description"]}')
    return "\n".join(lines)


def _rm_criteria_block() -> str:
    lines = []
    for c in RM_CRITERIA:
        scoring_note = ""
        if c["scoring"] == "intensity_0_2":
            scoring_note = ' (use "intensity": 0, 1, or 2 for this criterion)'
        lines.append(f'  - "{c["key"]}": {c["description"]}{scoring_note}')
    return "\n".join(lines)


def build_extraction_prompt(stmt: dict, incident: str) -> list:
    """Build the chat messages for per-statement extraction."""
    system = (
        "You are an expert forensic statement analyst. "
        "You extract structured data from witness and suspect statements "
        "and return ONLY valid JSON. No commentary, no markdown."
    )
    user = f"""Analyze this statement from an investigation and extract structured information.

CASE: {incident}
STATEMENT BY: {stmt['speaker_name']} (Role: {stmt['speaker_role']})
---
{stmt['statement_text']}
---

Return a JSON object with EXACTLY these three keys:

1. "timeline_events" — array of atomic events mentioned. Each object:
   {{
     "event_id": "E1",
     "description": "brief description",
     "actors": ["person names or descriptions"],
     "location": "place or null",
     "time_start": "HH:MM" (24-hour) or null,
     "time_end": "HH:MM" or null,
     "action": "what happened"
   }}

2. "cbca_annotations" — object mapping each criterion key to an annotation.
   Criteria:
{_cbca_criteria_block()}
   Each annotation:
   {{"present": true/false, "strength": 0.0-1.0, "evidence": ["short quote from statement"]}}
   Mark "present": true ONLY if the statement text contains clear evidence.

3. "rm_annotations" — object mapping each criterion key to an annotation.
   Criteria:
{_rm_criteria_block()}
   Each annotation:
   {{"observed": true/false, "strength": 0.0-1.0, "frequency": integer_count, "intensity": 0_or_1_or_2_or_null, "evidence": ["short quote"]}}
   "intensity" is ONLY used for clarity_vividness, reconstructability, and realism.
   For all other criteria, set "intensity": null.

Return ONLY the JSON object. No extra text."""
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_crossref_prompt(events_by_stmt: dict, incident: str) -> list:
    """Build the chat messages for cross-statement conflict/corroboration detection."""
    system = (
        "You are a forensic analyst cross-referencing multiple witness and "
        "suspect statements. Return ONLY valid JSON."
    )

    event_blocks = []
    for stmt_id, info in events_by_stmt.items():
        lines = [f"### {stmt_id} — {info['speaker_name']} ({info['speaker_role']})"]
        for ev in info["events"]:
            lines.append(
                f"  {stmt_id}.{ev['event_id']}: "
                f"[{ev.get('time_start','?')}–{ev.get('time_end','?')}] "
                f"{ev['description']} | actors: {ev.get('actors',[])} | "
                f"location: {ev.get('location','?')}"
            )
        event_blocks.append("\n".join(lines))

    all_events_text = "\n\n".join(event_blocks)

    user = f"""CASE: {incident}

Here are timeline events extracted from each statement:

{all_events_text}

Return a JSON object with these keys:

1. "conflicts" — array of pairs of events that DIRECTLY CONTRADICT each other.
   Each object:
   {{
     "event_a_id": "STMT_XX.EY",
     "event_b_id": "STMT_XX.EY",
     "fact_category": "vehicle | direction | timing | count | presence | alibi | other",
     "description": "what the contradiction is",
     "version_a": "what speaker A claims",
     "version_b": "what speaker B claims"
   }}

2. "corroborations" — array of pairs of events that SUPPORT each other.
   Each object:
   {{
     "event_a_id": "STMT_XX.EY",
     "event_b_id": "STMT_XX.EY",
     "description": "what they agree on",
     "weight": 0.0-1.0
   }}

3. "contested_facts" — array of key disputed facts across all statements.
   Each object:
   {{
     "fact": "description of the disputed fact",
     "versions": {{"version description": number_of_speakers_supporting_it}}
   }}

Be thorough. Identify ALL contradictions and ALL corroborations.
Return ONLY the JSON object."""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


# ═══════════════════════════════════════════════════════════════════════════
# Pipeline stages
# ═══════════════════════════════════════════════════════════════════════════

def extract_statement(api_key: str, stmt: dict, incident: str) -> dict:
    """Call LLM to extract timeline events, CBCA annotations, RM annotations."""
    messages = build_extraction_prompt(stmt, incident)
    raw = call_groq(api_key, messages)

    events = raw.get("timeline_events", [])
    cbca_ann = raw.get("cbca_annotations", {})
    rm_ann = raw.get("rm_annotations", {})

    # Filter to known keys only
    known_cbca = {c["key"] for c in CBCA_CRITERIA}
    known_rm = {c["key"] for c in RM_CRITERIA}
    cbca_ann = {k: v for k, v in cbca_ann.items() if k in known_cbca}
    rm_ann = {k: v for k, v in rm_ann.items() if k in known_rm}

    return {
        "timeline_events": events,
        "cbca_annotations": cbca_ann,
        "rm_annotations": rm_ann,
    }


def analyze_statement(stmt: dict, extraction: dict) -> dict:
    """Run CBCA and RM analysis on a single statement's extracted annotations."""
    cbca_result = cbca_analyze(
        stmt["statement_text"],
        extraction["cbca_annotations"],
    )
    rm_result = rm_analyze(
        stmt["statement_text"],
        extraction["rm_annotations"],
    )
    return {
        "speaker_name": stmt["speaker_name"],
        "speaker_role": stmt["speaker_role"],
        "statement_text": stmt["statement_text"],
        "statement_id": stmt["id"],
        "timeline_events": extraction["timeline_events"],
        "cbca_result": cbca_result,
        "rm_result": rm_result,
    }


def cross_reference(api_key: str, analyzed: dict, incident: str) -> dict:
    """Detect conflicts and corroborations across all statements."""
    events_by_stmt = {}
    for stmt_id, data in analyzed.items():
        events_by_stmt[stmt_id] = {
            "speaker_name": data["speaker_name"],
            "speaker_role": data["speaker_role"],
            "events": data["timeline_events"],
        }

    messages = build_crossref_prompt(events_by_stmt, incident)
    return call_groq(api_key, messages)


def build_conflict_graph_input(crossref: dict, analyzed: dict) -> dict:
    """Transform cross-ref results into conflict_graph_mis input format."""
    # Each event becomes a "statement" node.
    statements = []
    seen_ids = set()
    for stmt_id, data in analyzed.items():
        for ev in data["timeline_events"]:
            full_id = f"{stmt_id}.{ev['event_id']}"
            if full_id not in seen_ids:
                statements.append({
                    "id": full_id,
                    "text": ev.get("description", ""),
                })
                seen_ids.add(full_id)

    # Build conflict pairs
    conflicts = []
    for c in crossref.get("conflicts", []):
        a, b = c.get("event_a_id", ""), c.get("event_b_id", "")
        if a in seen_ids and b in seen_ids:
            conflicts.append([a, b])

    return {"statements": statements, "conflicts": conflicts}


def build_pagerank_input(crossref: dict, analyzed: dict) -> dict:
    """Transform corroboration edges into pagerank input format."""
    nodes = set()
    for stmt_id, data in analyzed.items():
        for ev in data["timeline_events"]:
            nodes.add(f"{stmt_id}.{ev['event_id']}")

    edges = []
    for c in crossref.get("corroborations", []):
        a, b = c.get("event_a_id", ""), c.get("event_b_id", "")
        w = float(c.get("weight", 0.5))
        if a in nodes and b in nodes:
            edges.append({"source": a, "target": b, "weight": w})
            edges.append({"source": b, "target": a, "weight": w})

    return {"nodes": sorted(nodes), "edges": edges}


def build_entropy_inputs(crossref: dict) -> list[dict]:
    """Build one entropy input per contested fact."""
    results = []
    for cf in crossref.get("contested_facts", []):
        versions = cf.get("versions", {})
        if versions and len(versions) > 1:
            results.append({
                "fact": cf["fact"],
                "input": {"frequencies": versions},
            })
    return results


def build_master_timeline(analyzed: dict, crossref: dict,
                          mis_result: dict, pr_result: dict) -> list:
    """Merge all events into a single sorted master timeline."""
    selected_set = set(mis_result.get("selected_statements", []))
    pr_scores = pr_result.get("scores", {})

    # Index conflicts and corroborations by event ID
    conflict_map: dict[str, list] = {}
    for c in crossref.get("conflicts", []):
        a, b = c.get("event_a_id", ""), c.get("event_b_id", "")
        conflict_map.setdefault(a, []).append(c)
        conflict_map.setdefault(b, []).append(c)

    corr_map: dict[str, list] = {}
    for c in crossref.get("corroborations", []):
        a, b = c.get("event_a_id", ""), c.get("event_b_id", "")
        corr_map.setdefault(a, []).append(c)
        corr_map.setdefault(b, []).append(c)

    timeline = []
    for stmt_id, data in analyzed.items():
        for ev in data["timeline_events"]:
            full_id = f"{stmt_id}.{ev['event_id']}"
            has_conflict = full_id in conflict_map
            has_corr = full_id in corr_map

            if has_conflict:
                status = "contested"
            elif has_corr:
                status = "corroborated"
            else:
                status = "single_source"

            timeline.append({
                "event_full_id": full_id,
                "statement_id": stmt_id,
                "speaker_name": data["speaker_name"],
                "speaker_role": data["speaker_role"],
                "time_start": ev.get("time_start"),
                "time_end": ev.get("time_end"),
                "description": ev.get("description", ""),
                "action": ev.get("action", ""),
                "actors": ev.get("actors", []),
                "location": ev.get("location"),
                "status": status,
                "in_consistent_set": full_id in selected_set,
                "pagerank_score": pr_scores.get(full_id, 0.0),
                "conflicts": conflict_map.get(full_id, []),
                "corroborations": corr_map.get(full_id, []),
            })

    # Sort by time_start (nulls last)
    def sort_key(e):
        t = e.get("time_start") or "99:99"
        return (t, e["statement_id"], e["event_full_id"])

    timeline.sort(key=sort_key)
    return timeline


# ═══════════════════════════════════════════════════════════════════════════
# Main pipeline
# ═══════════════════════════════════════════════════════════════════════════

def run_pipeline(case_path: str | Path) -> dict:
    """Run the full investigation pipeline and return consolidated results."""
    api_key = load_api_key()

    # 1. Load case
    with open(case_path, encoding="utf-8") as f:
        case = json.load(f)

    incident = case.get("incident", "Unknown Incident")
    statements = case["statements"]
    print(f"\n{'='*60}")
    print(f"  INVESTIGATION PIPELINE")
    print(f"  Case: {case.get('case_id', 'N/A')} — {incident}")
    print(f"  Statements: {len(statements)}")
    print(f"{'='*60}\n")

    # 2. Extract + Analyze each statement
    analyzed = {}
    for i, stmt in enumerate(statements):
        sid = stmt["id"]
        print(f"[{i+1}/{len(statements)}] Extracting: {stmt['speaker_name']} ({stmt['speaker_role']}) …")
        extraction = extract_statement(api_key, stmt, incident)
        n_events = len(extraction["timeline_events"])
        n_cbca = sum(1 for v in extraction["cbca_annotations"].values()
                     if isinstance(v, dict) and v.get("present"))
        n_rm = sum(1 for v in extraction["rm_annotations"].values()
                   if isinstance(v, dict) and v.get("observed"))
        print(f"    ✓ {n_events} events, {n_cbca} CBCA criteria, {n_rm} RM criteria")

        result = analyze_statement(stmt, extraction)
        analyzed[sid] = result
        time.sleep(1)  # polite rate spacing

    # 3. Cross-reference
    print(f"\n[Cross-Reference] Detecting conflicts & corroborations …")
    crossref = cross_reference(api_key, analyzed, incident)
    n_conf = len(crossref.get("conflicts", []))
    n_corr = len(crossref.get("corroborations", []))
    n_cf = len(crossref.get("contested_facts", []))
    print(f"    ✓ {n_conf} conflicts, {n_corr} corroborations, {n_cf} contested facts")

    # 4. Conflict Graph — Maximum Independent Set
    print(f"\n[Conflict Graph MIS] Finding maximal consistent narrative …")
    mis_input = build_conflict_graph_input(crossref, analyzed)
    if mis_input["statements"]:
        mis_result = greedy_mis(mis_input)
    else:
        mis_result = {"selected_statements": [], "rejected_statements": [], "size": 0,
                      "algorithm": "Greedy Maximum Independent Set approximation"}
    print(f"    ✓ Selected {mis_result['size']}, rejected {len(mis_result.get('rejected_statements', []))}")

    # 5. PageRank — Corroboration ranking
    print(f"\n[PageRank] Computing evidence support scores …")
    pr_input = build_pagerank_input(crossref, analyzed)
    if pr_input["nodes"] and pr_input["edges"]:
        pr_result = run_pagerank(pr_input)
    else:
        pr_result = {"scores": {n: 0.0 for n in pr_input["nodes"]},
                     "ranking": pr_input["nodes"]}
    print(f"    ✓ Ranked {len(pr_result.get('ranking', []))} event nodes")

    # 6. Entropy — Uncertainty per contested fact
    print(f"\n[Entropy] Measuring uncertainty on contested facts …")
    entropy_inputs = build_entropy_inputs(crossref)
    entropy_results = []
    for ei in entropy_inputs:
        ent = calculate_entropy(ei["input"])
        ent["fact"] = ei["fact"]
        entropy_results.append(ent)
    if entropy_results:
        avg_ent = sum(e["normalized_entropy"] for e in entropy_results) / len(entropy_results)
        print(f"    ✓ {len(entropy_results)} contested facts, avg normalized entropy: {avg_ent:.3f}")
    else:
        print(f"    ✓ No contested facts to measure")

    # 7. Build master timeline
    print(f"\n[Timeline] Building unified master timeline …")
    master_tl = build_master_timeline(analyzed, crossref, mis_result, pr_result)
    print(f"    ✓ {len(master_tl)} events in master timeline")

    # 8. Consolidate results
    result = {
        "case_id": case.get("case_id"),
        "incident": incident,
        "incident_date": case.get("incident_date"),
        "incident_timeframe": case.get("incident_timeframe"),
        "generated_at": datetime.now().isoformat(),

        "statements": analyzed,
        "cross_analysis": crossref,
        "conflict_graph_result": mis_result,
        "pagerank_result": pr_result,
        "entropy_results": entropy_results,
        "master_timeline": master_tl,
    }

    # 9. Save JSON
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    json_path = out_dir / "case_result.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n  💾 JSON saved → {json_path}")

    # 10. Generate HTML report
    from report_generator import generate_report
    html_path = out_dir / "report.html"
    generate_report(result, str(html_path))
    print(f"  📊 HTML report → {html_path}")

    print(f"\n{'='*60}")
    print(f"  ✅ PIPELINE COMPLETE")
    print(f"{'='*60}\n")
    return result


# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    case_file = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "case_input.json")
    run_pipeline(case_file)
