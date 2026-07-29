from __future__ import annotations

import json
import tomllib

from src.data.precompute import check_precompute_status, load_precomputed_metadata


def test_streamlit_is_local_and_telemetry_is_disabled():
    with open(".streamlit/config.toml", "rb") as config_file:
        config = tomllib.load(config_file)

    assert config["browser"]["gatherUsageStats"] is False
    assert config["server"]["address"] == "127.0.0.1"


def test_precomputed_metadata_uses_json(tmp_path):
    metadata = {
        "cycle": "2024",
        "available_vars": ["GEN_005"],
        "record_count": 10,
    }
    metadata_path = tmp_path / "metadata_2024.json"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    assert load_precomputed_metadata("2024", tmp_path) == metadata


def test_precompute_status_requires_data_bootstrap_and_json_metadata(tmp_path):
    (tmp_path / "harmonized_data_2024.parquet").touch()
    (tmp_path / "harmonized_bootstrap_2024.parquet").touch()
    (tmp_path / "metadata_2024.json").write_text("{}", encoding="utf-8")

    assert check_precompute_status(["2024"], tmp_path) == {"2024": True}

    (tmp_path / "harmonized_bootstrap_2024.parquet").unlink()
    assert check_precompute_status(["2024"], tmp_path) == {"2024": False}
