import json
from datetime import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from cbca.cbca import analyze as cbca_analyze
from rm.rm import analyze as rm_analyze
from conflict_graph_mis.algorithm import greedy_mis
from pagerank.algorithm import pagerank as run_pagerank
from entropy.algorithm import calculate_entropy
from pipeline import build_conflict_graph_input, build_pagerank_input, build_entropy_inputs, build_master_timeline
from report_generator import generate_report

def run_mock_pipeline():
    # Load case
    case_path = ROOT / "case_input.json"
    with open(case_path, encoding="utf-8") as f:
        case = json.load(f)

    incident = case.get("incident", "Unknown Incident")
    statements = case["statements"]

    # Mock extracted annotations
    extractions = {
        "STMT_01": {
            "timeline_events": [
                {"event_id": "E1", "description": "Closing store", "actors": ["Rajesh"], "location": "Store front", "time_start": "20:55", "time_end": "21:00", "action": "walking"},
                {"event_id": "E2", "description": "Robbers enter", "actors": ["Two masked men", "Rajesh"], "location": "Inside store", "time_start": "21:00", "time_end": "21:04", "action": "robbery"},
                {"event_id": "E3", "description": "Escape in dark SUV", "actors": ["Two masked men"], "location": "Outside store", "time_start": "21:05", "time_end": "21:05", "action": "driving towards Pusa Road"}
            ],
            "cbca_annotations": {
                "logical_structure": {"present": True, "strength": 0.9, "evidence": ["Chronological order of closing shop to robbery."]},
                "quantity_of_details": {"present": True, "strength": 0.85, "evidence": ["Black handle knife", "15-20 necklaces", "dark SUV"]}
            },
            "rm_annotations": {
                "sensory_information": {"observed": True, "strength": 0.9, "frequency": 3, "intensity": None, "evidence": ["glass shattering like car crash", "deep voice western UP accent"]},
                "spatial_information": {"observed": True, "strength": 0.8, "frequency": 2, "intensity": None, "evidence": ["back-room safe to front counter"]}
            }
        },
        "STMT_02": {
            "timeline_events": [
                {"event_id": "E1", "description": "Silver sedan parked", "actors": ["Unknown"], "location": "Outside store", "time_start": "20:50", "time_end": "21:00", "action": "idling"},
                {"event_id": "E2", "description": "Loud crashing sounds", "actors": [], "location": "Next door", "time_start": "21:00", "time_end": "21:02", "action": "glass breaking"},
                {"event_id": "E3", "description": "One man escapes in silver car", "actors": ["One man"], "location": "Outside store", "time_start": "21:03", "time_end": "21:04", "action": "driving towards Ajmal Khan Road"}
            ],
            "cbca_annotations": {
                "contextual_embedding": {"present": True, "strength": 0.7, "evidence": ["doing end-of-day accounts"]},
                "unexpected_complications": {"present": True, "strength": 0.8, "evidence": ["car sitting idling for 10 mins"]}
            },
            "rm_annotations": {
                "affective_information": {"observed": True, "strength": 0.85, "frequency": 1, "intensity": None, "evidence": ["I was scared"]},
                "clarity_vividness": {"observed": True, "strength": 0.7, "frequency": None, "intensity": 1, "evidence": ["medium height, dark clothes, mask"]}
            }
        },
        "STMT_03": {
            "timeline_events": [
                {"event_id": "E1", "description": "Loud glass breaking", "actors": ["Two figures"], "location": "Store window", "time_start": "21:05", "time_end": "21:05", "action": "shouting and breaking"},
                {"event_id": "E2", "description": "Two men escape in dark SUV", "actors": ["Two men"], "location": "Outside store", "time_start": "21:07", "time_end": "21:08", "action": "driving towards Pusa Road"}
            ],
            "cbca_annotations": {
                "related_external_associations": {"present": True, "strength": 0.8, "evidence": ["checked wristwatch to log patrol"]},
                "admitting_lack_of_memory": {"present": True, "strength": 0.9, "evidence": ["couldn't make out faces", "couldn't tell the exact model"]}
            },
            "rm_annotations": {
                "spatial_information": {"observed": True, "strength": 0.75, "frequency": 2, "intensity": None, "evidence": ["distance maybe 25 to 30 meters"]},
                "temporal_information": {"observed": True, "strength": 0.9, "frequency": 2, "intensity": None, "evidence": ["About 2 to 3 minutes later"]}
            }
        },
        "STMT_04": {
            "timeline_events": [
                {"event_id": "E1", "description": "Dinner at Dhaba", "actors": ["Vikram", "Deepak"], "location": "Sharma Dhaba, Rajouri Garden", "time_start": "20:00", "time_end": "22:30", "action": "eating and watching cricket"}
            ],
            "cbca_annotations": {
                "superfluous_details": {"present": True, "strength": 0.8, "evidence": ["butter chicken, dal makhani, and naan", "two glasses of lassi"]},
                "raising_doubts_about_own_testimony": {"present": False, "strength": None, "evidence": []}
            },
            "rm_annotations": {
                "cognitive_operations": {"observed": True, "strength": 0.8, "frequency": 2, "intensity": None, "evidence": ["I think I had two glasses", "we wanted to watch it"]}
            }
        }
    }

    # 2. Analyze
    analyzed = {}
    for stmt in statements:
        sid = stmt["id"]
        ext = extractions[sid]
        analyzed[sid] = {
            "speaker_name": stmt["speaker_name"],
            "speaker_role": stmt["speaker_role"],
            "statement_text": stmt["statement_text"],
            "statement_id": stmt["id"],
            "timeline_events": ext["timeline_events"],
            "cbca_result": cbca_analyze(stmt["statement_text"], ext["cbca_annotations"]),
            "rm_result": rm_analyze(stmt["statement_text"], ext["rm_annotations"]),
        }

    # 3. Cross-reference
    crossref = {
        "conflicts": [
            {
                "event_a_id": "STMT_01.E3",
                "event_b_id": "STMT_02.E3",
                "fact_category": "vehicle | direction | count",
                "description": "Rajesh says 2 men in dark SUV towards Pusa Road, Sunita says 1 man in silver sedan towards Ajmal Khan Road.",
                "version_a": "Two men, dark SUV, Pusa Road",
                "version_b": "One man, silver car, Ajmal Khan Road"
            },
            {
                "event_a_id": "STMT_01.E2",
                "event_b_id": "STMT_04.E1",
                "fact_category": "alibi",
                "description": "Rajesh was robbed by masked men, Vikram claims he was at a Dhaba across town.",
                "version_a": "Robbery occurred at 9:00 PM",
                "version_b": "Vikram was eating dinner at 9:00 PM in Rajouri Garden"
            }
        ],
        "corroborations": [
            {
                "event_a_id": "STMT_01.E2",
                "event_b_id": "STMT_02.E2",
                "description": "Both heard loud glass breaking around 9:00 PM",
                "weight": 0.9
            },
            {
                "event_a_id": "STMT_01.E3",
                "event_b_id": "STMT_03.E2",
                "description": "Both saw two men escape in a dark SUV towards Pusa Road",
                "weight": 0.85
            }
        ],
        "contested_facts": [
            {
                "fact": "Escape vehicle type",
                "versions": {"Dark SUV": 2, "Silver Sedan": 1}
            },
            {
                "fact": "Number of robbers escaping",
                "versions": {"Two men": 2, "One man": 1}
            },
            {
                "fact": "Escape direction",
                "versions": {"Pusa Road": 2, "Ajmal Khan Road": 1}
            }
        ]
    }

    # 4. Conflict Graph MIS
    mis_input = build_conflict_graph_input(crossref, analyzed)
    mis_result = greedy_mis(mis_input) if mis_input["statements"] else {"selected_statements": [], "rejected_statements": [], "size": 0, "algorithm": "Greedy Maximum Independent Set approximation"}

    # 5. PageRank
    pr_input = build_pagerank_input(crossref, analyzed)
    pr_result = run_pagerank(pr_input) if pr_input["nodes"] and pr_input["edges"] else {"scores": {}, "ranking": []}

    # 6. Entropy
    entropy_inputs = build_entropy_inputs(crossref)
    entropy_results = []
    for ei in entropy_inputs:
        ent = calculate_entropy(ei["input"])
        ent["fact"] = ei["fact"]
        entropy_results.append(ent)

    # 7. Timeline
    master_tl = build_master_timeline(analyzed, crossref, mis_result, pr_result)

    # 8. Result
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

    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    json_path = out_dir / "case_result.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    html_path = out_dir / "report.html"
    generate_report(result, str(html_path))
    print(f"Mock pipeline complete! Generated {html_path}")

if __name__ == "__main__":
    run_mock_pipeline()
