"""Regenerate Ontario geographic lookup JSON from authoritative open data.

The source downloads are pinned by URL and SHA-256 checksum. The script refuses
to generate outputs when a downloaded or supplied source does not match the
recorded checksum.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import unicodedata
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path


@dataclass(frozen=True)
class Source:
    name: str
    filename: str
    url: str
    sha256: str
    reference_date: str
    release_or_update_date: str
    licence: str
    licence_url: str


STATCAN_GAF = Source(
    name="Statistics Canada 2021 Census Geographic Attribute File",
    filename="2021_92-151_X.zip",
    url=(
        "https://www12.statcan.gc.ca/census-recensement/2021/geo/aip-pia/"
        "attribute-attribs/files-fichiers/2021_92-151_X.zip"
    ),
    sha256="918aa8502d9d95b1ae5ce437ed9674e0977ec55977c08b8d01822a9dab6fe5da",
    reference_date="2021-01-01",
    release_or_update_date="2022-02-09",
    licence="Statistics Canada Open Licence",
    licence_url="https://www.statcan.gc.ca/en/terms-conditions/open-licence",
)

ONTARIO_MUNICIPALITIES = Source(
    name="Ontario Ministry of Municipal Affairs and Housing List of municipalities",
    filename="municipalities_-_en_2026-0526.csv",
    url=(
        "https://data.ontario.ca/dataset/62e83cbc-0731-4d66-abdc-2f2b31bcd76c/"
        "resource/6783a586-6b05-4a73-9663-e60a6963c91e/download/"
        "municipalities_-_en_2026-0526.csv"
    ),
    sha256="5370b4e1b3804d10059c67513db9ea59d61bba964096f8e5b35f4a8afd973196",
    reference_date="2026-05-26",
    release_or_update_date="2026-06-03",
    licence="Open Government Licence – Ontario, version 1.0",
    licence_url="https://www.ontario.ca/page/open-government-licence-ontario",
)

INCLUDED_MUNICIPAL_STATUSES = {"Lower Tier", "Single Tier"}
FORMAL_SUFFIX = re.compile(
    r", (?:City|County|Municipality|Town|Township|Village) of$"
)

# These names cannot be resolved solely by removing Ontario's formal suffix and
# comparing the English or French component of the Statistics Canada CSD name.
OFFICIAL_NAME_TO_CSD_CODE = {
    "Prince Edward, County of": "3513020",
    # Ontario shortened the formal municipal name after the 2021 SGC reference date.
    "Tarbutt, Township of": "3557014",
}

FORMAL_TYPE_TO_CSD_TYPES = {
    "City": {"C", "CV", "CY"},
    "County": {"CY"},
    "Municipality": {"M", "MU"},
    "Town": {"T"},
    "Township": {"TP"},
    "Village": {"VL"},
}


class _AnchorTitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "a" or self.title is not None:
            return
        self.title = dict(attrs).get("title")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_source(path: Path, source: Source) -> None:
    actual = sha256_file(path)
    if actual != source.sha256:
        raise ValueError(
            f"Checksum mismatch for {source.name}: expected {source.sha256}, "
            f"received {actual} from {path}"
        )


def download_source(source: Source, cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    destination = cache_dir / source.filename
    if destination.exists():
        verify_source(destination, source)
        return destination

    partial = destination.with_suffix(destination.suffix + ".part")
    with urllib.request.urlopen(source.url) as response, partial.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    verify_source(partial, source)
    partial.replace(destination)
    return destination


def resolve_source(
    source: Source,
    supplied_path: Path | None,
    cache_dir: Path,
) -> Path:
    path = supplied_path if supplied_path is not None else download_source(source, cache_dir)
    verify_source(path, source)
    return path


def load_ontario_csds(gaf_zip: Path) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    with zipfile.ZipFile(gaf_zip) as archive:
        with archive.open("2021_92-151_X.csv") as raw:
            # The GAF is published using the Windows-1252 character set.
            text = io.TextIOWrapper(raw, encoding="cp1252", newline="")
            for row in csv.DictReader(text):
                if row["PRUID_PRIDU"] != "35":
                    continue
                code = row["CSDUID_SDRIDU"]
                record = {
                    "label": f"{row['CSDNAME_SDRNOM']} ({code})",
                    "name": row["CSDNAME_SDRNOM"],
                    "type": row["CSDTYPE_SDRGENRE"],
                }
                previous = records.setdefault(code, record)
                if previous != record:
                    raise ValueError(f"Conflicting Statistics Canada records for CSD {code}")

    if not records:
        raise ValueError("No Ontario census subdivisions found in Statistics Canada source")
    return dict(sorted(records.items()))


def extract_official_name(value: str) -> str:
    parser = _AnchorTitleParser()
    parser.feed(value)
    if not parser.title:
        raise ValueError(f"Municipality cell has no linked title: {value!r}")
    return repair_source_mojibake(parser.title.strip())


def repair_source_mojibake(value: str) -> str:
    """Repair UTF-8 text that the current Ontario CSV stores as Windows-1252."""
    if not any(marker in value for marker in ("Ã", "Â")):
        return value
    try:
        return value.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(character for character in value if not unicodedata.combining(character))
    value = value.casefold().replace("&", " and ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def official_base_name(official_name: str) -> str:
    base = FORMAL_SUFFIX.sub("", official_name)
    if base == "The Nation Municipality":
        return "The Nation"
    return base


def build_csd_name_index(csds: dict[str, dict[str, str]]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for code, record in csds.items():
        names = {record["name"], *record["name"].split(" / ")}
        for name in names:
            index.setdefault(normalize_name(name), set()).add(code)
    return index


def match_csd_code(
    official_name: str,
    csds: dict[str, dict[str, str]],
    name_index: dict[str, set[str]],
) -> str:
    override = OFFICIAL_NAME_TO_CSD_CODE.get(official_name)
    if override is not None:
        if override not in csds:
            raise ValueError(f"Configured CSD override {override} does not exist")
        return override

    base = official_base_name(official_name)
    candidates = name_index.get(normalize_name(base), set())
    formal_type_match = re.search(
        r", (City|County|Municipality|Town|Township|Village) of$", official_name
    )
    if len(candidates) > 1 and formal_type_match:
        expected_types = FORMAL_TYPE_TO_CSD_TYPES[formal_type_match.group(1)]
        candidates = {
            code for code in candidates if csds[code]["type"] in expected_types
        }
    if len(candidates) != 1:
        raise ValueError(
            f"Expected exactly one CSD match for {official_name!r} (base {base!r}); "
            f"found {sorted(candidates)}"
        )
    return next(iter(candidates))


def load_official_municipalities(
    municipalities_csv: Path,
    csds: dict[str, dict[str, str]],
) -> tuple[dict[str, dict[str, str]], dict[str, int]]:
    name_index = build_csd_name_index(csds)
    records: dict[str, dict[str, str]] = {}
    status_counts: dict[str, int] = {}

    with municipalities_csv.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            status = row["Municipal status"].strip()
            status_counts[status] = status_counts.get(status, 0) + 1
            if status not in INCLUDED_MUNICIPAL_STATUSES:
                continue

            official_name = extract_official_name(row["Municipality"])
            code = match_csd_code(official_name, csds, name_index)
            record = {
                "csd_name": csds[code]["name"],
                "geographic_area": row["Geographic area"].strip(),
                "label": f"{official_name} ({code})",
                "municipal_status": status,
                "official_name": official_name,
            }
            if code in records:
                raise ValueError(
                    f"Multiple Ontario municipalities matched Statistics Canada CSD {code}: "
                    f"{records[code]['official_name']!r} and {official_name!r}"
                )
            records[code] = record

    return dict(sorted(records.items())), dict(sorted(status_counts.items()))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write("\n")


def source_provenance(source: Source, retrieved_on: str) -> dict[str, str]:
    return {
        "licence": source.licence,
        "licence_url": source.licence_url,
        "name": source.name,
        "reference_date": source.reference_date,
        "release_or_update_date": source.release_or_update_date,
        "retrieved_on": retrieved_on,
        "sha256": source.sha256,
        "url": source.url,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--statcan-source", type=Path)
    parser.add_argument("--ontario-source", type=Path)
    parser.add_argument(
        "--cache-dir", type=Path, default=Path(".cache/geographic-lookups")
    )
    parser.add_argument("--output-dir", type=Path, default=Path("harmonization"))
    parser.add_argument("--retrieved-on", default=date.today().isoformat())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    statcan_path = resolve_source(STATCAN_GAF, args.statcan_source, args.cache_dir)
    ontario_path = resolve_source(
        ONTARIO_MUNICIPALITIES, args.ontario_source, args.cache_dir
    )

    csds = load_ontario_csds(statcan_path)
    municipalities, source_status_counts = load_official_municipalities(
        ontario_path, csds
    )

    csd_output = args.output_dir / "ontario_csd_lookup.json"
    municipality_output = args.output_dir / "ontario_official_municipalities.json"
    write_json(csd_output, csds)
    write_json(municipality_output, municipalities)

    provenance = {
        "generated_by": "scripts/generate_geographic_lookups.py",
        "generated_on": args.retrieved_on,
        "outputs": {
            str(csd_output): {
                "records": len(csds),
                "sha256": sha256_file(csd_output),
            },
            str(municipality_output): {
                "included_statuses": sorted(INCLUDED_MUNICIPAL_STATUSES),
                "records": len(municipalities),
                "sha256": sha256_file(municipality_output),
                "source_status_counts": source_status_counts,
            },
        },
        "sources": [
            source_provenance(STATCAN_GAF, args.retrieved_on),
            source_provenance(ONTARIO_MUNICIPALITIES, args.retrieved_on),
        ],
        "transformation": (
            "The StatCan GAF was deduplicated to Ontario CSD code, name, and type. "
            "Ontario lower-tier and single-tier municipalities were matched to CSDs "
            "using normalized official names, bilingual StatCan name components, and "
            "the explicit audited override in the generator. Upper-tier records were "
            "excluded because they are not census subdivisions."
        ),
    }
    write_json(args.output_dir / "geographic_lookup_provenance.json", provenance)

    print(f"Wrote {len(csds)} Ontario CSD records to {csd_output}")
    print(
        f"Wrote {len(municipalities)} official municipality records to "
        f"{municipality_output}"
    )


if __name__ == "__main__":
    main()
