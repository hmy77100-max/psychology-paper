execute_model <- function(payload) {
  s <- payload$spec; m <- s$model; inf <- s$inference
  if (!requireNamespace("afex",quietly=TRUE)) fail("MISSING_PACKAGE", "Package afex is required")
  if (length(inf$bootstrap)) fail("UNSUPPORTED_MODEL", "ANOVA bootstrap is not implemented", "UNSUPPORTED_MODEL")
  if (!identical(inf$alternative,"two-sided") || length(m$covariates)) fail("UNSUPPORTED_MODEL", "Unsupported ANOVA inference or covariates", "UNSUPPORTED_MODEL")
  between <- unlist(m$between); within <- unlist(m$within); allfac <- c(between,within)
  if (!length(allfac) || anyDuplicated(allfac) || !m$ss_type %in% c("II","III") || !m$correction %in% c("none","GG","HF")) fail("INVALID_SPEC", "Invalid factors, sums of squares, or correction")
  if (m$method=="factorial_anova" && length(within) || m$method=="repeated_anova" && (!length(within) || length(between)) || m$method=="mixed_anova" && (!length(within) || !length(between))) fail("INVALID_SPEC", "Method and factor roles disagree")
  if (!all(allfac %in% names(m$factors))) fail("INVALID_SPEC", "Explicit factor levels required")
  if (!m$aggregation %in% c("none","mean")) fail("INVALID_SPEC", "Explicit aggregation required")
  id <- m$subject_id; if ((length(within) && (is.null(id) || !nzchar(id))) || (!is.null(id) && id %in% c(m$outcome,allfac))) fail("INVALID_SPEC", "Subject ID required")
  vars <- unique(c(m$outcome,allfac,id)); cats <- m$factors
  if (!is.null(id)) {
    fm <- s$field_map; keys <- vapply(fm,function(x)x$variable,""); cols <- vapply(fm,function(x)x$column,""); col <- cols[match(id,keys)]
    if (is.na(col)) fail("MISSING_COLUMN", "Missing subject ID")
    cats[[id]] <- unique(vapply(payload$rows,function(r) if(is.null(r[[col]])) "" else as.character(r[[col]]),"")); cats[[id]] <- cats[[id]][nzchar(cats[[id]])]
  }
  z <- prepare_frame(payload,vars,cats,grouping_ids=if(!is.null(id)) id else character()); d <- z$data; map <- z$map; n <- z$n
  if (is.null(id)) { d$.subject <- factor(seq_len(n)); idcol <- ".subject" } else idcol <- map[[id]]
  if (!length(within) && !is.null(id) && anyDuplicated(d[[idcol]])) fail("DUPLICATE_SUBJECT", "Factorial ANOVA requires one observation per subject")
  design <- unname(map[allfac]); grid <- do.call(table,d[design]); if (any(grid==0)) fail("INCOMPLETE_DESIGN", "Empty factorial cell")
  if (length(within)) {
    for (b in between) if (any(vapply(split(d[[map[[b]]]],d[[idcol]]),function(x) length(unique(x))!=1L,logical(1)))) fail("INVALID_DESIGN", "Between factor varies within subject")
    cell <- interaction(d[c(idcol,unname(map[within]))],drop=TRUE); counts <- table(cell)
    if (any(counts>1L) && m$aggregation=="none") fail("DUPLICATE_CELL", "Duplicate subject-condition observations require explicit aggregation")
    expected <- prod(vapply(within,function(v)nlevels(d[[map[[v]]]]),integer(1)))
    per_subject <- tapply(as.character(cell),d[[idcol]],function(x) length(unique(x)))
    if (any(per_subject!=expected)) fail("INCOMPLETE_DESIGN", "Incomplete within-subject cells")
  }
  warnings <- list(); fit <- withCallingHandlers(afex::aov_ez(id=idcol,dv=map[[m$outcome]],data=d,between=if(length(between)) unname(map[between]) else NULL,within=if(length(within)) unname(map[within]) else NULL,type=if(m$ss_type=="II") 2 else 3,fun_aggregate=if (m$aggregation=="mean") mean else NULL,anova_table=list(correction=m$correction,es="pes")),warning=function(w) { warnings[[length(warnings)+1L]] <<- conditionMessage(w); invokeRestart("muffleWarning") })
  tab <- as.data.frame(fit$anova_table); required <- c("num Df","den Df","F","Pr(>F)"); if (!all(required %in% names(tab))) fail("BACKEND_ERROR", "Unexpected afex ANOVA table")
  decode <- function(x) decode_tokens(x,map)
  res <- lapply(seq_len(nrow(tab)),function(i) {
    vals <- unlist(tab[i,required]); if (any(!is.finite(vals))) fail("NONFINITE_ESTIMATE", "Nonfinite ANOVA output")
    r <- list(outcome_id=m$outcome,term_id=decode(rownames(tab)[i]),contrast_id="omnibus",kind="omnibus",statistic=unname(tab[i,"F"]),df_num=unname(tab[i,"num Df"]),df=unname(tab[i,"den Df"]),p=unname(tab[i,"Pr(>F)"]),n=n)
    if ("pes" %in% names(tab) && is.finite(tab[i,"pes"])) r$partial_eta_squared <- unname(tab[i,"pes"]); r
  })
  res <- c(res,extract_comparisons(fit,payload,map,n,m$outcome))
  audit <- z$audit; if (!is.null(id) && !length(within)) audit$n_subjects <- nlevels(d[[idcol]]); if(length(within)) { audit$n_subjects <- nlevels(d[[idcol]]); audit$model_rows <- length(unique(interaction(d[c(idcol,unname(map[within]))],drop=TRUE))) }
  list(status="COMPLETED",results=res,sample_audit=audit,diagnostics=list(warnings=warnings,converged=TRUE),backend_versions=list(R=as.character(getRversion()),jsonlite=as.character(utils::packageVersion("jsonlite")),afex=as.character(utils::packageVersion("afex")),emmeans=if(length(inf$comparisons)) as.character(utils::packageVersion("emmeans")) else NULL),model_summary=list(expected_result_ids=lapply(res,function(x) list(x$outcome_id,x$term_id,x$contrast_id)),ss_type=m$ss_type,correction=m$correction,aggregation=m$aggregation))
}
