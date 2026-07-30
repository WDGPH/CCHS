# Third-Party Data and Metadata

## CCHS respondent data and bootstrap weights

This repository does not distribute CCHS respondent-level data, bootstrap
weights, or derived respondent-level datasets. Each organization must obtain and
use its files under its own authorization and applicable Statistics Canada or
provincial data-sharing terms.

The MIT license in this repository applies to project code. It does not grant
rights to CCHS microdata supplied separately by an analyst or organization.

## CCHS harmonization metadata

Files named `harmonization/CCHS_<year>.json`, `categories.json`, and
`crosswalk.json` contain variable descriptions, category labels, and mappings
derived from cycle-specific CCHS documentation and local harmonization review.
They do not contain respondent records or frequencies.

Primary survey documentation is available from Statistics Canada:

- <https://www.statcan.gc.ca/en/survey/household/3226>
- <https://www23.statcan.gc.ca/imdb/p2SV.pl?Function=getSurvey&SDDS=3226>

Before redistribution, maintainers should confirm that each derived metadata
file remains consistent with the source documentation and its applicable terms.

## Geographic lookup metadata

The geographic lookup files contain public names, classifications, and codes
used for interface labels and filtering. They contain no CCHS respondent
records. They are adapted third-party data and are not licensed solely under
the repository's MIT license.

### Ontario census subdivisions

`harmonization/ontario_csd_lookup.json` is an Ontario subset and JSON adaptation
of Statistics Canada's:

- [2021 Census Geographic Attribute
  File](https://www12.statcan.gc.ca/census-recensement/2021/geo/aip-pia/attribute-attribs/index2021-eng.cfm)
- Reference date: January 1, 2021
- Release date: February 9, 2022
- Retrieved: July 29, 2026
- Licence: [Statistics Canada Open
  Licence](https://www.statcan.gc.ca/en/terms-conditions/open-licence)

The repository file contains 577 Ontario census-subdivision records keyed by
seven-digit SGC code. It retains Statistics Canada census-subdivision names and
type abbreviations.

Required source acknowledgment:

> Adapted from Statistics Canada, 2021 Census Geographic Attribute File,
> reference date January 1, 2021. This does not constitute an endorsement by
> Statistics Canada of this product.

### Ontario official municipalities

`harmonization/ontario_official_municipalities.json` is an adapted subset of the
Ontario Ministry of Municipal Affairs and Housing:

- [Municipalities dataset, including the "List of municipalities"
  resource](https://data.ontario.ca/en/dataset/municipalities)
- Source-file date: May 26, 2026
- Catalogue update date: June 3, 2026
- Retrieved: July 29, 2026
- Licence: [Open Government Licence – Ontario,
  version 1.0](https://www.ontario.ca/page/open-government-licence-ontario)

The source dataset provides municipality name, municipal status, and geographic
area. The repository file contains all 414 lower-tier and single-tier records
from the pinned source and adds Statistics Canada census-subdivision codes and
normalized names. The 30 upper-tier source records are excluded because they
are not census subdivisions. This is therefore a value-added join rather than
an unmodified copy of the Ontario resource. The Statistics Canada acknowledgment
above also applies to the incorporated codes and names.

Required Ontario source acknowledgment:

> Contains information licensed under the Open Government Licence – Ontario.

### Reproducibility

The lookups were regenerated on July 29, 2026, replacing earlier JSON whose
exact source snapshots had not been recorded. Exact source URLs, dates, SHA-256
checksums, output checksums, record counts, and the transformation summary are
stored in `harmonization/geographic_lookup_provenance.json`.

Regenerate and verify the files with:

```bash
uv run python scripts/generate_geographic_lookups.py
uv run pytest -q tests/test_geographic_lookups.py
```

The generator pins both downloads by checksum, repairs a documented encoding
defect in the current Ontario CSV, rejects missing or ambiguous matches, and
records explicit cross-vintage name overrides. To adopt a newer Ontario source
or future Statistics Canada geography, update the source URL, checksum, dates,
and any reviewed name mappings together.

## Codebook PDFs

Codebook PDFs are local inputs used by the extraction scripts and are not
distributed. `codebooks/*.pdf` is Git-ignored. Analysts must obtain codebooks
from an authorized source and comply with the source terms.
