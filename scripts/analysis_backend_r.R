# Fixed JSON bridge. No package installation, arbitrary formula, or user-supplied code.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) stop("Expected payload and output paths")
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("Missing required package: jsonlite")
script_arg <- grep("^--file=", commandArgs(), value = TRUE)
script_dir <- dirname(normalizePath(sub("^--file=", "", script_arg[[1L]]), mustWork = TRUE))
fail <- function(code, message, status = "INVALID_DATA") {
  e <- simpleError(message); e$code <- code; e$status <- status; stop(e)
}
# Shared preparation for bounded model wrappers. Every model variable is mapped to a generated name.
prepare_frame <- function(payload, vars, categorical = list(), allow_fiml = FALSE, grouping_ids = character()) {
  s <- payload$spec; vars <- unique(vars); fm <- s$field_map
  keys <- vapply(fm, function(x) x$variable, ""); vals <- vapply(fm, function(x) x$column, "")
  if (anyDuplicated(keys) || any(!vars %in% keys)) fail("INVALID_SPEC", "Invalid field map")
  cols <- vals[match(vars, keys)]; if (any(!cols %in% unlist(payload$columns)) || anyDuplicated(cols)) fail("MISSING_COLUMN", "Missing or duplicate source column")
  selected <- payload$rows; input_n <- length(selected); audits <- list()
  for (rule in s$sample$filters) {
    col <- if (!is.null(rule$variable)) vals[match(rule$variable,keys)] else rule$column
    if (length(col)!=1L || is.na(col) || !col %in% unlist(payload$columns)) fail("INVALID_FILTER", "Unknown filter column")
    allowed <- if (identical(rule$op,"eq")) list(rule$value) else rule$values
    if (!rule$op %in% c("eq","in","not_in") || !is.list(allowed)) fail("INVALID_FILTER", "Invalid filter")
    before <- length(selected); keep <- vapply(selected,function(row) { hit <- any(vapply(allowed,function(v) identical(row[[col]],v),logical(1))); if (rule$op=="not_in") !hit else hit },logical(1))
    selected <- selected[keep]; audits[[length(audits)+1L]] <- list(column=col,op=rule$op,before=before,after=length(selected),excluded=before-length(selected))
  }
  if (!s$sample$missing %in% c("error","complete_case",if (allow_fiml) "fiml")) fail("UNSUPPORTED_MODEL", "Missing policy unsupported for this model", "UNSUPPORTED_MODEL")
  missing_values <- s$data$read_options$missing_values; if (is.null(missing_values)) missing_values <- list("")
  absent <- function(x) is.null(x) || (length(x)==1L && (is.na(x) || any(vapply(missing_values,function(v) identical(x,v),logical(1)))))
  good <- vapply(selected,function(row) !any(vapply(cols,function(col) absent(row[[col]]),logical(1))),logical(1))
  if (any(!good) && s$sample$missing=="error") fail("MISSING_DATA", "Missing required model value")
  if (s$sample$missing != "fiml") selected <- selected[good]; n <- length(selected); if (n<3L) fail("INSUFFICIENT_SAMPLE", "Too few observations")
  safe <- paste0("v",seq_along(vars),"__"); dat <- list()
  for (i in seq_along(vars)) {
    raw <- lapply(selected,function(row) row[[cols[[i]]]])
    if (vars[[i]] %in% names(categorical)) {
      lev <- unlist(categorical[[vars[[i]]]],use.names=FALSE); val <- vapply(raw,as.character,"")
      if (!length(lev) || anyDuplicated(lev) || any(!val %in% lev)) fail("INVALID_FACTOR", "Factor levels do not match observations")
      if (!vars[[i]] %in% grouping_ids && any(!lev %in% val)) fail("INCOMPLETE_DESIGN", "A declared model factor or ordered category has no observations")
      value <- factor(val, levels=lev)
      dat[[safe[[i]]]] <- if (vars[[i]] %in% grouping_ids) droplevels(value) else value
    } else {
      if (any(vapply(raw,is.logical,logical(1)))) fail("INVALID_NUMERIC", "Boolean numeric values require recoding")
      num <- vapply(raw,function(x) if(absent(x)) NA_real_ else suppressWarnings(as.numeric(x)),numeric(1)); if (length(num)!=n || any(is.nan(num) | is.infinite(num)) || (!allow_fiml && any(is.na(num)))) fail("INVALID_NUMERIC", "Nonfinite or nonnumeric model value"); if(any(vapply(seq_along(raw),function(j) !absent(raw[[j]]) && is.na(num[[j]]),logical(1)))) fail("INVALID_NUMERIC", "Nonnumeric model value")
      dat[[safe[[i]]]] <- num
    }
  }
  list(data=as.data.frame(dat),map=setNames(safe,vars),n=n,audit=list(input_rows=input_n,effective_n=n,model_rows=n,excluded_missing=if(s$sample$missing=="fiml") 0L else sum(!good),excluded_filters=audits))
}

