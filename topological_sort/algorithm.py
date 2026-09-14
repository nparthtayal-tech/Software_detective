"""
TOPOLOGICAL SORT WITH CYCLE DETECTION (KAHN'S ALGORITHM)

INPUT (JSON):
- "events": a list of unique event IDs.
- "precedence": a list of [before, after] pairs. Each pair means the first event
  must have occurred before the second event.

Example:
{
    "events": ["E1", "E2", "E3", "E4"],
    "precedence": [["E1", "E2"], ["E2", "E3"], ["E1", "E4"]]
}

OUTPUT (JSON):
- topological_order: the events ordered so that every "before" event comes first.
  When the graph has no precedence constraint between two events they are ordered
  by their ID for determinism.
- has_cycle: true when two or more precedence constraints create a logical loop
  (e.g. A before B AND B before A). A cycle means the timeline contains a
  temporal contradiction.
- cycle_edges: the subset of precedence pairs that participate in at least one
  cycle. Empty when has_cycle is false.
- algorithm: identifies this as Kahn's BFS-based topological sort.

IMPORTANT:
A cycle does NOT prove deception. It means the stated temporal ordering is
internally inconsistent and warrants further investigation.

GRAPH THEORY BASIS:
Kahn, A. B. (1962). Topological sorting of large networks.
Communications of the ACM, 5(11), 558–562.
"""

import json
import sys
from collections import defaultdict, deque


def topological_sort(data):
    events = data.get("events", [])
    precedence = data.get("precedence", [])

    if not isinstance(events, list) or not events:
        raise ValueError("'events' must be a non-empty list.")
    if not isinstance(precedence, list):
        raise ValueError("'precedence' must be a list of [before, after] pairs.")
    if len(events) != len(set(events)):
        raise ValueError("Event IDs must be unique.")

    event_set = set(events)

    # Build adjacency list and in-degree map.
    adj = defaultdict(list)
    in_degree = {e: 0 for e in events}

    for pair in precedence:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError("Each precedence entry must be [before, after].")
        before, after = pair
        if before not in event_set or after not in event_set:
            raise ValueError(f"Unknown event in precedence: {pair}")
        if before == after:
            raise ValueError("An event cannot precede itself.")
        adj[before].append(after)
        in_degree[after] += 1

    # --- Kahn's algorithm (BFS topological sort) ---
    # Use a sorted container so that when multiple events have in_degree 0
    # the output is deterministic (alphabetical by ID).
    queue = deque(sorted(e for e in events if in_degree[e] == 0))
    order = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbour in sorted(adj[node]):
            in_degree[neighbour] -= 1
            if in_degree[neighbour] == 0:
                queue.append(neighbour)
        # Re-sort to keep deterministic ordering among newly freed nodes.
        queue = deque(sorted(queue))

    has_cycle = len(order) != len(events)

    # Identify the edges that participate in cycle(s).
    cycle_edges = []
    if has_cycle:
        remaining = {e for e in events if e not in set(order)}
        for pair in precedence:
            if pair[0] in remaining and pair[1] in remaining:
                cycle_edges.append(pair)

    return {
        "topological_order": order,
        "has_cycle": has_cycle,
        "cycle_edges": cycle_edges,
        "algorithm": "Kahn's topological sort (BFS)",
    }


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else "input.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "output.json"

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = topological_sort(data)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    print(json.dumps(result, indent=4))


if __name__ == "__main__":
    main()
