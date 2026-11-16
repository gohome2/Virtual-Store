"""Verify that each persona has one usable price sensitivity estimate."""

import csv
import re
from math import isfinite
from statistics import mean

from config import DATA_DIR

# Allowed deviation from the assumed target average of 0.50.
TARGET_MEAN = 0.50
MEAN_TOLERANCE = 0.05
CONFIDENCE_LEVELS = {"low", "medium", "high"}


def read_rows(name):
    with (DATA_DIR / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main():
    personas = read_rows("personas.csv")
    traits = read_rows("customer_traits.csv")
    persona_ids = [row["customer_id"] for row in personas]
    trait_ids = [row["customer_id"] for row in traits]
    if len(set(persona_ids)) != len(persona_ids) or len(set(trait_ids)) != len(trait_ids):
        raise SystemExit("Duplicate customer IDs.")
    if set(persona_ids) != set(trait_ids) or not trait_ids:
        raise SystemExit("Customer IDs do not match between the persona and trait files.")

    values = []
    errors = []
    for row in traits:
        customer = row["customer_id"]
        try:
            sensitivity = float(row["price_sensitivity"])
        except ValueError:
            errors.append(f"Customer {customer} has an invalid price sensitivity.")
            continue
        if not isfinite(sensitivity) or not 0 <= sensitivity <= 1:
            errors.append(f"Customer {customer} is outside the 0–1 price sensitivity range.")
        evidence = row["evidence"].strip()
        remaining = re.sub(r"\b(?:age|aged|year|years|old|male|female|man|woman|sex|and|or)\b|[\W\d_]", "", evidence, flags=re.I)
        if not remaining:
            errors.append(f"Customer {customer} needs evidence beyond age or sex.")
        if row["confidence"] not in CONFIDENCE_LEVELS:
            errors.append(f"Customer {customer} has an invalid confidence level.")
        values.append(sensitivity)
    if errors:
        raise SystemExit("\n".join(errors))
    average = mean(values)
    if abs(average - TARGET_MEAN) > MEAN_TOLERANCE + 1e-9:
        raise SystemExit(f"Mean price sensitivity {average:.4f} is outside the target range.")

    low_confidence = sum(row["confidence"] == "low" for row in traits)
    print(f"{len(values)} estimates passed. Range {min(values):.2f}–{max(values):.2f}, mean {average:.4f}.")
    print(f"{low_confidence} estimates have low confidence.")


if __name__ == "__main__":
    main()
