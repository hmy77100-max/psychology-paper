# Regression

`linear_regression`: OLS, multiple predictors and between-subject ANCOVA; ordinary SE or explicit HC3. `binomial_regression`: logit for 0/1 or explicitly mapped successes/totals. `poisson_regression`: log count model with an explicit optional offset. Specify intercept, reference levels/contrasts, centering, interactions, covariate set, missingness and estimand. Do not choose variables by automatic significance searching.

Report coefficients/CI and applicable odds or rate ratios, fit information and residual/influence diagnostics. Logit requires complete/quasi-complete separation checks; separation cannot become an apparently finite normal MLE. A bias-reduced model is a distinct candidate. Diagnose Poisson overdispersion without silently switching distributions. Reject rank deficiency rather than silently dropping columns.

No ordinal/multinomial logit, negative-binomial/zero-inflated, survival, penalized regression or GAM/GAMM in this first scope. Conditional predictions/slopes need specified values and comparison families. Their causal meaning follows design and assumptions.

Implementation scope: R stats; sandwich for HC3 and detectseparation for logit checks. Primary references: https://stat.ethz.ch/R-manual/R-devel/library/stats/html/glm.html and https://sandwich.r-forge.r-project.org/reference/vcovHC.html .

These are approved extension boundaries, not a claim of numerical acceptance. Query the selected current method contract; undeclared options are unsupported. Optional R dependencies are checked at run time, never auto-installed. Retain scientific settings, actual runtime/package versions, diagnostics and candidate status. Use external reviewed implementations for out-of-scope methods without claiming controlled execution.
