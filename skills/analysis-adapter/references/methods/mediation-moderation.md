# Mediation and moderation

`mediation`: simple/parallel paths for independent single-level observations, continuous mediator(s) and outcome, continuous or explicitly binary-coded exposure, with covariates assigned to explicit paths. Define X/M/Y, direct/indirect/total effects, missingness and sample. Bootstrap independent observational units; specify percentile interval, seed, requested draws and failed draws. Do not resample trials as independent participants. Report effects and CI, not just a binary mediation verdict.

`moderation`: reuse the supported OLS/binomial/Poisson regression interaction path; specify X/W/Y, coding/centering, conditional values, simple slopes/contrasts and comparison family. An interaction and conditional contrasts answer different questions. Separate support for mediation and moderation does not implement moderated mediation.

First scope excludes serial, multilevel/longitudinal mediation, generic causal decomposition for binary mediators/outcomes, latent interactions, moderated mediation and all PROCESS numbered templates. Cross-sectional path products do not prove causal mechanisms. Preserve post-result exploratory timing through adoption.

Mediation shares lavaan estimation/extraction with SEM; moderation shares regression rather than a second solver. Primary references: https://lavaan.ugent.be/tutorial/mediation.html and https://rvlenth.github.io/emmeans/articles/interactions.html .

These are approved extension boundaries, not a claim of numerical acceptance. Query the selected current method contract; undeclared options are unsupported. Optional R dependencies are checked at run time, never auto-installed. Retain scientific settings, actual runtime/package versions, diagnostics and candidate status. Use external reviewed implementations for out-of-scope methods without claiming controlled execution.