decode_tokens <- function(x, map) {
  matches <- gregexpr("(?<![A-Za-z0-9])v[0-9]+__", x, perl=TRUE)
  pieces <- regmatches(x,matches)
  pieces <- lapply(pieces,function(tokens) vapply(tokens,function(token) { index <- match(token,unname(map)); if(is.na(index)) token else names(map)[[index]] },""))
  regmatches(x,matches) <- pieces
  x
}
extract_comparisons <- function(fit, payload, map, n, outcome, vcov_override=NULL) {
  inf <- payload$spec$inference; comps <- inf$comparisons; if (!length(comps)) return(list())
  if (!requireNamespace("emmeans",quietly=TRUE)) fail("MISSING_PACKAGE", "Package emmeans is required for comparisons")
  result <- list(); families <- character()
  for (cmp in comps) {
    if (is.null(cmp$id) || is.null(cmp$family_id)) fail("INVALID_SPEC", "Comparison identity and family required")
    if (!is.null(cmp$slope)) {
      if (!cmp$slope %in% names(map) || length(cmp$factor) || !length(cmp$at)) fail("INVALID_SPEC", "Invalid simple slope")
      at <- list(); for (nm in names(cmp$at)) { if (!nm %in% names(map) || !is.numeric(cmp$at[[nm]]) || length(cmp$at[[nm]])!=1L || !is.finite(cmp$at[[nm]])) fail("INVALID_SPEC", "Invalid slope conditioning value"); center <- payload$spec$model$center[[nm]]; at[[map[[nm]]]] <- cmp$at[[nm]] - if(is.null(center)) 0 else center }
      args <- list(object=fit,specs=~1,var=map[[cmp$slope]],at=at); if(!is.null(vcov_override)) args$vcov. <- vcov_override; grid <- do.call(emmeans::emtrends,args)
      out <- as.data.frame(summary(grid,infer=c(TRUE,TRUE),level=inf$confidence_level,adjust="none")); estimate_name <- grep("\\.trend$",names(out),value=TRUE)
      term <- cmp$slope
    } else {
      if (is.null(cmp$factor) || length(cmp$levels)!=2L || !cmp$factor %in% names(map)) fail("INVALID_SPEC", "Invalid factor comparison")
      at <- list(); if (length(cmp$by)) for (nm in names(cmp$by)) { if (!nm %in% names(map)) fail("INVALID_SPEC", "Unknown comparison conditioning variable"); value <- cmp$by[[nm]]; center <- payload$spec$model$center[[nm]]; if (!is.null(center)) { if (!is.numeric(value) || length(value)!=1L || !is.finite(value)) fail("INVALID_SPEC", "Invalid centered conditioning value"); value <- value-center }; at[[map[[nm]]]] <- value }
      args <- list(object=fit,specs=map[[cmp$factor]],at=at); if(!is.null(vcov_override)) args$vcov. <- vcov_override; grid <- do.call(emmeans::emmeans,args)
      levels <- as.character(grid@grid[[map[[cmp$factor]]]]); pair <- unlist(cmp$levels)
      if (any(!pair %in% levels) || anyDuplicated(pair)) fail("INVALID_SPEC", "Comparison levels are invalid")
      weights <- rep(0,length(levels)); weights[match(pair[1],levels)] <- 1; weights[match(pair[2],levels)] <- -1
      out <- as.data.frame(summary(emmeans::contrast(grid,method=setNames(list(weights),cmp$id)),infer=c(TRUE,TRUE),level=inf$confidence_level,adjust="none")); estimate_name <- "estimate"; term <- cmp$factor
    }
    lower <- if("lower.CL" %in% names(out)) "lower.CL" else "asymp.LCL"; upper <- if("upper.CL" %in% names(out)) "upper.CL" else "asymp.UCL"
    if (length(estimate_name)!=1L || !all(c(estimate_name,"SE","p.value",lower,upper) %in% names(out)) || nrow(out)!=1L || any(!is.finite(unlist(out[1,c(estimate_name,"SE","p.value",lower,upper)])))) fail("NONFINITE_ESTIMATE", "Invalid comparison output")
    r <- list(outcome_id=outcome,term_id=term,contrast_id=cmp$id,kind="contrast",estimate=unname(out[[estimate_name]]),se=unname(out$SE),p=unname(out$p.value),ci=c(unname(out[[lower]]),unname(out[[upper]])),confidence_level=inf$confidence_level,ci_alternative="two-sided",ci_adjustment="none",family_id=cmp$family_id,n=n)
    if(is.finite(out$df)) r$df <- unname(out$df); result[[length(result)+1L]] <- r; families <- c(families,cmp$family_id)
  }
  for (family in unique(families)) {
    method <- inf$adjustments[[family]]; if (is.null(method) || !method %in% c("holm","bonferroni","none")) fail("INVALID_SPEC", "Comparison family adjustment required")
    idx <- which(families==family); adjusted <- stats::p.adjust(vapply(result[idx],function(x)x$p,numeric(1)),method=method)
    for(j in seq_along(idx)) { result[[idx[j]]]$p_adjusted <- adjusted[j]; result[[idx[j]]]$p_adjustment <- method }
  }
  result
}

