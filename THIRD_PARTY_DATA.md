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

- [Standard Geographical Classification (SGC) 2021, Volume I, classification
  structure](https://www.statcan.gc.ca/en/subjects/standard/sgc/2021/index)
- Reference date: January 1, 2021
- Release date: February 9, 2022
- Licence: [Statistics Canada Open
  Licence](https://www.statcan.gc.ca/en/terms-conditions/open-licence)

The repository file contains 577 Ontario census-subdivision records keyed by
seven-digit SGC code. It retains Statistics Canada census-subdivision names and
type abbreviations.

Required source acknowledgment:

> Adapted from Statistics Canada, Standard Geographical Classification (SGC)
> 2021, classification structure, reference date January 1, 2021. This does not
> constitute an endorsement by Statistics Canada of this product.

### Ontario official municipalities

`harmonization/ontario_official_municipalities.json` is an adapted subset of the
Ontario Ministry of Municipal Affairs and Housing:

- [Municipalities dataset, including the "List of municipalities"
  resource](https://data.ontario.ca/en/dataset/municipalities)
- Licence: [Open Government Licence – Ontario,
  version 1.0](https://www.ontario.ca/page/open-government-licence-ontario)

The source dataset provides municipality name, municipal status, and geographic
area. The repository file contains 403 records and adds Statistics Canada SGC
census-subdivision codes and normalized names. It is therefore a value-added
join rather than an unmodified copy of the Ontario resource. The Statistics
Canada acknowledgment above also applies to those incorporated codes and
names.

Required Ontario source acknowledgment:

> Contains information licensed under the Open Government Licence – Ontario.

### Historical snapshot limitation

Both lookup files were introduced into this repository on April 14, 2026. The
commit did not include source URLs, retrieval dates, source-file checksums, or a
generation script. The Ontario catalogue resource is updated over time, so the
exact historical Ontario CSV snapshot used for the existing JSON cannot be
verified from repository history. The source dataset and applicable licences
can be identified with high confidence, but the original download date should
not be represented as known.

When regenerating these files, maintainers should preserve the downloaded source
version and record its URL, retrieval date, checksum, unmatched records, and
transformation procedure.

## Codebook PDFs

Codebook PDFs are local inputs used by the extraction scripts and are not
distributed. `codebooks/*.pdf` is Git-ignored. Analysts must obtain codebooks
from an authorized source and comply with the source terms.
