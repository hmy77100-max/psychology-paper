execute_model <- function(payload) {
  s <- payload$spec; m <- s$model; inf <- s$inference
  if (!requireNamespace("lavaan",quietly=TRUE)) fail("MISSING_PACKAGE", "Package lavaan is required")
  if (!m$estimator %in% c("ML","MLR","WLSMV") || !identical(inf$alternative,"two-sided") || length(inf$comparisons) || length(inf$bootstrap)) fail("UNSUPPORTED_MODEL", "Unsupported SEM estimator or inference", "UNSUPPORTED_MODEL")
  if (identical(s$sample$missing,"fiml") && (m$estimator=="WLSMV" || length(m$ordered))) fail("UNSUPPORTED_MODEL", "FIML requires continuous ML or MLR", "UNSUPPORTED_MODEL")
  if (!is.logical(m$std_lv) || length(m$std_lv)!=1L || !is.logical(m$fixed_x) || length(m$fixed_x)!=1L) fail("INVALID_SPEC", "Explicit std_lv and fixed_x booleans required")
  latent <- m$latent; if (is.null(latent) || !length(latent) || is.null(names(latent)) || anyDuplicated(names(latent))) fail("INVALID_SPEC", "Named latent factors required")
  factors <- names(latent); indicators <- unique(unlist(latent)); paths <- m$paths; covs <- m$residual_covariances
  observed_paths <- setdiff(unique(unlist(lapply(paths,function(x)c(x$outcome,unlist(x$predictors))))),factors)
  observed_covs <- setdiff(unique(unlist(covs)),factors); observed <- unique(c(indicators,observed_paths,observed_covs))
  if (any(factors %in% observed) || any(vapply(latent,function(x) length(x)<2L || anyDuplicated(unlist(x)),logical(1)))) fail("INVALID_SPEC", "Invalid latent indicators")
  ordered <- m$ordered; if (is.null(ordered)) ordered <- list()
  if (length(ordered) && m$estimator!="WLSMV" || !length(ordered) && m$estimator=="WLSMV" || any(!names(ordered) %in% indicators)) fail("INVALID_SPEC", "WLSMV requires explicit ordered indicators")
  z <- prepare_frame(payload,observed,ordered,allow_fiml=TRUE); d <- z$data; map <- c(z$map,setNames(paste0("L",seq_along(factors)),factors)); n <- z$n
  syntax <- vapply(factors,function(f) paste0(map[[f]]," =~ ",paste(unname(map[unlist(latent[[f]])]),collapse=" + ")),"")
  if (length(paths) && anyDuplicated(vapply(paths,function(p) p$outcome,""))) fail("INVALID_SPEC", "Duplicate structural outcome")
  if (length(paths)) for (p in paths) { v <- unlist(p$predictors); if (!length(v) || any(!c(p$outcome,v) %in% names(map)) || p$outcome %in% v || anyDuplicated(v)) fail("INVALID_SPEC", "Invalid structural path"); syntax <- c(syntax,paste(map[[p$outcome]],"~",paste(unname(map[v]),collapse=" + "))) }
  if (length(covs)) for (pair in covs) { v <- unlist(pair); if (length(v)!=2L || any(!v %in% names(map)) || v[1]==v[2]) fail("INVALID_SPEC", "Invalid residual covariance"); syntax <- c(syntax,paste(map[[v[1]]],"~~",map[[v[2]]])) }
  # Cyclic structural graphs are outside the controlled scope.
  if (length(paths)) {
    edges <- lapply(paths,function(p) unlist(p$predictors)); names(edges) <- vapply(paths,function(p)p$outcome,"")
    visit <- function(node,stack=character()) { if (node %in% stack) return(TRUE); any(vapply(edges[[node]],function(v) visit(v,c(stack,node)),logical(1))) }
    if(any(vapply(names(edges),visit,logical(1)))) fail("UNSUPPORTED_MODEL", "Cyclic structural paths are unsupported", "UNSUPPORTED_MODEL")
  }
  warnings <- list(); fit <- withCallingHandlers(lavaan::sem(paste(syntax,collapse="\n"),data=d,estimator=m$estimator,std.lv=isTRUE(m$std_lv),fixed.x=isTRUE(m$fixed_x),ordered=if(length(ordered)) unname(map[names(ordered)]) else NULL,missing=if(identical(s$sample$missing,"fiml")) "fiml" else "listwise"),warning=function(w){warnings[[length(warnings)+1L]] <<- conditionMessage(w);invokeRestart("muffleWarning")})
  if (!isTRUE(lavaan::lavInspect(fit,"converged"))) fail("NONCONVERGED", "SEM did not converge", "NONCONVERGED")
  if (lavaan::lavInspect(fit,"nobs") != n) fail("INVALID_DATA", "Estimator excluded rows; inspect missing exogenous variables")
  if (!isTRUE(lavaan::lavInspect(fit,"post.check"))) fail("IMPROPER_SOLUTION", "SEM failed post-estimation admissibility checks")
  pe <- lavaan::parameterEstimates(fit,standardized=TRUE,ci=TRUE,level=inf$confidence_level)
  pt <- lavaan::parTable(fit); if (nrow(pt)!=nrow(pe) || any(pt$lhs!=pe$lhs | pt$op!=pe$op | pt$rhs!=pe$rhs)) fail("INCOMPLETE_OUTPUT", "SEM parameter table alignment failed"); free <- pt$free > 0; if (any(!is.finite(pe$se[free]))) fail("UNIDENTIFIED_MODEL", "No finite standard error for a free parameter")
  if (any(pe$op=="~~" & pe$lhs==pe$rhs & pe$est<0)) fail("IMPROPER_SOLUTION", "Negative variance detected", "INVALID_DATA")
  if (any(!is.finite(pe$est))) fail("NONFINITE_ESTIMATE", "Nonfinite SEM parameter")
  decode <- function(x) { idx <- match(x,unname(map)); if(is.na(idx)) x else names(map)[idx] }
  res <- lapply(seq_len(nrow(pe)),function(i) {
    outcome <- decode(pe$lhs[i]); term <- paste0(decode(pe$lhs[i]),pe$op[i],decode(pe$rhs[i])); kind <- if(pe$op[i]=="=~") "loading" else if(pe$op[i]=="~~") "variance" else "coefficient"
    r <- list(outcome_id=outcome,term_id=term,contrast_id="parameter",kind=kind,estimate=unname(pe$est[i]),free=unname(free[i]),n=n)
    if(is.finite(pe$std.all[i])) r$standardized_estimate <- unname(pe$std.all[i]); if(is.finite(pe$se[i])) r$se <- unname(pe$se[i]); if(is.finite(pe$pvalue[i])) r$p <- unname(pe$pvalue[i])
    if(is.finite(pe$ci.lower[i]) && is.finite(pe$ci.upper[i])) { r$ci <- c(unname(pe$ci.lower[i]),unname(pe$ci.upper[i])); r$confidence_level <- inf$confidence_level; r$ci_alternative <- "two-sided" }; r
  })
  measures <- lavaan::fitMeasures(fit); required_fit <- c("chisq","df","srmr"); if(any(!required_fit %in% names(measures)) || any(!is.finite(measures[required_fit]))) fail("INCOMPLETE_OUTPUT", "Required fit measures unavailable")
  fit_missing <- list(); for (key in c("cfi","tli","rmsea","rmsea.ci.lower","rmsea.ci.upper")) if (!key %in% names(measures) || !is.finite(measures[[key]]) || measures[["df"]]==0) fit_missing[[key]] <- if(measures[["df"]]==0) "Saturated model: fit index does not assess model fit" else "Not available for this estimator or model"
  if(measures[["df"]]==0) measures <- measures[!names(measures) %in% names(fit_missing)]
  measures <- as.list(measures[is.finite(measures)]); r2 <- lavaan::lavInspect(fit,"r2"); r2 <- as.list(r2[is.finite(r2)]); names(r2) <- vapply(names(r2),decode,"")
  list(status="COMPLETED",results=res,sample_audit=z$audit,diagnostics=list(warnings=warnings,converged=TRUE),backend_versions=list(R=as.character(getRversion()),jsonlite=as.character(utils::packageVersion("jsonlite")),lavaan=as.character(utils::packageVersion("lavaan"))),model_summary=list(expected_result_ids=lapply(res,function(x) list(x$outcome_id,x$term_id,x$contrast_id)),fit_measures=measures,r_squared=r2,unavailable_fit_measures=fit_missing,estimator=m$estimator,std_lv=isTRUE(m$std_lv),fixed_x=isTRUE(m$fixed_x)))
}
