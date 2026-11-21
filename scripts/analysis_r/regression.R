execute_model <- function(payload) {
  s <- payload$spec; m <- s$model; inf <- s$inference
  family_name <- if(m$method=="linear_regression") "linear" else if(m$method=="binomial_regression") "binomial" else if(m$method=="poisson_regression") "poisson" else if(m$method=="moderation") m$family else "unknown"
  if (!family_name %in% c("linear","binomial","poisson")) fail("UNSUPPORTED_MODEL", "Unknown regression family", "UNSUPPORTED_MODEL")
  if (family_name != "linear" && !is.null(m$standard_error) && m$standard_error != "conventional") fail("UNSUPPORTED_MODEL", "GLM supports conventional standard errors only", "UNSUPPORTED_MODEL")
  if (length(inf$bootstrap)) fail("UNSUPPORTED_MODEL", "Bootstrap is not implemented", "UNSUPPORTED_MODEL")
  if (!identical(inf$alternative, "two-sided")) fail("UNSUPPORTED_MODEL", "Only two-sided inference is supported", "UNSUPPORTED_MODEL")
  predictors <- unique(c(unlist(m$predictors), unlist(m$covariates)))
  if (length(setdiff(names(m$center),predictors))) fail("INVALID_SPEC", "Centering applies only to declared predictors")
  if (m$outcome %in% names(m$factors)) fail("INVALID_SPEC", "Outcome must be numeric")
  if (!length(predictors) || !is.character(m$outcome)) fail("INVALID_SPEC", "Outcome and predictors are required")
  vars <- unique(c(m$outcome, predictors, m$trials, m$offset)); mapping <- s$field_map
  vnames <- vapply(mapping, function(x) x$variable, ""); source_names <- vapply(mapping, function(x) x$column, "")
  if (anyDuplicated(vnames) || any(!vars %in% vnames)) fail("INVALID_SPEC", "Missing or duplicate field mapping")
  columns <- unlist(payload$columns); cols <- source_names[match(vars, vnames)]
  if (any(!cols %in% columns) || anyDuplicated(cols)) fail("MISSING_COLUMN", "Missing or duplicate source column")
  rows <- payload$rows; input_n <- length(rows); selected <- rows; audits <- list()
  for (rule in s$sample$filters) {
    col <- if (!is.null(rule$variable)) source_names[match(rule$variable, vnames)] else rule$column
    if (length(col) != 1L || is.na(col) || !col %in% columns) fail("INVALID_FILTER", "Unknown filter column")
    allowed <- if (identical(rule$op, "eq")) list(rule$value) else rule$values
    if (!rule$op %in% c("eq", "in", "not_in") || !is.list(allowed)) fail("INVALID_FILTER", "Invalid filter")
    before <- length(selected)
    keep <- vapply(selected, function(row) { hit <- any(vapply(allowed, function(v) identical(row[[col]], v), logical(1))); if (rule$op == "not_in") !hit else hit }, logical(1))
    selected <- selected[keep]; audits[[length(audits)+1L]] <- list(column=col, op=rule$op, before=before, after=length(selected), excluded=before-length(selected))
  }
  if (!s$sample$missing %in% c("error", "complete_case")) fail("INVALID_SPEC", "Unsupported missing policy")
  missing_values <- s$data$read_options$missing_values; if (is.null(missing_values)) missing_values <- list("")
  missing_cell <- function(x) is.null(x) || (length(x)==1L && (is.na(x) || any(vapply(missing_values, function(v) identical(v,x), logical(1)))))
  good <- vapply(selected, function(row) !any(vapply(cols, function(col) missing_cell(row[[col]]), logical(1))), logical(1))
  if (any(!good) && s$sample$missing == "error") fail("MISSING_DATA", "Missing required model value")
  excluded <- sum(!good); selected <- selected[good]; n <- length(selected)
  if (n < 3L) fail("INSUFFICIENT_SAMPLE", "Too few complete observations")
  safe <- paste0("v", seq_along(vars), "__"); dat <- list(); labels <- setNames(vars, safe)
  factors <- m$factors; if (is.null(factors)) factors <- list()
  for (i in seq_along(vars)) {
    raw <- lapply(selected, function(row) row[[cols[[i]]]])
    if (vars[[i]] %in% names(factors)) {
      if (!is.null(m$center[[vars[[i]]]])) fail("INVALID_SPEC", "Cannot center categorical variables")
      lev <- unlist(factors[[vars[[i]]]], use.names=FALSE); val <- vapply(raw, as.character, "")
      if (length(lev)<2L || anyDuplicated(lev) || any(!val %in% lev) || any(!lev %in% val)) fail("INVALID_FACTOR", "Factor levels do not match observations")
      dat[[safe[[i]]]] <- factor(val, levels=lev)
    } else {
      if (any(vapply(raw, is.logical, logical(1)))) fail("INVALID_NUMERIC", "Boolean numeric values require recoding")
      num <- suppressWarnings(as.numeric(unlist(raw))); if (length(num)!=n || any(!is.finite(num))) fail("INVALID_NUMERIC", "Nonfinite or nonnumeric model value")
      constant <- m$center[[vars[[i]]]]; if (!is.null(constant)) { if (length(constant)!=1 || !is.numeric(constant) || !is.finite(constant)) fail("INVALID_SPEC", "Invalid centering constant"); num <- num-constant }
      dat[[safe[[i]]]] <- num
    }
  }
  d <- as.data.frame(dat); map <- setNames(safe, vars); terms <- unname(map[predictors])
  for (inter in m$interactions) { v <- unlist(inter); if (length(v)<2L || any(!v %in% predictors) || anyDuplicated(v)) fail("INVALID_SPEC", "Invalid interaction"); terms <- c(terms, paste(unname(map[v]), collapse=":")) }
  form <- reformulate(terms, response=unname(map[[m$outcome]]), intercept=!identical(m$intercept,FALSE))
  y <- d[[map[[m$outcome]]]]; warnings <- list()
  if (!is.null(m$trials) && family_name!="binomial" || !is.null(m$offset) && family_name!="poisson") fail("INVALID_SPEC", "Trials and offset must match family")
  if (family_name=="binomial") {
    if (!requireNamespace("detectseparation",quietly=TRUE)) fail("MISSING_PACKAGE", "detectseparation is required for binomial regression")
    if (!is.null(m$trials)) { trials <- d[[map[[m$trials]]]]; if(any(trials<=0 | trials!=floor(trials) | y<0 | y>trials | y!=floor(y))) fail("INVALID_DATA", "Invalid successes or trials"); d$.success <- y; d$.failure <- trials-y; form[[2]] <- quote(cbind(.success,.failure)) }
    else if(any(!y %in% c(0,1))) fail("INVALID_DATA", "Binomial outcomes must be 0/1")
    sep <- stats::glm(form,data=d,family=stats::binomial(),method=detectseparation::detect_separation,na.action=stats::na.fail)
    if (any(!is.finite(stats::coef(sep)))) fail("SEPARATION", "Complete or quasi-complete separation detected")
  }
  if (family_name=="poisson" && any(y<0 | y!=floor(y))) fail("INVALID_DATA", "Poisson outcome must be nonnegative integers")
  if (!is.null(m$offset)) { d$.offset <- d[[map[[m$offset]]]]; form <- update(form, . ~ . + offset(.offset)) }
  fit <- withCallingHandlers(if(family_name=="linear") stats::lm(form,data=d,na.action=stats::na.fail) else stats::glm(form,data=d,family=if(family_name=="binomial") stats::binomial() else stats::poisson(),na.action=stats::na.fail),warning=function(w){warnings[[length(warnings)+1L]] <<- conditionMessage(w); invokeRestart("muffleWarning")})
  if (family_name!="linear" && !isTRUE(fit$converged)) fail("NONCONVERGED", "GLM did not converge", "NONCONVERGED")
  if (fit$rank < ncol(model.matrix(fit))) fail("RANK_DEFICIENT", "Model matrix is rank deficient")
  if (fit$df.residual <= 0) fail("INSUFFICIENT_SAMPLE", "No residual degrees of freedom")
  se_type <- m$standard_error; if (is.null(se_type)) se_type <- "conventional"
  vc <- if (identical(se_type,"conventional")) stats::vcov(fit) else if (identical(se_type,"HC3") && family_name=="linear") {
    if (!requireNamespace("sandwich", quietly=TRUE)) fail("MISSING_PACKAGE", "Package sandwich is required")
    sandwich::vcovHC(fit, type="HC3")
  } else fail("UNSUPPORTED_MODEL", "Unsupported standard error", "UNSUPPORTED_MODEL")
  est <- stats::coef(fit); se <- sqrt(diag(vc)); stat <- est/se; df <- fit$df.residual
  if (any(!is.finite(c(est,se,stat)))) fail("NONFINITE_ESTIMATE", "Nonfinite coefficient or uncertainty")
  alpha <- 1-inf$confidence_level; critical <- if(family_name=="linear") stats::qt(1-alpha/2,df) else stats::qnorm(1-alpha/2)
  p <- if(family_name=="linear") 2*stats::pt(abs(stat),df,lower.tail=FALSE) else 2*stats::pnorm(abs(stat),lower.tail=FALSE)
  if (!is.finite(critical)) fail("INVALID_SPEC", "Invalid confidence level")
  convert_name <- function(x) decode_tokens(x,map)
  result <- lapply(seq_along(est), function(i) list(outcome_id=m$outcome,term_id=convert_name(names(est)[[i]]),contrast_id="coefficient",kind="coefficient",estimate=unname(est[[i]]),se=unname(se[[i]]),statistic=unname(stat[[i]]),df=df,p=unname(p[[i]]),ci=unname(c(est[[i]]-critical*se[[i]],est[[i]]+critical*se[[i]])),confidence_level=inf$confidence_level,ci_alternative="two-sided",n=n))
  result <- c(result, extract_comparisons(fit,payload,map,n,m$outcome,if(se_type=="HC3") vc else NULL))
  if(family_name!="linear") for(i in seq_along(result)) { result[[i]]$df <- NULL; result[[i]]$scale <- "link"; if(result[[i]]$kind=="coefficient") { value <- exp(result[[i]]$estimate); if(!is.finite(value)) fail("NONFINITE_ESTIMATE", "Exponentiated coefficient overflows"); result[[i]]$exponentiated_estimate <- value } }
  versions <- list(R=as.character(getRversion()), jsonlite=as.character(utils::packageVersion("jsonlite")), stats=as.character(utils::packageVersion("stats")))
  if (family_name=="binomial") versions$detectseparation <- as.character(utils::packageVersion("detectseparation"))
  if (length(inf$comparisons)) versions$emmeans <- as.character(utils::packageVersion("emmeans"))
  if (se_type=="HC3") versions$sandwich <- as.character(utils::packageVersion("sandwich"))
  list(status="COMPLETED",results=result,sample_audit=list(input_rows=input_n,effective_n=n,model_rows=n,excluded_missing=excluded,excluded_filters=audits),diagnostics=list(warnings=warnings,converged=TRUE,dispersion=if(family_name=="poisson") sum(stats::residuals(fit,type="pearson")^2)/df else NULL),backend_versions=versions,model_summary=list(expected_result_ids=lapply(result,function(x) list(x$outcome_id,x$term_id,x$contrast_id)),r_squared=if(family_name=="linear") unname(summary(fit)$r.squared) else NULL,adjusted_r_squared=if(family_name=="linear") unname(summary(fit)$adj.r.squared) else NULL, family=family_name,residual_df=df,standard_error=se_type))
}
