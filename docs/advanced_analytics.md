# Advanced Analytics (Tier 1)

This tab extends the base bootstrap prevalence analysis with four additional
panels that every PHU-facing CCHS report eventually needs: **stratified
prevalence**, **group contrast**, **equity gradient**, and **benchmarking**.

All four share the same merged dataset (respondent rows + `BSW*` replicate
weights) and the same CCHS release rules (`n ≥ 30`, `CV ≤ 33.3%`). The common
variance engine is documented in `bootstrap_analysis_documentation.md`; this
file covers what is new in the Advanced tab.

---

## 1. Entry point and data flow

```
apply_filters  ──►  base_data (inclusion flags + age groups)
                 ├─►  province_merged   =  base_data ⋈ bootstrap_data
                 └─►  merged_data       = (geo-filtered base_data) ⋈ bootstrap_data
```

- `merged_data` is the **local** (PHU-scoped) analytic frame.
- `province_merged` is the **unfiltered province-wide** frame, used as the
  Ontario comparator for benchmarking. It inherits the same inclusion-flag
  definitions and age groups as the local frame so the benchmark is
  apples-to-apples; only the geographic scope differs.

Both are written to `st.session_state` when the **Apply Filters** button fires
(`app.py`). The Advanced tab reads them via
`render_advanced_analytics_tab(merged_data=..., province_merged=...)`.

### Shared controls

The tab's header has two selectors that feed **every** sub-panel:

| Control      | Source                                | Used by                    |
|--------------|---------------------------------------|----------------------------|
| Variable     | `selected_variables` from session     | all four panels            |
| Stratifier   | `STRATIFIER_REGISTRY ∩ merged_data.columns` | stratified, contrast, equity |

The stratifier list is intentionally constrained to a curated registry
(`config/settings.py::STRATIFIER_REGISTRY`) — variables validated as usable
across every CCHS cycle for subgroup analysis, with harmonized skip codes and
value labels.

---

## 2. Stratified prevalence (`📊 Stratified prevalence`)

**What it does.** Computes weighted prevalence of every value of the selected
variable *within each level of the stratifier*. Normalisation is
**within-stratum**: the denominator is the sum of weights over that stratum
only, so each row is a conditional probability `P(variable = value | stratum)`.

**How inference is computed.** The same bootstrap engine as base analysis,
applied once per (stratum, value) cell — replicate prevalence per cell is
computed by dividing the stratum's replicate numerator by the stratum's
replicate denominator, one `BSW*` column at a time. Variance is the mean
squared deviation of replicate prevalence from the base estimate; CI bounds
are `base ± 1.96·SD`.

**Quality flag.** Each row is tagged `ok` / `caution` / `suppress` using
Statistics Canada's share-table rule: suppress if `n < 30` or `CV > 33.3%`,
caution if `16.6% < CV ≤ 33.3%`, otherwise ok. When the user downloads the
suppressed table, the numeric columns are blanked out on suppressed rows.

**Implementation.** `src/analysis/stratified.py::run_bootstrap_stratified`.

**Gotchas.**
- Skip / refusal codes registered under `exclude_values` are dropped *before*
  stratification — don't be surprised when the sum of stratum Ns is less than
  the local frame size.
- `pd.Categorical` stratifiers (e.g. `AgeGroup` from `pd.cut`) are coerced to
  object internally because categorical MultiIndexes break the
  `reindex`-then-divide pattern used for per-replicate denominators.

---

## 3. Group contrast (`⚖️ Group contrast`)

**What it does.** Picks two levels of the stratifier (A and B) and produces
one row per outcome value with: prevalence in each group, the absolute
difference (pp), prevalence ratio (PR), odds ratio (OR), and a two-sided
z-test p-value.

**Why it replaces the old "do CIs overlap?" check.** Non-overlap of two
independent 95% CIs is overly conservative — two estimates can be
significantly different at `p < 0.05` while their individual CIs still
overlap. Here, the bootstrap SE is computed on the **per-replicate contrast**:

```
rep_diff[b]      = rep_A[v, b] − rep_B[v, b]        # for each BSW replicate b
SE(difference)   = sqrt( mean((rep_diff − base_diff)²) )
z                = base_diff / SE(difference)
p                = 2·Φ̄(|z|)
```

Ratio CIs use the delta method on the **log scale**, then exponentiate:

```
SE(log PR) = sqrt( mean((log rep_ratio − log base_ratio)²) )
CI(PR)     = exp(log base_ratio ± 1.96·SE(log PR))
```

Odds ratio CIs follow the same pattern but with `p/(1−p)` converted from
prevalence (clipped to `[1e-6, 1 − 1e-6]` to keep the log finite).

**Implementation.** `src/analysis/difference.py::bootstrap_contrast` for a
single value, `contrast_all_values` to iterate over every value of the
outcome.

**When a CI shows `—`.** The OR (and sometimes the PR) is **undefined** when
either arm's prevalence hits exactly 0% or 100% — the odds go to zero or
infinity and the log scale blows up. Those cases return `NaN` bounds
internally; `src/analysis/difference.py::_fmt_ci` renders them as an em-dash
rather than leaking `(nan, nan)` into the dataframe. (Earlier builds showed
literal `(nan, nan)`; this was a display-layer bug.)

