"""Data harmonization functions for multi-cycle CCHS analysis."""

import difflib


def build_crosswalk(cycles: list, descriptions: dict, cutoff: float = 0.6) -> dict:
    """
    Build a crosswalk mapping reference-cycle variable names to each cycle's
    matching variable name, by fuzzy-matching variable descriptions.

    The last entry in `cycles` is treated as the reference cycle: every
    other cycle's variable is matched against each reference variable's
    description via difflib.get_close_matches (single best match). This is
    a heuristic textual match, not an authoritative concordance - unmatched
    or ambiguous descriptions are recorded as None and should be reviewed.

    Args:
        cycles: Cycle years in order, with the reference cycle last
        descriptions: Dict mapping cycle -> {variable_name: description}
        cutoff: difflib similarity cutoff (0-1) for a match to count

    Returns:
        Dict mapping reference_var -> {cycle: cycle_specific_var_or_None}
    """
    reference_cycle = cycles[-1]
    reference_vars = descriptions[reference_cycle]

    crosswalk = {}
    for ref_var, ref_desc in reference_vars.items():
        crosswalk[ref_var] = {reference_cycle: ref_var}
        for cycle in cycles[:-1]:
            candidates = descriptions[cycle]
            best_match = difflib.get_close_matches(ref_desc, candidates.values(), n=1, cutoff=cutoff)
            if best_match:
                for var, desc in candidates.items():
                    if desc == best_match[0]:
                        crosswalk[ref_var][cycle] = var
                        break
            else:
                crosswalk[ref_var][cycle] = None

    return crosswalk


def auto_harmonize(label: str) -> str:
    """
    Normalize a raw codebook category label into a shared harmonized category.

    Order matters: "not stated", "valid skip", "don't know", and "female"
    each contain "no" or "male" as a substring (e.g. "**no**t stated",
    "fe**male**"), so the more specific phrases must be checked before the
    shorter "no"/"male" rules or they get misclassified.
    """
    l = label.lower()
    if "not stated" in l:
        return "Not stated"
    if "valid skip" in l:
        return "Valid skip"
    if "don’t know" in l or "don't know" in l:
        return "Don't know"
    if "female" in l:
        return "Female"
    if "male" in l:
        return "Male"
    if "yes" in l:
        return "Yes"
    if "no" in l:
        return "No"
    return label.strip()


def get_common_harmonized_vars(cycles: list, crosswalk: dict, data_dict: dict) -> list:
    """
    Get harmonized variables that exist in all specified cycles.
    
    Args:
        cycles: List of cycle years
        crosswalk: Crosswalk dictionary
        data_dict: Dictionary mapping cycle -> DataFrame (with cycle-specific column names)
    
    Returns:
        List of harmonized variable names available in all cycles
    """
    common_vars = []
    
    for harmonized_var, cycle_mapping in crosswalk.items():
        available_in_all = True
        for cycle in cycles:
            cycle_specific_var = cycle_mapping.get(cycle)
            if not cycle_specific_var or cycle_specific_var not in data_dict[cycle].columns:
                available_in_all = False
                break
        
        if available_in_all:
            common_vars.append(harmonized_var)
    
    return common_vars

