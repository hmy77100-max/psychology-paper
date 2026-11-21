# Mixed-effects models

`linear_mixed`, `binomial_mixed`, `poisson_mixed`: LMM and logit/Poisson GLMM for repeated, longitudinal, clustered or subject-by-stimulus observations. Specify fixed terms, grouping IDs, time coding, nested/crossed random intercepts and data-supported random slopes. Distinguish people, groups and observations.

Specify ML/REML; LMM uses Satterthwaite inference, GLMM Laplace/Wald inference. Report coefficients/CI, variance components, likelihood and applicable df alongside convergence and singularity diagnostics. Singular fits retain that warning in candidate output; numerical completion does not establish model adequacy. Nonconverged fits cannot be registered as complete results. Do not silently remove random slopes or switch optimizers until significant. Additional trials cannot remove a shortage of independent groups.

Nested-model LRT requires identical observations and comparable estimation. Do not compare different fixed structures by REML likelihood. First scope excludes AR residual structures, nonlinear/Bayesian mixed models, GAMM and unlisted GLMM families; mixed ANOVA has a separate interface.

Implementation scope: lme4/lmerTest, with emmeans for specified comparisons. Primary references: https://lme4.github.io/lme4/reference/lmer.html and https://lme4.github.io/lme4/reference/glmer.html .

These are approved extension boundaries, not a claim of numerical acceptance. Query the selected current method contract; undeclared options are unsupported. Optional R dependencies are checked at run time, never auto-installed. Retain scientific settings, actual runtime/package versions, diagnostics and candidate status. Use external reviewed implementations for out-of-scope methods without claiming controlled execution.
