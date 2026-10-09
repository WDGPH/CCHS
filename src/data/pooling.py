"""Population requirements for pooling supported annual CCHS cycles."""

import numpy as np
import pandas as pd

from config.settings import POOLING_CYCLE_POLICIES


def get_pooling_policy(cycles, geography_filtered=False):
    cycles = sorted({str(cycle).strip() for cycle in cycles})
    unknown = sorted(set(cycles) - set(POOLING_CYCLE_POLICIES))
    if unknown or not cycles:
        raise ValueError("Pooling population policy is unavailable for cycle(s): " + ", ".join(unknown))
    policies = [POOLING_CYCLE_POLICIES[cycle] for cycle in cycles]
    reasons = []
    if len({policy["design"] for policy in policies}) > 1:
        reasons.append(
            "The selected years cross the 2022 survey redesign. Review collection "
            "methods, question universes, and survey concepts before combining them."
        )
    if geography_filtered and len({policy["csd_vintage"] for policy in policies}) > 1:
        reasons.append(
            "The selected years use different census geography vintages. Confirm "
            "that your selected boundaries represent the same population, or "
            "harmonize the geographic codes before pooling."
        )
    return {
        "minimum_age": max(policy["minimum_age"] for policy in policies),
        "review_reasons": reasons,
    }


def prepare_pooling_population(data, cycles, *, reviewed=False, geography_filtered=False):
    """Apply the common age population, rejecting unreviewed known breaks."""
    policy = get_pooling_policy(cycles, geography_filtered)
    if policy["review_reasons"] and not reviewed:
        raise ValueError("Complete the survey-design/geography compatibility review before pooling.")
    age_column = next((column for column in ["AWCAGE", "DHH_AGE"] if column in data), None)
    if age_column is None:
        raise ValueError("Pooling requires respondent age to enforce a common target population.")
    ages = pd.to_numeric(data[age_column], errors="coerce")
    if ages.isna().any() or not np.isfinite(ages.to_numpy(dtype=float)).all():
        raise ValueError("Pooling requires complete, finite numeric respondent ages.")
    if "CYCLE" not in data:
        raise ValueError("Pooling requires a CYCLE column to validate the common population.")
    result = data.loc[ages >= policy["minimum_age"]].copy()
    result[age_column] = ages.loc[result.index]
    expected = {str(cycle).strip() for cycle in cycles}
    observed = set(result["CYCLE"].dropna().astype(str).str.strip())
    if observed != expected:
        raise ValueError(
            "Every selected cycle must retain records in the common age population "
            f"({policy['minimum_age']}+). Missing: " + ", ".join(sorted(expected - observed))
            + "; unexpected: " + ", ".join(sorted(observed - expected)) + "."
        )
    return result


def annotate_pooling_population(results, policy):
    """Record the population scope and required review in analysis exports."""
    results["Population Minimum Age"] = policy["minimum_age"]
    results["Compatibility Review"] = (
        "Required analyst review completed" if policy["review_reasons"]
        else "No configured design/geography review trigger"
    )
    return results
