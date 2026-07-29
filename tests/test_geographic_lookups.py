from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.generate_geographic_lookups import (
    normalize_name,
    official_base_name,
    repair_source_mojibake,
)


HARMONIZATION = Path("harmonization")


def _load_json(filename: str):
    return json.loads((HARMONIZATION / filename).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_name_normalization_supports_official_and_bilingual_names():
    assert official_base_name("Ottawa, City of") == "Ottawa"
    assert official_base_name("The Nation Municipality") == "The Nation"
    assert normalize_name("Rivière des Français") == "riviere des francais"
    assert repair_source_mojibake("Mattice-Val CÃ´tÃ©") == "Mattice-Val Côté"


def test_checked_in_lookup_contract_and_coverage():
    csds = _load_json("ontario_csd_lookup.json")
    municipalities = _load_json("ontario_official_municipalities.json")

    assert len(csds) == 577
    assert len(municipalities) == 414
    assert municipalities.keys() <= csds.keys()

    for code, record in csds.items():
        assert len(code) == 7 and code.startswith("35") and code.isdigit()
        assert record["label"] == f"{record['name']} ({code})"
        assert set(record) == {"label", "name", "type"}

    for code, record in municipalities.items():
        assert record["label"] == f"{record['official_name']} ({code})"
        assert record["csd_name"] == csds[code]["name"]
        assert record["municipal_status"] in {"Lower Tier", "Single Tier"}


def test_provenance_hashes_match_checked_in_outputs():
    provenance = _load_json("geographic_lookup_provenance.json")

    for output_name, metadata in provenance["outputs"].items():
        output = Path(output_name)
        assert output.exists()
        assert metadata["sha256"] == _sha256(output)

    assert all(source["retrieved_on"] for source in provenance["sources"])
    assert all(source["sha256"] for source in provenance["sources"])