result <- tryCatch({
  payload <- jsonlite::fromJSON(args[[1L]], simplifyVector = FALSE)
  spec <- payload$spec; method <- spec$model$method
  modules <- c(factorial_anova="anova", repeated_anova="anova", mixed_anova="anova",
    linear_regression="regression", binomial_regression="regression", poisson_regression="regression",
    moderation="regression", linear_mixed="mixed", binomial_mixed="mixed", poisson_mixed="mixed",
    mediation="mediation", cfa="sem", sem="sem")
  if (is.null(method) || length(method) != 1L || !method %in% names(modules))
    fail("UNSUPPORTED_MODEL", "Unknown model", "UNSUPPORTED_MODEL")
  if (!is.null(spec$inference$nested_test) && !method %in% c("linear_mixed","binomial_mixed","poisson_mixed")) fail("UNSUPPORTED_MODEL", "Nested likelihood-ratio testing is limited to mixed models", "UNSUPPORTED_MODEL")
  source(file.path(script_dir, "analysis_r", paste0(unname(modules[[method]]), ".R")), local = TRUE)
  execute_model(payload)
}, error = function(e) list(status = if (!is.null(e$status)) e$status else "INVALID_DATA",
  errors = list(list(code = if (!is.null(e$code)) e$code else "BACKEND_ERROR", message = conditionMessage(e)))))
jsonlite::write_json(result, args[[2L]], auto_unbox = TRUE, null = "null", na = "null", digits = 16)
