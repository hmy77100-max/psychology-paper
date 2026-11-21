# CFA and SEM

`cfa`, `sem`: single-group CFA and basic recursive structural paths. Specify observed/latent variables, loadings/paths, permitted residual relations, scaling and identification constraints. Continuous indicators use ML/MLR; ordered indicators use WLSMV with explicit category order. Continuous ML/MLR may use explicit FIML, documenting missing exogenous-variable handling separately. First-scope ordered WLSMV requires declared complete-sample handling; ordinal FIML is unsupported.

Report unstandardized/standardized parameters, CI, R-squared and applicable chi-square/df, CFI/TLI, RMSEA/CI and SRMR. Distinguish robust from ordinary indices. Record convergence, information-matrix problems, negative variances and inadmissible solutions; iteration termination alone is not success. Saturated df=0 perfect fit does not validate theory; fit thresholds do not decide theory for the author.

No multigroup invariance, ESEM, multilevel SEM, latent growth/classes/mixtures, Bayesian SEM or automatic path modification in this first scope. Identification and admissibility need actual model/data evidence, not complexity or sample-count slogans.

Implementation scope: lavaan shared with mediation. Primary references: https://lavaan.ugent.be/tutorial/est.html , https://lavaan.ugent.be/tutorial/cat.html and https://lavaan.ugent.be/tutorial/cfa.html .

These are approved extension boundaries, not a claim of numerical acceptance. Query the selected current method contract; undeclared options are unsupported. Optional R dependencies are checked at run time, never auto-installed. Retain scientific settings, actual runtime/package versions, diagnostics and candidate status. Use external reviewed implementations for out-of-scope methods without claiming controlled execution.