**Also note.** PHU-vs-Ontario benchmarking uses
`contrast_two_frames`, which deliberately **does not** compute OR — the two
frames have different BSW totals and rolling up the OR's delta-method CI is
not well-defined in that setting.

---

## 4. Equity gradient (`📈 Equity gradient`)

Operates on the output of the Stratified panel (cached in
`st.session_state[f"_strat_cache_{variable}_{stratifier}"]`). For each
outcome value, reports:

| Metric             | Definition                                           |
|--------------------|------------------------------------------------------|
| Absolute gap (pp)  | `prev(most disadvantaged) − prev(most advantaged)`   |
| Relative ratio     | `prev(disadv) / prev(adv)`                           |
| **SII (pp)**       | Slope Index of Inequality — see below                |
| **RII**            | Relative Index of Inequality — see below             |

**SII / RII.** Define each stratum's **ridit** as the midpoint of its
cumulative population share (sort strata from advantaged to disadvantaged,
convert each weighted population to a share, and place the stratum at the
midpoint of its cumulative interval). Then fit a population-weighted linear
regression of prevalence on ridit:

```
prevalence_i  ≈  intercept + slope · ridit_i     (weighted by pop_i)

SII  = prevalence at ridit=0  −  prevalence at ridit=1
     = intercept − (intercept + slope)
     = −slope          # positive ⇒ burden on the disadvantaged end
RII  = prevalence at ridit=0 / prevalence at ridit=1
```

SII has units of percentage points (absolute inequality); RII is unitless
(relative inequality), so they tell complementary stories — report both.

**When SII/RII aren't computed.** The metrics require an **ordered**
stratifier (monotone direction of social/economic advantage). If the
registry marks the stratifier as categorical, the panel shows a message and
only reports gap/ratio.

**Implementation.** `src/analysis/equity.py` — `calculate_gap`,
`calculate_sii_rii`, and `equity_summary` (per-value table).

---

## 5. Benchmarking (`🏙️ Benchmark`)

Compares the local PHU against either (a) all of Ontario, (b) one or more
named comparator PHUs, or (c) the league table across every PHU.

### 5a. Prerequisite: `province_merged`

This panel **requires** `st.session_state['province_merged']` to be
populated — without it, benchmarking has no Ontario comparator and the panel
prints an instructional message. Wiring is handled in `app.py`'s filter-apply
block: the same `base_data` (inclusion flags + age groups applied) is merged
with bootstrap weights *before* the geographic filter is applied.

> If you are adding a new UI entry point or a new data-loading path, mirror
> this wiring — compute `province_merged` alongside the local `merged_data`,
> skipping the geographic filter but keeping every other definitional filter.

### 5b. Ontario / PHU contrast

For each value of the outcome, runs
`src/analysis/difference.py::contrast_two_frames` with:

- `data_a` = local merged frame
- `data_b` = `province_merged` (Ontario) **or** `province_merged` filtered to
  the selected comparator PHUs via `GEODVHR4`.

Only the BSW columns shared between the two frames are used (defensive
against rare cycle-specific replicate differences). The variance of the
difference is still computed on per-replicate differences, so the inference
is proper.

The panel reports `Local Prev`, `Ontario/Comparator Prev`, `Difference (pp)`
with its 95% CI, a z-statistic, p-value, and both arms' unweighted N. OR/PR
columns are deliberately omitted for the frame-vs-frame case (see §3).

### 5c. League table

`rank_phu_on_outcome` iterates every health region code in
`KNOWN_HEALTH_REGION_LABELS`, runs a standard bootstrap on the subset, pulls
the row for the chosen outcome value, and returns a sorted table with rank,
prevalence, CI, CV, and n. Use it when an analyst asks "where does WDG sit
on outcome X relative to every other PHU?"

---

## 6. Extending the tab

### Add a new stratifier

1. Confirm the variable exists (or is harmonized) across every cycle you
   care about.
2. Add an entry to `STRATIFIER_REGISTRY` in `config/settings.py` with
   `ordered`, `exclude_values`, `value_labels`, and a `label`.
3. If ordered (ridit-based SII/RII will use it), make sure the numeric code
   order matches "advantaged → disadvantaged" — the regression is signed.

### Add a new sub-panel

Each panel is a `_render_*_panel` function in `src/ui/advanced.py` that
takes the shared frames and the selected variable/stratifier and writes to
the current Streamlit container. Add it to the `st.tabs(...)` call inside
`render_advanced_analytics_tab`.

### Add a new benchmarking comparator

Extend `src/analysis/benchmark.py::benchmark_against` with another branch in
the `comparator` switch. Whatever you pass must be a subset of
`province_merged` (or share its BSW columns) so `contrast_two_frames` can
find common replicates.

---

## 7. Known caveats

- **Bootstrap variance is Statistics Canada's Rao-Wu-Yue rescaling method.**
  The replicate weights come with the PUMF — don't re-derive them.
- **Interpret SII/RII with the stratifier's direction in mind.** A positive
  SII on education means the less-educated group has higher prevalence; flip
  the sign mentally if you reverse the stratum order.
- **Benchmarking uses shared `BSW*` columns only.** If you ever merge frames
  from different cycles with different replicate counts, `contrast_two_frames`
  will fall back to the intersection; watch the printed `n A` / `n B`.
- **OR/PR at boundary prevalences.** Rendered as `—`; do not interpret the
  missing CI as "not significant" — the estimate itself is undefined.
