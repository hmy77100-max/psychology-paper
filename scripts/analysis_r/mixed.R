execute_model <- function(payload) {
  s <- payload$spec; m <- s$model; inf <- s$inference
  if (!is.null(m$standard_error) && !identical(m$standard_error,"conventional")) fail("UNSUPPORTED_MODEL", "Mixed-model robust standard errors are unsupported", "UNSUPPORTED_MODEL")
  if (!requireNamespace("lme4",quietly=TRUE) || (m$method=="linear_mixed" && !requireNamespace("lmerTest",quietly=TRUE))) fail("MISSING_PACKAGE", "lme4 and (for LMM) lmerTest are required")
  if (length(inf$bootstrap)) fail("UNSUPPORTED_MODEL", "Mixed bootstrap is not implemented", "UNSUPPORTED_MODEL")
  if (!identical(inf$alternative,"two-sided")) fail("UNSUPPORTED_MODEL", "Only two-sided inference is supported", "UNSUPPORTED_MODEL")
  if (!is.null(m$trials) && m$method!="binomial_mixed" || !is.null(m$offset) && m$method!="poisson_mixed") fail("INVALID_SPEC", "Trials and offset must match family")
  pred <- unique(c(unlist(m$predictors),unlist(m$covariates))); random <- m$random
  if (!length(random) || !length(pred)) fail("INVALID_SPEC", "Fixed predictors and random effects required")
  groups <- vapply(random,function(x) x$group,""); slopes <- unique(unlist(lapply(random,function(x) x$slopes)))
  if (anyDuplicated(groups) || any(!slopes %in% pred)) fail("INVALID_SPEC", "Invalid random grouping or slopes")
  vars <- unique(c(m$outcome,pred,groups,m$trials,m$offset)); fac <- m$factors; if (is.null(fac)) fac <- list()
  fm <- s$field_map; keys <- vapply(fm,function(x)x$variable,""); cols <- vapply(fm,function(x)x$column,"")
  for (g in groups) {
    col <- cols[match(g,keys)]; if (is.na(col)) fail("MISSING_COLUMN", "Missing grouping variable")
    values <- unique(vapply(payload$rows,function(r) if (is.null(r[[col]])) "" else as.character(r[[col]]),"")); values <- values[nzchar(values)]
    fac[[g]] <- values
  }
  z <- prepare_frame(payload,vars,fac,grouping_ids=groups); d <- z$data; map <- z$map; n <- z$n
  for (v in names(m$center)) { k <- m$center[[v]]; if (!v %in% pred || !is.numeric(k) || length(k)!=1L || !is.finite(k) || is.factor(d[[map[[v]]]])) fail("INVALID_SPEC", "Invalid centering constant"); d[[map[[v]]]] <- d[[map[[v]]]]-k }
  fixed <- unname(map[pred]); for (inter in m$interactions) { v <- unlist(inter); if (length(v)<2L || any(!v %in% pred) || anyDuplicated(v)) fail("INVALID_SPEC", "Invalid interaction"); fixed <- c(fixed,paste(unname(map[v]),collapse=":")) }
  if (identical(m$intercept,FALSE)) fixed <- c("0",fixed)
  re <- vapply(random,function(x) { sl <- unlist(x$slopes); if (any(!sl %in% pred)) fail("INVALID_SPEC", "Unknown random slope"); if (identical(x$correlated,FALSE) && any(sl %in% names(fac))) fail("UNSUPPORTED_MODEL", "Uncorrelated categorical random slopes are unsupported", "UNSUPPORTED_MODEL"); if (!is.null(x$correlated) && !is.logical(x$correlated)) fail("INVALID_SPEC", "Invalid random correlation"); paste0("(1",if(length(sl)) paste0(" + ",paste(unname(map[sl]),collapse=" + ")) else "",if(identical(x$correlated,FALSE)) " || " else " | ",map[[x$group]],")") },"")
  response <- unname(map[[m$outcome]]); y <- d[[response]]
  if(!is.null(m$trials)) { trials <- d[[map[[m$trials]]]]; if(any(trials<=0 | trials!=floor(trials) | y<0 | y>trials | y!=floor(y))) fail("INVALID_DATA", "Invalid successes or trials"); d$.success <- y; d$.failure <- trials-y; response <- "cbind(.success,.failure)" }
  if(!is.null(m$offset)) { d$.offset <- d[[map[[m$offset]]]]; fixed <- c(fixed,"offset(.offset)") }
  f <- stats::as.formula(paste(response,"~",paste(c(fixed,re),collapse=" + ")))
  warnings <- list(); fit <- withCallingHandlers({
    if (m$method=="linear_mixed") {
      if (!m$estimation %in% c("ML","REML")) fail("INVALID_SPEC", "LMM estimation must be ML or REML")
      lmerTest::lmer(f,data=d,REML=m$estimation=="REML",na.action=stats::na.fail)
    } else {
      if (!identical(m$estimation,"ML")) fail("INVALID_SPEC", "GLMM estimation must be ML")
      family <- if (m$method=="binomial_mixed") stats::binomial() else stats::poisson()
      y <- d[[map[[m$outcome]]]]; if (m$method=="binomial_mixed" && is.null(m$trials) && any(!y %in% c(0,1))) fail("INVALID_DATA", "Binary outcome must be 0/1")
      if (m$method=="poisson_mixed" && any(y<0 | y!=floor(y))) fail("INVALID_DATA", "Poisson outcome must be nonnegative integers")
      lme4::glmer(f,data=d,family=family,nAGQ=1L,na.action=stats::na.fail)
    }
  },warning=function(w) { warnings[[length(warnings)+1L]] <<- conditionMessage(w); invokeRestart("muffleWarning") })
  messages <- fit@optinfo$conv$lme4$messages; serious <- if(is.null(messages)) character() else messages[!startsWith(messages,"boundary (singular) fit")]; if (length(serious) || !is.null(fit@optinfo$conv$opt) && any(fit@optinfo$conv$opt != 0L)) fail("NONCONVERGED", "Mixed model failed convergence checks", "NONCONVERGED")
  if(length(messages)) warnings <- c(warnings,as.list(messages))
  if (length(lme4::fixef(fit)) != ncol(lme4::getME(fit,"X")) || !is.null(attr(lme4::getME(fit,"X"),"col.dropped"))) fail("RANK_DEFICIENT", "Rank deficient fixed effects")
  tab <- summary(fit)$coefficients; if (any(!is.finite(tab))) fail("NONFINITE_ESTIMATE", "Nonfinite model coefficient")
  namesafe <- function(x) decode_tokens(x,map)
  res <- lapply(seq_len(nrow(tab)),function(i) {
    est <- unname(tab[i,1]); se <- unname(tab[i,2]); df <- if (m$method=="linear_mixed") unname(tab[i,"df"]) else NULL
    crit <- if (is.null(df)) stats::qnorm((1+inf$confidence_level)/2) else stats::qt((1+inf$confidence_level)/2,df)
    row <- list(outcome_id=m$outcome,term_id=namesafe(rownames(tab)[i]),contrast_id="coefficient",kind="coefficient",estimate=est,se=se,statistic=unname(tab[i,if(is.null(df)) "z value" else "t value"]),p=unname(tab[i,ncol(tab)]),ci=c(est-crit*se,est+crit*se),confidence_level=inf$confidence_level,ci_alternative="two-sided",n=n)
    if (!is.null(df)) row$df <- df; row
  })
  vc <- as.data.frame(lme4::VarCorr(fit)); for (i in seq_len(nrow(vc))) res[[length(res)+1L]] <- list(outcome_id=m$outcome,term_id=paste0("random:",namesafe(vc$grp[i]),":",namesafe(vc$var1[i]),if(!is.na(vc$var2[i])) paste0(":",namesafe(vc$var2[i])) else ""),contrast_id="variance",kind="variance",estimate=unname(vc$vcov[i]),n=n)
  nested_details <- NULL
  if (!is.null(inf$nested_test)) {
    if (!identical(m$estimation,"ML")) fail("UNSUPPORTED_MODEL", "Nested fixed-effect likelihood ratio tests require ML; REML is never refitted", "UNSUPPORTED_MODEL")
    nested <- inf$nested_test; if (!setequal(names(nested),c("predictors","interactions"))) fail("INVALID_SPEC", "Nested test requires predictors and interactions only"); reduced_pred <- unlist(nested$predictors); reduced_inter <- nested$interactions
    if (anyDuplicated(reduced_pred) || any(!reduced_pred %in% pred)) fail("INVALID_SPEC", "Nested predictors must be a subset of full predictors")
    key <- function(v) paste(sort(unlist(v)),collapse="|")
    full_keys <- vapply(m$interactions,key,""); reduced_keys <- vapply(reduced_inter,key,"")
    if (anyDuplicated(reduced_keys) || any(!reduced_keys %in% full_keys) || any(vapply(reduced_inter,function(v) any(!unlist(v) %in% reduced_pred),logical(1)))) fail("INVALID_SPEC", "Nested interactions must be a subset with retained predictors")
    if (length(reduced_pred)==length(pred) && length(reduced_keys)==length(full_keys)) fail("INVALID_SPEC", "Nested model must remove a fixed effect")
    reduced_fixed <- unname(map[reduced_pred]); for(inter in reduced_inter) reduced_fixed <- c(reduced_fixed,paste(unname(map[unlist(inter)]),collapse=":"))
    if (identical(m$intercept,FALSE)) reduced_fixed <- c("0",reduced_fixed)
    if (!is.null(m$offset)) reduced_fixed <- c(reduced_fixed,"offset(.offset)")
    reduced_formula <- stats::as.formula(paste(response,"~",paste(c(reduced_fixed,re),collapse=" + ")))
    reduced <- withCallingHandlers(if(m$method=="linear_mixed") lme4::lmer(reduced_formula,data=d,REML=FALSE,na.action=stats::na.fail) else lme4::glmer(reduced_formula,data=d,family=if(m$method=="binomial_mixed") stats::binomial() else stats::poisson(),nAGQ=1L,na.action=stats::na.fail),warning=function(w){warnings[[length(warnings)+1L]] <<- conditionMessage(w);invokeRestart("muffleWarning")})
    other_messages <- reduced@optinfo$conv$lme4$messages; serious2 <- if(is.null(other_messages)) character() else other_messages[!startsWith(other_messages,"boundary (singular) fit")]
    if(length(serious2) || !is.null(reduced@optinfo$conv$opt) && any(reduced@optinfo$conv$opt!=0L)) fail("NONCONVERGED", "Nested model failed convergence checks", "NONCONVERGED")
    if (!is.null(attr(lme4::getME(reduced,"X"),"col.dropped")) || stats::nobs(reduced)!=stats::nobs(fit)) fail("INVALID_DATA", "Nested model is rank deficient or uses different rows")
    lrt <- as.data.frame(stats::anova(reduced,fit,refit=FALSE)); if(nrow(lrt)!=2L || any(!c("Chisq","Df","Pr(>Chisq)") %in% names(lrt))) fail("INCOMPLETE_OUTPUT", "Unexpected nested-model comparison")
    values <- unlist(lrt[2,c("Chisq","Df","Pr(>Chisq)")]); if(any(!is.finite(values)) || values[[2]]<=0) fail("INVALID_DATA", "Nested-model comparison is not estimable")
    res[[length(res)+1L]] <- list(outcome_id=m$outcome,term_id="nested_model",contrast_id="likelihood_ratio",kind="fit",statistic=unname(values[[1]]),df_num=unname(values[[2]]),p=unname(values[[3]]),n=n)
    nested_details <- list(reduced_log_likelihood=as.numeric(stats::logLik(reduced)),full_log_likelihood=as.numeric(stats::logLik(fit)),reduced_parameters=attr(stats::logLik(reduced),"df"),full_parameters=attr(stats::logLik(fit),"df"),shared_n=n)
  }
  res <- c(res,extract_comparisons(fit,payload,map,n,m$outcome))
  audit <- z$audit; audit$n_groups <- as.list(setNames(vapply(groups,function(g)nlevels(d[[map[[g]]]]),integer(1)),groups))
  versions <- list(R=as.character(getRversion()),jsonlite=as.character(utils::packageVersion("jsonlite")),lme4=as.character(utils::packageVersion("lme4")))
  if (length(inf$comparisons)) versions$emmeans <- as.character(utils::packageVersion("emmeans"))
  if (m$method=="linear_mixed") versions$lmerTest <- as.character(utils::packageVersion("lmerTest"))
  list(status="COMPLETED",results=res,sample_audit=audit,diagnostics=list(warnings=warnings,converged=TRUE,singular=lme4::isSingular(fit)),backend_versions=versions,model_summary=list(expected_result_ids=lapply(res,function(x) list(x$outcome_id,x$term_id,x$contrast_id)),log_likelihood=as.numeric(stats::logLik(fit)),nested_test=nested_details,estimation=m$estimation))
}
