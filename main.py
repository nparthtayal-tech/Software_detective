"""
INVESTIGATION PIPELINE — Main orchestrator.

Usage:
    python main.py                          # uses statements_input.json
    python main.py  path/to/statements.json # uses custom input

Flow:
    1. Load raw natural-language statements
    2. Call Gemini via nlp_engine to extract structured JSON
    3. Run CBCA + RM on each statement
    4. Build corroboration graph → run PageRank
    5. Build conflict graph → run Greedy MIS
    6. Build temporal precedence graph → run Topological Sort
    7. Compute Entropy on each contested fact
    8. Assemble master_timeline with all metadata
    9. Write output/case_result.json
   10. Generate output/timeline.html
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Any

# Local algorithm imports
from cbca import analyze as cbca_analyze
from rm import analyze as rm_analyze
from conflict_graph_mis import greedy_mis
from pagerank import pagerank
from entropy import calculate_entropy
from topological_sort import topological_sort

import nlp_engine
import timeline_generator


def _now_iso() -> str:
    return datetime.now().isoformat()


def run(input_path: str = "statements_input.json",
        output_dir: str = "output") -> dict[str, Any]:
    """
    Execute the full investigation pipeline.

    Parameters
    ----------
    input_path : str
        Path to a JSON file containing a list of statement dicts.
    output_dir : str
        Directory for output files.

    Returns
    -------
    dict
        The complete case_result.
    """
    # ── 1. Load raw statements ───────────────────────────────────────
    print(f"[1/10] Loading statements from {input_path} ...")
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        raw_statements = data.get("statements", [])
        input_case_id = data.get("case_id")
        input_incident = data.get("incident")
    elif isinstance(data, list):
        raw_statements = data
        input_case_id = None
        input_incident = None
    else:
        raise ValueError("Input must be a non-empty JSON array or a case object with 'statements'.")

    if not raw_statements:
        raise ValueError("No statements found in input.")

    # ── 2. NLP extraction via Gemini ─────────────────────────────────
    print("[2/10] Calling Gemini API for NLP extraction ...")
    extraction = nlp_engine.extract(raw_statements)

    statements_data = extraction.get("statements", {})
    conflicts_data = extraction.get("conflicts", [])
    corroborations_data = extraction.get("corroborations", [])
    contested_facts_data = extraction.get("contested_facts", [])
    precedence_data = extraction.get("precedence", [])

    # ── 3. Run CBCA & RM on each statement ───────────────────────────
    print("[3/10] Running CBCA & RM analysis on each statement ...")
    for stmt_id, stmt in statements_data.items():
        text = stmt.get("statement_text", "")

        # CBCA
        cbca_annots = stmt.get("cbca_annotations", {})
        stmt["cbca_result"] = cbca_analyze(text, cbca_annots)

        # RM
        rm_annots = stmt.get("rm_annotations", {})
        stmt["rm_result"] = rm_analyze(text, rm_annots)

    # ── 4. Collect all event full-IDs ────────────────────────────────
    print("[4/10] Building event graph ...")
    all_event_ids = []
    event_lookup: dict[str, dict[str, Any]] = {}  # full_id → event dict + parent stmt info

    for stmt_id, stmt in statements_data.items():
        for ev in stmt.get("timeline_events", []):
            full_id = f"{stmt_id}.{ev['event_id']}"
            ev["event_full_id"] = full_id
            all_event_ids.append(full_id)
            event_lookup[full_id] = {
                **ev,
                "statement_id": stmt_id,
                "speaker_name": stmt.get("speaker_name", "Unknown"),
                "speaker_role": stmt.get("speaker_role", ""),
            }

    # ── 5. Build corroboration graph → PageRank ──────────────────────
    print("[5/10] Running PageRank on corroboration graph ...")
    pr_edges = []
    for corr in corroborations_data:
        a = corr.get("event_a_id", "")
        b = corr.get("event_b_id", "")
        w = float(corr.get("weight", 1.0))
        if a in event_lookup and b in event_lookup:
            # Bidirectional support.
            pr_edges.append({"source": a, "target": b, "weight": w})
            pr_edges.append({"source": b, "target": a, "weight": w})

    pr_input = {"nodes": all_event_ids, "edges": pr_edges, "damping": 0.85, "iterations": 100}
    pr_result = pagerank(pr_input)

    # ── 6. Build conflict graph → Greedy MIS ─────────────────────────
    print("[6/10] Running Conflict Graph MIS ...")
    conflict_pairs = []
    for conf in conflicts_data:
        a = conf.get("event_a_id", "")
        b = conf.get("event_b_id", "")
        if a in event_lookup and b in event_lookup:
            conflict_pairs.append([a, b])

    mis_statements = [{"id": eid} for eid in all_event_ids]
    mis_input = {"statements": mis_statements, "conflicts": conflict_pairs}
    mis_result = greedy_mis(mis_input)

    selected_set = set(mis_result.get("selected_statements", []))

    # ── 7. Topological Sort ──────────────────────────────────────────
    print("[7/10] Running Topological Sort ...")
    # Filter precedence to valid event IDs.
    valid_precedence = [
        p for p in precedence_data
        if isinstance(p, list) and len(p) == 2
        and p[0] in event_lookup and p[1] in event_lookup
    ]
    topo_input = {"events": all_event_ids, "precedence": valid_precedence}
    topo_result = topological_sort(topo_input)

    # ── 8. Entropy on contested facts ────────────────────────────────
    print("[8/10] Computing Entropy on contested facts ...")
    entropy_results = []
    for cf in contested_facts_data:
        versions = cf.get("versions", {})
        if versions:
            ent = calculate_entropy({"frequencies": versions})
            ent["fact"] = cf.get("fact", "")
            entropy_results.append(ent)

    # ── 9. Assemble master_timeline ──────────────────────────────────
    print("[9/10] Assembling master timeline ...")
    master_timeline = []
    for full_id in all_event_ids:
        ev = event_lookup[full_id]

        # Determine status.
        ev_conflicts = [c for c in conflicts_data
                        if c.get("event_a_id") == full_id or c.get("event_b_id") == full_id]
        ev_corroborations = [c for c in corroborations_data
                             if c.get("event_a_id") == full_id or c.get("event_b_id") == full_id]

        if ev_corroborations and not ev_conflicts:
            status = "corroborated"
        elif ev_conflicts:
            status = "contested"
        else:
            status = "single_source"

        master_timeline.append({
            "event_full_id": full_id,
            "statement_id": ev["statement_id"],
            "speaker_name": ev["speaker_name"],
            "speaker_role": ev["speaker_role"],
            "time_start": ev.get("time_start", "00:00"),
            "time_end": ev.get("time_end", "00:00"),
            "description": ev.get("description", ""),
            "action": ev.get("action", ""),
            "actors": ev.get("actors", []),
            "location": ev.get("location", ""),
            "status": status,
            "in_consistent_set": full_id in selected_set,
            "pagerank_score": pr_result["scores"].get(full_id, 0),
            "conflicts": ev_conflicts,
            "corroborations": ev_corroborations,
        })

    # Sort by time.
    master_timeline.sort(key=lambda e: e.get("time_start", "00:00"))

    # ── 10. Assemble full case result ────────────────────────────────
    case_id = input_case_id or f"CASE-{datetime.now().strftime('%Y-%m%d')}"
    incident = input_incident or "Forensic Investigation"

    case_result = {
        "case_id": case_id,
        "incident": incident,
        "generated_at": _now_iso(),
        "statements": statements_data,
        "cross_analysis": {
            "conflicts": conflicts_data,
            "corroborations": corroborations_data,
            "contested_facts": contested_facts_data,
        },
        "conflict_graph_result": mis_result,
        "pagerank_result": pr_result,
        "topological_sort_result": topo_result,
        "entropy_results": entropy_results,
        "master_timeline": master_timeline,
    }

    # ── Write outputs ────────────────────────────────────────────────
    os.makedirs(output_dir, exist_ok=True)

    result_path = os.path.join(output_dir, "case_result.json")
    print(f"[10/10] Writing {result_path} ...")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(case_result, f, indent=2, ensure_ascii=False)

    timeline_path = os.path.join(output_dir, "timeline.html")
    print(f"        Generating {timeline_path} ...")
    timeline_generator.generate(case_result, timeline_path)

    # Also generate analytical report
    try:
        from report_generator import generate_report
        report_path = os.path.join(output_dir, "report.html")
        generate_report(case_result, report_path)
    except Exception as rep_err:
        print(f"Report generation note: {rep_err}")

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print(f"\n[+] Done! Outputs written to {output_dir}/")
    print(f"   * case_result.json  ({os.path.getsize(result_path):,} bytes)")
    print(f"   * timeline.html     ({os.path.getsize(timeline_path):,} bytes)")
    print(f"\nSummary:")
    print(f"   * Statements analyzed : {len(statements_data)}")
    print(f"   * Timeline events     : {len(master_timeline)}")
    print(f"   * Conflicts detected  : {len(conflicts_data)}")
    print(f"   * Corroborations      : {len(corroborations_data)}")
    print(f"   * Consistent set size : {mis_result.get('size', 0)}")
    print(f"   * Temporal cycles     : {'YES (Cycle)' if topo_result.get('has_cycle') else 'None'}")
    print(f"   * Contested facts     : {len(contested_facts_data)}")

    return case_result


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "statements_input.json"
    run(input_path=path)
