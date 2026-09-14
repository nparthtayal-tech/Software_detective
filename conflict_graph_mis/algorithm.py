"""
CONFLICT GRAPH + MAXIMUM INDEPENDENT SET (GREEDY APPROXIMATION)

INPUT (JSON):
- "statements": a list of statement objects. Each object needs a unique "id"
  and may contain the statement text in "text".
- "conflicts": a list of pairs [id1, id2]. Each pair means the two statements
  mutually conflict.

Example:
{
    "statements": [
        {"id": "S1", "text": "The meeting happened on Monday."},
        {"id": "S2", "text": "The meeting happened on Tuesday."},
        {"id": "S3", "text": "The meeting was held online."}
    ],
    "conflicts": [["S1", "S2"]]
}

OUTPUT (JSON):
- selected_statements: a conflict-free set produced by the greedy MIS algorithm.
- rejected_statements: statements not selected because they conflicted with a
  selected statement.
- size: number of selected statements.
- algorithm: identifies this as a greedy approximation, because exact Maximum
  Independent Set is NP-hard for general graphs.

IMPORTANT:
This algorithm does NOT detect contradictions from raw text by itself. The
"conflicts" list must already identify which statements conflict.
"""

import json
import sys
from collections import defaultdict


def greedy_mis(data):
    statements = data.get("statements", [])
    conflicts = data.get("conflicts", [])

    if not isinstance(statements, list) or not statements:
        raise ValueError("'statements' must be a non-empty list.")
    if not isinstance(conflicts, list):
        raise ValueError("'conflicts' must be a list of [id1, id2] pairs.")

    ids = [item.get("id") for item in statements]
    if any(not node_id for node_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("Every statement must have a unique non-empty 'id'.")

    graph = defaultdict(set)
    for node_id in ids:
        graph[node_id]

    for pair in conflicts:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError("Each conflict must be [id1, id2].")
        a, b = pair
        if a not in graph or b not in graph:
            raise ValueError(f"Unknown statement id in conflict: {pair}")
        if a == b:
            raise ValueError("A statement cannot conflict with itself.")
        graph[a].add(b)
        graph[b].add(a)

    # Greedy heuristic: choose the lowest-degree remaining node first.
    remaining = set(ids)
    selected = []

    while remaining:
        node = min(remaining, key=lambda x: (len(graph[x] & remaining), x))
        selected.append(node)
        remaining.remove(node)
        remaining -= graph[node]

    selected_set = set(selected)
    rejected = [node_id for node_id in ids if node_id not in selected_set]

    return {
        "selected_statements": selected,
        "rejected_statements": rejected,
        "size": len(selected),
        "algorithm": "Greedy Maximum Independent Set approximation"
    }


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else "input.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "output.json"

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = greedy_mis(data)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    print(json.dumps(result, indent=4))


if __name__ == "__main__":
    main()
