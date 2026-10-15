# Synthetic benchmark; no CCHS records or variable dictionaries are used.
# Run with: Rscript scripts/validate_pooled_variance.R
# Requires the CRAN survey package. See bootstrap_analysis_documentation.md.
library(survey)
fixture <- data.frame(
  CYCLE = rep(c("2022", "2023", "2024"), each = 2),
  OUTCOME = rep(c(1, 0), 3),
  WTS_S = c(2, 3, 4, 2, 3, 6),
  BSW1 = c(3, 2, 5, 3, 2, 7),
  BSW2 = c(1, 5, 2, 2, 4, 4),
  BSW3 = c(4, 4, 6, 1, 5, 8)
)
cycles <- unique(fixture$CYCLE)
B <- 3
K <- length(cycles)
replicate_weights <- do.call(cbind, lapply(cycles, function(cycle) {
  do.call(cbind, lapply(seq_len(B), function(b) {
    ifelse(fixture$CYCLE == cycle, fixture[[paste0("BSW", b)]], fixture$WTS_S) / K
  }))
}))
design <- svrepdesign(
  data = fixture, weights = ~I(WTS_S / K), repweights = replicate_weights,
  type = "other", combined.weights = TRUE, scale = 1 / B,
  rscales = rep(1, K * B), mse = TRUE
)
estimate <- svymean(~OUTCOME, design)
cat("R version:", as.character(getRversion()), "\n")
cat("survey version:", as.character(packageVersion("survey")), "\n")
cat(sprintf("Prevalence=%.15f\nVariance=%.15f\n", coef(estimate) * 100, vcov(estimate)[1, 1] * 10000))
