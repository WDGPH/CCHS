# CCHS 2024 Data Quality Reporting Standards
> Based on Sections 10 & 11 of the CCHS 2024 Annual Component User Guide (August 2025)

---

## Release Categories

| Category | Meaning |
|----------|---------|
| **A** | Release with no warning — use 95% CI as quality indicator |
| **E** | Release with caution warning — use 95% CI as quality indicator |
| **F** | Suppress — do not release |

> Note: 'A' is not itself a quality indicator and should not be published alongside the estimate. The 95% confidence interval is the quality indicator.

---

## Release Rules for Proportions (Table 10.1)

**Effective Sample Size formula:**

$$\text{Effective Sample Size} = \frac{\hat{p}(1-\hat{p})}{\text{Var}(\hat{p})} = \frac{1-\hat{p}}{\hat{p} \cdot CV^2}$$

| Condition | Category | Action |
|-----------|----------|--------|
| $n_2 \geq 100$ **and** $\frac{1-\hat{p}}{\hat{p} \cdot CV^2} \geq 60$ | **A** | Release with no warning |
| Otherwise | **E** | Release with quality warning |
| $n_2 < 50$ **or** $\frac{1-\hat{p}}{\hat{p} \cdot CV^2} < 30$ **or** $n_1 < 10$ | **F** | Suppress |

- $n_1$ = unweighted count in **numerator**
- $n_2$ = unweighted count in **denominator**
- Estimates of **0% or 100% should never be published**

---

## Release Rules for Counts, Means & Totals (Table 10.2)

| Condition | Category | Action |
|-----------|----------|--------|
| $n \geq 100$ **and** $CV \leq 25\%$ | **A** | Release with no warning |
| $50 \leq n < 100$ **and** $CV \leq 35\%$ | **E** | Release with quality warning |
| Otherwise | **F** | Suppress |

- For **counts and totals**: $n$ = unweighted count of respondents with nonzero values
- For **means**: $n$ = unweighted count of all respondents contributing to the estimate (including zeros)

---

## Release Rules for Differences and Ratios

The release category of a difference or ratio inherits the **lower (worse) category** of its two component estimates:

- If either estimate is **F** → assign **F**, suppress
- If either estimate is **E** → assign **E**
- If both estimates are **A** → assign **A**

---

## Confidence Intervals

### General Formula

$$CI_{\hat{X}} = \left[\hat{X} - z \cdot \hat{X} \cdot \alpha_X,\quad \hat{X} + z \cdot \hat{X} \cdot \alpha_X\right]$$

Where $\alpha_X$ is the coefficient of variation (CV) of the estimate.

### Z values by confidence level

| $z$ | Confidence Level |
|-----|-----------------|
| 1.0 | 68% |
| 1.6 | 90% |
| **2.0** | **95% (Statistics Canada standard)** |
| 3.0 | 99% |

### Additional CI Suppression Rules (Category F)

A CI must also be suppressed if either condition is true:
- Lower bound = Upper bound (zero-length interval)
- A bound is implausible (e.g., a negative lower bound for a proportion)

---

## Standard Error of a Difference

$$\sigma_d = \sqrt{(\hat{X}_1 \cdot \alpha_1)^2 + (\hat{X}_2 \cdot \alpha_2)^2}$$

$$CV_d = \frac{\sigma_d}{d}, \quad \text{where } d = \hat{X}_1 - \hat{X}_2$$

> This formula is exact for **independent** subgroups. It **overstates** error when estimates are positively correlated and **understates** it when negatively correlated.

---

## Standard Error of a Ratio (non-subset numerator)

$$\sigma_{\hat{R}} = \hat{R}\sqrt{\alpha_1^2 + \alpha_2^2}$$

$$CV_{\hat{R}} = \frac{\sigma_{\hat{R}}}{\hat{R}} = \sqrt{\alpha_1^2 + \alpha_2^2}$$

> If the numerator **is a subset** of the denominator, convert to a percentage and use the proportion rules instead.

---

## Z-test for Significance of Differences

$$z = \frac{\hat{X}_1 - \hat{X}_2}{\sigma_d}$$

| Result | Interpretation |
|--------|---------------|
| $-2 \leq z \leq 2$ | Difference is **not significant** at the 5% level |
| $z < -2$ or $z > 2$ | Difference is **significant** at the 5% level |

---

## Minimum Sample Size Thresholds

| Context | Minimum Requirement |
|---------|-------------------|
| Master / Share file — characteristic | $n \geq 10$ |
| Master / Share file — domain (for proportions) | $n \geq 20$ |
| CV lookup table approximations | $n \geq 30$ |
| Estimates of 0% or 100% | **Never release** |

---

## Rounding Guidelines

| Estimate Type | Rounding Rule |
|---------------|--------------|
| Counts / aggregates | Round to nearest **100** using normal rounding |
| Subtotals and totals | Derived from unrounded components, then rounded to nearest 100 |
| Averages, proportions, rates, percentages | Round to **one decimal place** |
| Differences and sums of aggregates | Derived from unrounded components, then rounded to nearest 100 |

> **Never publish unrounded estimates** — this implies greater precision than actually exists.

---

## Variance Estimation: Bootstrap vs CV Tables

| Method | Use Case | Notes |
|--------|----------|-------|
| **Bootstrap weights** ✅ (recommended) | All analyses | Fully accounts for stratification, clustering, and multi-frame design |
| CV lookup tables | Quick approximations only | Approximate and unofficial; requires $n \geq 30$ |

### Software guidance

Use **survey-aware procedures** that incorporate both sample weights and bootstrap weights:

- ✅ SAS: `PROC SURVEYMEANS` (with bootstrap weights)
- ⚠️ SAS: `PROC MEANS` (adjusts estimates but underestimates variance — not recommended)

Only the bootstrap methodology properly accounts for the stratified, clustered, multi-frame nature of the CCHS design when calculating variance.

---

## Worked Example: 95% CI for a Proportion

Given: 71.2% of people who smoke at all smoke daily ($n_2 = 9{,}234$, numerator $= 3{,}665{,}449$, $CV = 1.3\%$)

$$CI = \{0.712 - (2)(0.712)(0.013),\ 0.712 + (2)(0.712)(0.013)\} = \{0.693,\ 0.731\}$$

**Release check:**

$$\frac{1-\hat{p}}{\hat{p} \cdot CV^2} = \frac{1 - 0.712}{(0.712)(0.013^2)} = 2{,}393 \geq 60 \quad \checkmark$$

$n_2 = 9{,}234 \geq 100 \quad \checkmark$ → **Category A — release with no warning**
