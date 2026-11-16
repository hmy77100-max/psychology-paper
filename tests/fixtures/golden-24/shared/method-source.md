# Method-learning packet
Official NIST pairing: https://www.itl.nist.gov/div898/handbook/eda/section3/eda353.htm
Official one-sample t formula: https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm
For d=post-pre, t=mean(d)/(s_d/sqrt(n)), df=n-1. Sample variance uses n-1. Independent pairs, meaningful differences and inference assumptions need assessment. Tiny n cannot establish normality from a nonsignificant diagnostic. This is one reproducible path, not a whitelist. Other sourced appropriate methods are acceptable, with their targets/conditions and tradeoffs stated.

SciPy 1.18.0 original implementation documentation, accessed 2026-11-14:
https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html
Exact source excerpt: "the null distribution is formed by independently changing the sign of each observation."
The documentation distinguishes samples (preserving pairs) from pairings (reassigning partners). For a single vector of paired differences, samples permutes signs; n_resamples=np.inf enumerates all distinct arrangements. Its paired-sample null uses exchangeability within pairs, not merely zero average change. For observational pre/post data, the corresponding symmetry/exchangeability assumption needs justification; this is not randomized causal identification. Two-sided p is twice the smaller tail proportion. This packet records implementation guidance, not original invention of permutation inference, expert certification or a guarantee of applicability.
