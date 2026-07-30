# CCHS Bootstrap Analysis Tool

A local Streamlit application for public health analysts and epidemiologists who
work with Canadian Community Health Survey (CCHS) data. It supports geographic
filtering, bootstrap prevalence estimates, CCHS release-quality indicators,
age-stratified analysis, exports, and comparisons across annual cycles.

!!! warning "Project status"
    This is a public-health-unit analytical tool under active validation. It is
    not an official Statistics Canada product. Analysts remain responsible for
    following their CCHS data-sharing agreements, organizational privacy
    policies, and applicable release standards.

## Analysis modes

- **Single Cycle** calculates estimates for one CCHS year.
- **Multi-Cycle Trends** calculates each selected year independently and compares
  the resulting estimates across years.

Multi-Cycle Trends does **not** pool respondent-level records or weights across
cycles. Cycle pooling is a requested future feature and will require a
separately validated statistical design before implementation.

Supported configurations currently include CCHS 2021, 2022, 2023, and 2024.

## Bring your own data

The repository does not distribute CCHS respondent data, bootstrap weights, or
codebook PDFs. Public health units run the application locally with files they
are authorized to use - see the [README](https://github.com/WDGPH/CCHS#bring-your-own-data)
for the exact file layout expected under `data/`.

## Get started

<div class="grid cards" markdown>

- :material-source-branch: **Adding a cycle**

    ---

    Bring a new CCHS survey year online: raw data, codebook extraction,
    crosswalk regeneration, and precomputation.

    [:octicons-arrow-right-24: Adding a New CCHS Cycle](ADDING_A_CYCLE.md)

- :material-chart-bell-curve: **Bootstrap methodology**

    ---

    How weighted prevalence, confidence intervals, and CCHS release-quality
    categories are calculated.

    [:octicons-arrow-right-24: Bootstrap Methodology](bootstrap_analysis_documentation.md)

- :material-shield-check: **Data quality and privacy**

    ---

    CCHS 2024 release standards and the privacy/security practices this tool
    follows when handling respondent-level data.

    [:octicons-arrow-right-24: Data Quality and Privacy](CCHS_2024_Data_Quality_Standards.md)

- :material-scale-balance: **Third-party data and licensing**

    ---

    What's distributed with this repository, what each organization must
    obtain under its own CCHS agreement, and how the MIT license applies.

    [:octicons-arrow-right-24: Third-Party Data and Licensing](THIRD_PARTY_DATA.md)

- :material-code-braces: **Code reference**

    ---

    Generated API documentation for the harmonization, data-loading, and
    bootstrap-analysis modules.

    [:octicons-arrow-right-24: Code Reference](reference.md)

- :material-account-group: **Contributing**

    ---

    How to propose changes, the review process, and the project's security
    and conduct policies.

    [:octicons-arrow-right-24: Contributing](CONTRIBUTING.md)

</div>

## Statistical outputs

For each variable value, the tool reports:

- weighted prevalence and population
- unweighted numerator and denominator
- bootstrap variance and standard error
- confidence interval using the documented CCHS `z = 2.0` convention
- coefficient of variation
- CCHS 2022+ A/E/F release category and action

Release flags are displayed by default for supported 2022+ cycles. Analysts
should suppress category F estimates and apply their organization's complete
review and rounding process before publication.

## Repository structure

```text
app.py                 Streamlit entry point
config/                Application and analysis settings
src/analysis/           Bootstrap and quality calculations
src/data/               Loading, harmonization, and preprocessing
src/ui/                 Streamlit interface components
harmonization/          Cycle metadata, crosswalks, and lookup tables
scripts/                Local conversion and precompute utilities
tests/                  Synthetic-data tests
```

## License

Project code is licensed under the MIT License. See
[Third-Party Data and Licensing](THIRD_PARTY_DATA.md) for the terms that
govern CCHS data and third-party metadata, which the project license does not
replace.
