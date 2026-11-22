# ANOVA

`factorial_anova`, `repeated_anova`, `mixed_anova`: one continuous outcome; between, within or between-by-within factors. Specify subject ID, factor level order, coding, type II/III sums of squares, missingness, and GG/HF/uncorrected inference. Repeated designs require recoverable subject-by-condition cells. Do not silently aggregate trials or select corrections after seeing favorable p values.

Report F, numerator/denominator df, p, partial eta-squared and specified marginal-mean contrasts with estimates/CI. Define each comparison family and Holm/Bonferroni/no-adjustment choice. Main effects, interactions and conditional comparisons have distinct identities; a nonsignificant interaction is not a blanket ban on planned conditional contrasts.

Require explicit authorized aggregation for duplicate cells; reject structural empty cells or unsupported incomplete repeated cells. No MANOVA, arbitrary repeated covariance structures, or repeated/mixed ANCOVA in this first scope. Between-subject ANCOVA uses linear regression. Mixed ANOVA is distinct from a mixed-effects model.

Implementation scope: afex/car, with emmeans for specified comparisons. Primary references: https://cran.r-project.org/web/packages/afex/refman/afex.html and https://rvlenth.github.io/emmeans/articles/interactions.html .

These are approved extension boundaries, not a claim of numerical acceptance. Query the selected current method contract; undeclared options are unsupported. Optional R dependencies are checked at run time, never auto-installed. Retain scientific settings, actual runtime/package versions, diagnostics and candidate status. Use external reviewed implementations for out-of-scope methods without claiming controlled execution.
