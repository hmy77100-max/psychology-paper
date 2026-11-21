execute_model <- function(payload) {
  s <- payload$spec; m <- s$model; inf <- s$inference; b <- inf$bootstrap
  if (!requireNamespace("lavaan",quietly=TRUE)) fail("MISSING_PACKAGE", "Package lavaan is required")
  if (!identical(m$estimator,"ML") || is.null(b) || !identical(b$unit,"observation") || !identical(b$ci_type,"percentile") || is.null(b$seed) || is.null(b$replicates) || b$replicates<2 || b$replicates!=as.integer(b$replicates)) fail("INVALID_SPEC", "ML and explicit observation percentile bootstrap, seed and replicate count required")
  if (!identical(inf$alternative,"two-sided") || length(inf$comparisons)) fail("UNSUPPORTED_MODEL", "Unsupported mediation inference", "UNSUPPORTED_MODEL")
  if (!is.logical(m$mediator_covariances) || length(m$mediator_covariances)!=1L) fail("INVALID_SPEC", "Explicit mediator covariance setting required")
  meds <- unlist(m$mediators); covars <- unlist(m$covariates); vars <- c(m$exposure,m$outcome,meds,covars)
  if (!length(meds) || anyDuplicated(vars)) fail("INVALID_SPEC", "Distinct exposure, outcome, mediators and covariates required")
  z <- prepare_frame(payload,vars); d <- z$data; map <- z$map; n <- z$n
  x <- unname(map[[m$exposure]]); y <- unname(map[[m$outcome]]); mm <- unname(map[meds]); cc <- unname(map[covars]); covpart <- if(length(cc)) paste0(" + ",paste(cc,collapse=" + ")) else ""
  syntax <- c(vapply(seq_along(mm),function(i) paste0(mm[i]," ~ a",i,"*",x,covpart),""),paste0(y," ~ direct*",x," + ",paste(paste0("b",seq_along(mm),"*",mm),collapse=" + "),covpart))
  if (length(mm)>1L) for(i in seq_len(length(mm)-1L)) for(j in (i+1L):length(mm)) syntax <- c(syntax,paste(mm[i],"~~",if(isTRUE(m$mediator_covariances)) "" else "0*",mm[j]))
  syntax <- c(syntax,vapply(seq_along(mm),function(i) paste0("indirect",i," := a",i,"*b",i),""),paste0("total_indirect := ",paste0("indirect",seq_along(mm),collapse=" + ")),"total := direct + total_indirect")
  warnings <- list(); set.seed(as.integer(b$seed))
  fit <- withCallingHandlers(lavaan::sem(paste(syntax,collapse="\n"),data=d,estimator="ML",se="bootstrap",bootstrap=as.integer(b$replicates),fixed.x=FALSE),warning=function(w){warnings[[length(warnings)+1L]] <<- conditionMessage(w);invokeRestart("muffleWarning")})
  if (!isTRUE(lavaan::lavInspect(fit,"converged"))) fail("NONCONVERGED", "Mediation model did not converge", "NONCONVERGED")
  if (!isTRUE(lavaan::lavInspect(fit,"post.check"))) fail("IMPROPER_SOLUTION", "Mediation failed post-estimation admissibility checks")
  pe <- lavaan::parameterEstimates(fit,ci=TRUE,level=inf$confidence_level,boot.ci.type="perc"); if(any(!is.finite(pe$est)) || any(!is.finite(pe$ci.lower)) || any(!is.finite(pe$ci.upper))) fail("NONFINITE_ESTIMATE", "Nonfinite parameter or bootstrap interval")
  decode <- function(x) decode_tokens(x,map)
  res <- lapply(seq_len(nrow(pe)),function(i) {
    term <- if(pe$op[i]==":=") pe$lhs[i] else paste0(decode(pe$lhs[i]),pe$op[i],decode(pe$rhs[i]))
    r <- list(outcome_id=m$outcome,term_id=term,contrast_id="parameter",kind=if(pe$op[i]==":=" && pe$lhs[i]!="total") "indirect" else if(pe$op[i]=="~~") "variance" else "coefficient",estimate=unname(pe$est[i]),ci=c(unname(pe$ci.lower[i]),unname(pe$ci.upper[i])),confidence_level=inf$confidence_level,ci_alternative="two-sided",n=n)
    if(is.finite(pe$se[i])) r$se <- unname(pe$se[i]); if(is.finite(pe$pvalue[i])) r$p <- unname(pe$pvalue[i]); r
  })
  boot <- lavaan::lavInspect(fit,"boot"); error_indices <- attr(boot,"error.idx"); nonadmissible <- attr(boot,"nonadmissible"); failed <- length(error_indices); inadmissible_n <- length(nonadmissible); invalid <- unique(c(error_indices,nonadmissible)); valid <- as.integer(b$replicates)-length(invalid)
  if(valid<2L) fail("INVALID_DATA", "Too few valid bootstrap replicates for percentile interval")
  if (failed>0L || inadmissible_n>0L) warnings[[length(warnings)+1L]] <- paste(failed,"bootstrap replicates failed and",inadmissible_n,"were nonadmissible")
  list(status="COMPLETED",results=res,sample_audit=z$audit,diagnostics=list(warnings=warnings,converged=TRUE,bootstrap_failed=failed,bootstrap_nonadmissible=inadmissible_n,bootstrap_valid=valid),backend_versions=list(R=as.character(getRversion()),jsonlite=as.character(utils::packageVersion("jsonlite")),lavaan=as.character(utils::packageVersion("lavaan"))),model_summary=list(expected_result_ids=lapply(res,function(x)list(x$outcome_id,x$term_id,x$contrast_id)),bootstrap_replicates=b$replicates,bootstrap_seed=b$seed,bootstrap_unit=b$unit,bootstrap_ci_type=b$ci_type))
}
