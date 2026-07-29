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

The Ontario census-subdivision and municipality lookup files contain public
geographic names and codes used for interface labels and filtering. Maintainers
should record the exact upstream dataset, edition, retrieval date, and licence
whenever these lookup files are regenerated. These lookup files contain no CCHS
respondent records.

## Codebook PDFs

Codebook PDFs are local inputs used by the extraction scripts and are not
distributed. `codebooks/*.pdf` is Git-ignored. Analysts must obtain codebooks
from an authorized source and comply with the source terms.
