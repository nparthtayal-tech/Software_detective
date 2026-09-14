"""
PAGERANK-STYLE NODE RANKING ALGORITHM

INPUT (JSON):
- "nodes": a list of unique node IDs.
- "edges": a list of directed edges with:
    "source": source node ID
    "target": target node ID
    "weight": optional non-negative connection strength (default = 1.0)
- Optional "damping": PageRank damping factor, normally 0.85.
- Optional "iterations": number of iterations, normally 100.

Example:
{
    "nodes": ["A", "B", "C", "D"],
    "edges": [
        {"source": "A", "target": "B", "weight": 1.0},
        {"source": "A", "target": "C", "weight": 2.0},
        {"source": "B", "target": "C", "weight": 1.0},
        {"source": "C", "target": "D", "weight": 1.0}
    ],
    "damping": 0.85,
    "iterations": 100
}

OUTPUT (JSON):
- scores: PageRank-style importance score for every node.
- ranking: nodes ordered from highest to lowest score.

INTERPRETATION:
A node receives more rank when important nodes point toward it. In a forensic
application, the score should be interpreted as graph-based importance or
support, NOT as proof that a statement is true.
"""

import json
import sys


def pagerank(data):
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    damping = float(data.get("damping", 0.85))
    iterations = int(data.get("iterations", 100))

    if not nodes or len(nodes) != len(set(nodes)):
        raise ValueError("'nodes' must be a non-empty list of unique IDs.")
    if not 0 < damping < 1:
        raise ValueError("'damping' must be between 0 and 1.")
    if iterations <= 0:
        raise ValueError("'iterations' must be greater than 0.")

    node_set = set(nodes)
    outgoing = {node: [] for node in nodes}

    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        weight = float(edge.get("weight", 1.0))

        if source not in node_set or target not in node_set:
            raise ValueError(f"Unknown node in edge: {edge}")
        if weight < 0:
            raise ValueError("Edge weights must be non-negative.")

        outgoing[source].append((target, weight))

    n = len(nodes)
    scores = {node: 1.0 / n for node in nodes}

    for _ in range(iterations):
        new_scores = {node: (1 - damping) / n for node in nodes}

        # Standard dangling-node handling: distribute its rank equally.
        dangling_rank = sum(
            scores[node] for node in nodes if not outgoing[node]
        )
        dangling_share = damping * dangling_rank / n
        for node in nodes:
            new_scores[node] += dangling_share

        for source in nodes:
            if not outgoing[source]:
                continue

            total_weight = sum(weight for _, weight in outgoing[source])
            if total_weight == 0:
                continue

            for target, weight in outgoing[source]:
                new_scores[target] += (
                    damping * scores[source] * weight / total_weight
                )

        scores = new_scores

    ranking = sorted(scores, key=lambda node: (-scores[node], node))

    return {
        "scores": {node: round(scores[node], 6) for node in nodes},
        "ranking": ranking
    }


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else "input.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "output.json"

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = pagerank(data)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    print(json.dumps(result, indent=4))


if __name__ == "__main__":
    main()
