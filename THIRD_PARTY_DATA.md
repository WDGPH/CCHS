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
`crosswalk.json` are **not distributed with this repository** and are Git-ignored
(see `.gitignore`). They contain variable descriptions, category labels, and
mappings extracted or derived from cycle-specific CCHS codebook documentation,
and the codebook itself is typically supplied to each organization under a
Statistics Canada or provincial CCHS data-sharing agreement rather than the
Statistics Canada Open Licence. Rather than resolve that licensing question on
every organization's behalf, this repository ships only the extraction and
harmonization **code** - each organization generates its own copies locally
from its own authorized codebook.

To regenerate these files, see [Adding a New CCHS Cycle](ADDING_A_CYCLE.md):

- `scripts/extract_codebook.py` parses variable names, concept descriptions,
  and answer-category tables out of a local
  `codebooks/CCHS_<year>_DataDictionary_Freqs.pdf` (also Git-ignored) into
  `harmonization/CCHS_<year>.json`. PDF text extraction can introduce ligature
  artifacts in descriptions (e.g. "file" rendered as "ﬁle") and is not
  guaranteed to produce perfect category mappings - review output before use.
- `scripts/build_crosswalk.py` matches the most recent cycle's variables to
  the closest-matching variable description in each earlier cycle using
  fuzzy string matching (`difflib`, cutoff 0.6) to produce `crosswalk.json`.
  This is a heuristic concordance, not an authoritative Statistics Canada
  mapping - unmatched or ambiguous variables are recorded as `null` and
  should be verified manually.
- `scripts/harmonize_categories.py` builds `categories.json` on top of
  `crosswalk.json`, normalizing category labels (e.g.
  "Yes"/"No"/"Valid skip"/"Don't know"/"Male"/"Female") across cycles with
  simple keyword rules. Labels that do not match a rule pass through
  unchanged.

None of these generated files contain respondent records, frequencies, or
weights - only variable-level metadata. Before relying on them, or
redistributing your own generated copies, confirm they remain consistent with
your codebook's source documentation and the terms under which your
organization obtained it.

Primary survey documentation is available from Statistics Canada:

- Canadian Community Health Survey (CCHS) - Annual Component, Statistics
  Canada Survey number 3226
- <https://www.statcan.gc.ca/en/survey/household/3226>
- <https://www23.statcan.gc.ca/imdb/p2SV.pl?Function=getSurvey&SDDS=3226>

If your codebook was sourced from a Statistics Canada Public Use Microdata
File (PUMF) release, that documentation is covered by the Statistics Canada
Open Licence, and the following acknowledgment applies to any metadata you
derive from it and choose to redistribute:

> Adapted from Statistics Canada, Canadian Community Health Survey (CCHS),
> Annual Component, cycle-specific Data Dictionary and Frequencies
> documentation. This does not constitute an endorsement by Statistics Canada
> of this product.

Note that CCHS PUMF releases use a smaller, disclosure-controlled variable
set than the full annual-component share file (for example, StatCan's 2022
PUMF data dictionary lists roughly 255 variables, versus several hundred in
a typical share-file extract), so a PUMF-derived cycle file will not match
one generated from a share-file codebook variable-for-variable.

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
