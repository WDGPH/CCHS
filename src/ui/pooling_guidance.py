"""Explain the pooled estimand, source guidance, and variance assumptions."""

import streamlit as st


def display_pooling_guidance(selected_cycles):
    """Show source-linked guidance alongside the user's selected cycles."""
    cycles = sorted(str(cycle) for cycle in selected_cycles)
    count = len(cycles)
    st.info(
        "Cycle Pooling gives one estimate for the selected survey years together. "
        "Open the guidance below for a worked example, the method, and its sources."
    )
    with st.expander("How Cycle Pooling works — guidance and sources"):
        st.caption(
            f"Selected years: {', '.join(cycles)}. Main and bootstrap weights "
            f"from each year are divided by {count}."
        )
        meaning, method, interpretation = st.tabs([
            "Meaning and example", "Method and sources", "Interpreting results"
        ])
        with meaning:
            st.markdown("""
**What question does this answer?**

“Across these survey years, what proportion of the population had this
characteristic?” Each survey respondent represents people through their survey
weight. Pooling combines those weighted records into one period estimate. It can
help when an individual year's sample is too small for the group of interest.

**Why divide the weights?**

Adding annual population totals counts several years of population together.
Dividing each year's weights by the number of selected years makes the reported
population an average annual population over those years.

**Illustration only: two fictional years**

| Weighted estimate | Year A | Year B | Pooled period |
| --- | ---: | ---: | ---: |
| People in the response domain | 1,000 | 1,200 | 1,100 |
| People with the characteristic | 200 | 360 | 280 |
| Prevalence | 20% | 30% | 25.45% |

The pooled population is `(1,000 + 1,200) / 2 = 1,100`; the characteristic
total is `(200 + 360) / 2 = 280`. Prevalence is `280 / 1,100 × 100 = 25.45%`.
Annual population sizes affect the result: averaging the two percentages would
give 25%. Dividing all weights by the same number changes population totals but
leaves their ratio unchanged.

These are weighted population estimates, not counts of interviewed respondents.
The pooled estimate describes the selected years together; use **Multi-Cycle
Trends** to see year-to-year changes.
""")
        with method:
            st.markdown("""
**Where does the weighting approach come from?**

**Recent official guidance and applications**

- [CCHS 2024 methodology](https://www23.statcan.gc.ca/imdb/p2SV.pl?Function=getSurvey&Id=1531795),
  **Description**: users can combine collection years with consistent design
  and population representation to study smaller populations or rare characteristics.
- [Islam and Gilmour, *Mood disorders among older Canadians* (17 December 2025)](https://www150.statcan.gc.ca/n1/pub/82-003-x/2025012/article/00002-eng.htm),
  **Analytical approach**: Statistics Canada combines nine annual cycles
  (2015–2023), rescales both sampling and bootstrap weights by a factor of nine,
  and interprets estimates as the average population over those years.
- [Islam and Gilmour, *Anxiety disorders among older Canadians* (18 December 2024)](https://www150.statcan.gc.ca/n1/pub/82-003-x/2024012/article/00001-eng.htm),
  **Analytical approach**: eight annual cycles (2015–2022) are pooled, with sampling
  weights rescaled by a factor of eight and an average-population interpretation.
- [Official CCHS 2023/2024 combined-data release (16 December 2025)](https://www150.statcan.gc.ca/n1/daily-quotidien/251216/dq251216d-eng.htm),
  **Note to readers**: the two-year reference period represents the average
  population aged 18+. This release describes Statistics Canada's own combined
  file; pooling annual files in this application does not reproduce that file.

These recent publications support period pooling and rescaling. The studies are
applications to particular questions and populations, not blanket approval to
combine any years or validation of this application's exact variance calculation.

**Foundational explanation**

[Thomas and Wannell (2009), *Combining cycles of the Canadian Community Health
Survey*](https://www150.statcan.gc.ca/n1/pub/82-003-x/2009001/article/10795/findings-resultats-eng.htm),
section **The pooled approach**, describes combining respondent records and
bootstrap files, and rescaling weights to represent the population of interest.
The [CCHS 2010 User Guide](https://www.statcan.gc.ca/en/statistical-programs/document/3226_D7_T9_V8),
section **8.8, Weighting for a two-year file**, gives the example of dividing
annual weights by two. The 2010 guide is historical background; the recent
Statistics Canada studies above show continued use of the pooling approach.

**How does this application calculate uncertainty?**

Bootstrap weights are alternative sets of respondent weights supplied with the
survey to estimate sampling uncertainty. The application changes one year's
weights at a time, keeping the other years at their main weights. It recalculates
the pooled percentage for each alternative, measures its squared change from the
original percentage, averages these changes within each year, then adds the
yearly contributions. The standard error is the square root of that variance.

This separate-cycle construction **assumes independent annual samples** and a
variance scale of **1 / the number of bootstrap replicates**. Those assumptions
must be checked against the documentation for the supplied weight files.
Statistics Canada's pooling guidance does not prescribe this exact construction
for every annual release.

[Gagné, Roberts and Keown (2014)](https://www150.statcan.gc.ca/n1/pub/12-002-x/2014001/article/11901-eng.htm),
**Problem-specific checklist, item 6.4**, explains why averaged bootstrap weights
may require an adjustment factor. The application does not infer an unknown
factor. The [R survey package's svrepdesign documentation](https://r-survey.r-forge.r-project.org/pkgdown/docs/reference/svrepdesign.html)
explains explicit replicate scaling and squared deviations about the original
estimate (`mse`).
""")
            with st.expander("Exact formula and independent calculation check"):
                st.markdown(
                    "Let N_c be the weighted total with the characteristic and "
                    "D_c the response-domain total in year c. K is the number "
                    "of years and B the number of replicates per year."
                )
                st.latex(r"\widehat P = \frac{1}{K}\sum_c N_c,\qquad \widehat p = 100\frac{\sum_c N_c}{\sum_c D_c}")
                st.markdown("For replicate b in year c, replace only that year's totals:")
                st.latex(r"\widehat p^{(c,b)} = 100\frac{\sum_{j\ne c}N_j + N_c^{(b)}}{\sum_{j\ne c}D_j + D_c^{(b)}}")
                st.latex(r"\widehat V = \sum_c\frac{1}{B}\sum_{b=1}^{B}(\widehat p^{(c,b)} - \widehat p)^2")
                st.markdown("""
The same synthetic fixture was calculated independently in **R 4.6.0 / survey
4.5**: prevalence **45%**, variance **85.542898251371724 percentage-points
squared**. This checks the arithmetic of the stated replicate design; it does
not verify the suitability of an annual CCHS weight release.

[Reproducible R script](https://github.com/WDGPH/CCHS/blob/7faf8264fb7a494e0222e7952aa6642b4b86fd78/scripts/validate_pooled_variance.R)
uses full replicate weights, `type="other"`, `scale=1/B`, `rscales=1`, and
`mse=TRUE`. See the [full methodology and validation guide](https://github.com/WDGPH/CCHS/blob/7faf8264fb7a494e0222e7952aa6642b4b86fd78/bootstrap_analysis_documentation.md).
""")
        with interpretation:
            st.markdown("""
**Use a comparable population and question.** Check question wording, response
categories, who was asked, collection methods, and geographic boundaries.
Matching variable names alone cannot establish comparability. Thomas and Wannell
(2009), **An evolving survey**, explains these checks.

The [CCHS 2023 methodology](https://www23.statcan.gc.ca/imdb/p2SV.pl?Function=getSurvey&Id=1496481),
**Description** and **Target population**, documents the 2022 redesign and
coverage changing to age 18+ in 2023. This application restricts pooling to
common covered ages and requests review of known design or geography changes.
Completing that review records the analyst's judgement; it does not automatically
harmonize the surveys.

**Know the denominator.** Null responses are excluded from numerator and
denominator calculations. Coded responses such as valid skip or not stated
remain categories by default. **Recalculate %** estimates the proportion among
the retained response categories and recomputes uncertainty for that domain.
This response-domain choice does not correct nonresponse bias.

**Report the period and population.** Include the selected years, age range,
geography, response domain, and confidence interval. Results describe an average
population over the selected years; they can hide changes within that period.
Adding cycles does not guarantee a narrower confidence interval.
""")
        st.caption("Sources reviewed 9 October 2026. The example uses fictional data.")
