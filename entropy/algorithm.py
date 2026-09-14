"""
ENTROPY ALGORITHM

INPUT (JSON):
- Provide either:
  1. "probabilities": a list of probabilities that sum approximately to 1, OR
  2. "frequencies": a dictionary mapping outcomes/categories to non-negative counts.

Example:
{
    "frequencies": {
        "A": 40,
        "B": 30,
        "C": 20,
        "D": 10
    }
}

OUTPUT (JSON):
- entropy: Shannon entropy in bits.
- normalized_entropy: entropy divided by log2(number of outcomes), when possible.
- interpretation: simple descriptive interpretation of uncertainty.

NOTE:
This measures uncertainty/distributional diversity. It is NOT a truth/lie detector.
"""

import json
import math
import sys


def calculate_entropy(data):
    if "probabilities" in data:
        probabilities = data["probabilities"]
        if not isinstance(probabilities, list) or not probabilities:
            raise ValueError("'probabilities' must be a non-empty list.")
        if any(not isinstance(p, (int, float)) or p < 0 for p in probabilities):
            raise ValueError("Probabilities must be non-negative numbers.")
        total = sum(probabilities)
        if total <= 0:
            raise ValueError("Probability total must be greater than 0.")
        probabilities = [p / total for p in probabilities]

    elif "frequencies" in data:
        frequencies = data["frequencies"]
        if not isinstance(frequencies, dict) or not frequencies:
            raise ValueError("'frequencies' must be a non-empty object.")
        values = list(frequencies.values())
        if any(not isinstance(v, (int, float)) or v < 0 for v in values):
            raise ValueError("Frequencies must be non-negative numbers.")
        total = sum(values)
        if total <= 0:
            raise ValueError("Frequency total must be greater than 0.")
        probabilities = [v / total for v in values if v > 0]
    else:
        raise ValueError("Input must contain either 'probabilities' or 'frequencies'.")

    entropy = -sum(p * math.log2(p) for p in probabilities if p > 0)
    n = len(probabilities)
    normalized = entropy / math.log2(n) if n > 1 else 0.0

    if normalized < 0.33:
        interpretation = "Low uncertainty / concentrated distribution"
    elif normalized < 0.67:
        interpretation = "Moderate uncertainty"
    else:
        interpretation = "High uncertainty / distributed outcomes"

    return {
        "entropy": round(entropy, 6),
        "normalized_entropy": round(normalized, 6),
        "interpretation": interpretation,
    }


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else "input.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "output.json"

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = calculate_entropy(data)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    print(json.dumps(result, indent=4))


if __name__ == "__main__":
    main()
