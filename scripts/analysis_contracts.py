"""Pure scientific specification and result contracts; no file access."""
from __future__ import annotations
import hashlib
import itertools
import json
import math

INTENTS = ('METHOD_REVIEW', 'CANDIDATE_ANALYSIS', 'FORMAL_ANALYSIS', 'VERIFICATION')
PYTHON_METHODS = ('descriptive', 'scale_score', 'welch_t', 'student_t', 'paired_t', 'pearson')
R_METHODS = ('factorial_anova', 'repeated_anova', 'mixed_anova', 'linear_regression',
             'binomial_regression', 'poisson_regression', 'linear_mixed', 'binomial_mixed',
             'poisson_mixed', 'mediation', 'moderation', 'cfa', 'sem')
METHODS = PYTHON_METHODS + R_METHODS
MODEL_FIELDS = {
    'descriptive': ('columns',), 'scale_score': ('columns',),
    'welch_t': ('outcome', 'group', 'group_order'),
    'student_t': ('outcome', 'group', 'group_order'),
    'paired_t': ('x', 'y', 'subject_id'), 'pearson': ('x', 'y'),
}
for _method in R_METHODS:
    if _method.endswith('_anova'):
        MODEL_FIELDS[_method] = ('outcome','between','within','subject_id','ss_type','correction','aggregation','factors')
    elif _method in ('cfa','sem'):
        MODEL_FIELDS[_method] = ('latent','paths','residual_covariances','ordered','estimator','std_lv','fixed_x')
    elif _method == 'mediation':
        MODEL_FIELDS[_method] = ('outcome','exposure','mediators','covariates','mediator_covariances','estimator')
    else:
        MODEL_FIELDS[_method] = ('outcome','predictors','factors','interactions','intercept','center','standard_error')
        if _method.endswith('_mixed'): MODEL_FIELDS[_method] += ('random','estimation')
        if _method == 'moderation': MODEL_FIELDS[_method] += ('family',)
VARIABLE_ROLES = ('outcome','independent','dependent','predictor','group','factor','covariate',
                  'subject','subject_id','item','mediator','moderator','identifier','time','within','between')

def describe_method(method):
    """Small public field contract, sharing the validator's actual field lists."""
    if method not in METHODS:
        raise ValueError('method unsupported by controlled runner')
    if method in R_METHODS:
        details={
            'factors':'object mapping each factor to its ordered observed labels; first level is regression reference',
            'sample_missing':['error','complete_case'],
            'comparisons':'[{id,family_id,factor,levels:[first,second],by:{factor:level}}] or [{id,family_id,slope,at:{numeric_predictor:value}}]',
            'adjustments':'object mapping every comparison family_id to holm, bonferroni or none',
            'context_values':{'inferential_status':['PRESPECIFIED','EXPLORATORY','UNDETERMINED'],
                              'analysis_role':['PRIMARY','CANDIDATE','REPRODUCTION','SENSITIVITY','CORRECTION','UNDETERMINED']}}
        if method.endswith('_anova'):
            details.update(between='factor names',within='factor names',subject_id='mapped ID; null only for independent rows',
                           ss_type=['II','III'],correction=['none','GG','HF'],aggregation=['none','mean'])
        elif method in ('cfa','sem'):
            details.update(latent='{factor:[indicator names]}',paths='[{outcome,predictors:[]}] (empty for CFA)',
                           residual_covariances='pairs of variable names',ordered='{indicator:[ordered category labels]}',
                           estimator=['ML','MLR','WLSMV'],std_lv='boolean',fixed_x='boolean',
                           sample_missing=['error','complete_case','fiml (continuous ML/MLR only)'])
        elif method=='mediation':
            details.update(exposure='mapped X',mediators='mapped parallel continuous M names',covariates='mapped names',
                           mediator_covariances='boolean',estimator=['ML'],
                           bootstrap='{replicates:integer>=2,seed:integer,unit:observation,ci_type:percentile}')
        else:
            details.update(predictors='mapped names',covariates='optional mapped names',interactions='arrays of predictor names',
                           intercept='boolean',center='{numeric_predictor:explicit constant}',
                           standard_error=['conventional','HC3 (OLS only)'],trials='optional binomial successes denominator column',
                           offset='optional Poisson log-exposure column')
            if method=='moderation':details['family']=['linear','binomial','poisson']
            if method.endswith('_mixed'):
                details.update(random='[{group,slopes:[],correlated:boolean}]',estimation=['ML','REML (LMM only)'],
                               nested_test='optional inference field {predictors:[],interactions:[]}: strictly smaller fixed model, same rows/random effects, ML only')
        return {'status':'METHOD_CONTRACT','schema_version':3,'method':method,'backend':'R',
                'execution_ready':False,'required_model_fields':list(MODEL_FIELDS[method]),
                'variable_roles':list(VARIABLE_ROLES),
                'model_options': 'Structured variables/terms only; no executable formulas or automatic selection.',
                'inference': 'alpha, confidence_level, two-sided alternative; explicit comparison families; mediation bootstrap.',
                'analysis_context': 'inferential_status, analysis_role, basis_ref, search_set_id, parent_analysis_id; discovery after results is exploratory.',
                'options':details,
                'scope':'Capability contract, not dependency readiness, validation or authorization.'}
    info = {
        'status': 'METHOD_CONTRACT', 'schema_version': 2, 'method': method,
        'execution_ready': False, 'required_model_fields': list(MODEL_FIELDS[method]),
        'variable_roles': list(VARIABLE_ROLES),
        'field_mapping': 'Model fields use variable names; map each to its data column with evidence.',
        'optional_model_fields': {'covariates': 'Only [] supported; no covariate adjustment.'},
        'inference': {'alpha': '0 < value < 1', 'confidence_level': '0 < value < 1',
                      'alternative': ['two-sided', 'less', 'greater'], 'intervals': 'two-sided'},
        'sample': {'missing': ['complete_case', 'error'], 'filters': 'Explicit list; eq/in/not_in only.'},
        'scope': 'Field information only; not method recommendation, runtime readiness or authorization.',
    }
    if method in ('paired_t', 'pearson'):
        info['contrast'] = 'x - y' if method == 'paired_t' else 'Pearson association of x and y'
    if method == 'paired_t':
        info['structure'] = 'One paired row per unique subject_id; x/y mapped to numeric columns.'
    if method in ('welch_t', 'student_t'):
        info['group_order'] = 'Exactly two distinct observed labels; first minus second.'
    if method == 'scale_score':
        info['scoring'] = {'method': 'scale', 'items': 'Same ordered list as model.columns',
                           'reverse_items': 'Explicit subset of items', 'minimum': 'Scale lower bound',
                           'maximum': 'Scale upper bound', 'aggregation': ['mean','sum'],
                           'min_answered': 'Explicit integer from 1 through item count'}
    else:
        info['scoring'] = {'accepted_methods': ['none', 'scale'],
                           'execution': 'Uses mapped input values without re-scoring; scale scoring is performed only by scale_score.'}
    return info

def normalize_design_tags(tags):
    result = []
    for tag in tags if isinstance(tags, list) else []:
        if not isinstance(tag, str):
            continue
        for value in [tag] + ([x for x in ('within-subjects', 'between-subjects', 'factorial') if x.rstrip('s') in tag]):
            if value not in result:
                result.append(value)
    return result

def scientific_spec(spec):
    data = spec.get('data', {})
    return {'design': spec.get('design'),
            'data': {k: data[k] for k in ('sha256', 'format', 'read_options') if k in data},
            'field_map': [{k: row[k] for k in ('variable', 'column') if k in row} for row in spec.get('field_map', []) if isinstance(row, dict)],
            **{k: spec[k] for k in ('scoring', 'sample', 'model', 'inference') if k in spec}}

def spec_hash(spec):
    return hashlib.sha256(json.dumps(scientific_spec(spec), sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()

def _text(v):
    return isinstance(v, str) and bool(v.strip())

def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def analysis_context(spec):
    """Legacy records remain unknown; adoption never changes analysis timing."""
    supplied=spec.get('analysis_context')
    if isinstance(supplied,dict): return dict(supplied)
    return {'inferential_status':'UNDETERMINED','analysis_role':'UNDETERMINED',
            'basis_ref':'Legacy record; timing not recorded','search_set_id':None,
            'parent_analysis_id':None,'discovered_after_results':False}


def context_hash(context):
    return hashlib.sha256(json.dumps(context,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()


def validate_context(context):
    if not isinstance(context,dict): return [{'code':'INVALID_SPEC','field':'analysis_context','message':'analysis origin required'}]
    errors=[]
    def need(ok,key):
        if not ok: errors.append({'code':'INVALID_SPEC','field':'analysis_context.'+key,'message':'invalid or missing analysis origin'})
    need(not(set(context)-{'inferential_status','analysis_role','basis_ref','search_set_id','parent_analysis_id','discovered_after_results'}),'fields')
    need(context.get('inferential_status') in ('PRESPECIFIED','EXPLORATORY','UNDETERMINED'),'inferential_status')
    need(context.get('analysis_role') in ('PRIMARY','CANDIDATE','REPRODUCTION','SENSITIVITY','CORRECTION','UNDETERMINED'),'analysis_role')
    need(_text(context.get('basis_ref')),'basis_ref')
    for k in ('search_set_id','parent_analysis_id'): need(context.get(k) is None or _text(context.get(k)),k)
    need(type(context.get('discovered_after_results')) is bool,'discovered_after_results')
    if context.get('discovered_after_results'): need(context.get('inferential_status')=='EXPLORATORY','inferential_status')
    return errors


def validate_extended_model(m, inf, sample, names, need):
    method=m['method']; names=set(names)
    allowed=set(MODEL_FIELDS[method])|{'method'}
    if method.endswith(('_regression','_mixed')) or method=='moderation': allowed|={'covariates','trials','offset'}
    if method.endswith('_anova'): allowed|={'covariates'}
    need(not(set(m)-allowed),'model','unsupported model option')
    for k in MODEL_FIELDS[method]: need(k in m,'model.'+k)
    def variables(value,key,nonempty=False,universe=None):
        space=names if universe is None else universe
        ok=isinstance(value,list) and (not nonempty or bool(value)) and all(isinstance(x,str) and x in space for x in value)
        if ok: ok=len(value)==len(set(value))
        need(ok,key,'unique mapped variables required')
        return value if ok else []
    def variable(value,key): need(isinstance(value,str) and value in names,key,'mapped variable required')
    def levels(value,key):
        ok=isinstance(value,list) and len(value)>=2 and all(isinstance(x,(str,int,float)) and not isinstance(x,bool) and (not isinstance(x,(int,float)) or math.isfinite(x)) for x in value)
        if ok: ok=len({str(x) for x in value})==len(value)
        need(ok,key,'at least two unique ordered labels required')
    if 'outcome' in m: variable(m['outcome'],'model.outcome')
    if 'covariates' in m: variables(m['covariates'],'model.covariates')
    factors=m.get('factors',{})
    need(isinstance(factors,dict),'model.factors')
    if not isinstance(factors,dict): factors={}
    if isinstance(factors,dict):
        for key,value in factors.items(): variable(key,'model.factors');levels(value,'model.factors.'+key)
    if method.endswith('_anova'):
        between=variables(m.get('between'),'model.between');within=variables(m.get('within'),'model.within')
        need(bool(between+within) and not(set(between)&set(within)),'model','distinct nonempty factors required')
        if within or m.get('subject_id') is not None:variable(m.get('subject_id'),'model.subject_id')
        if m.get('subject_id') is not None:need(m['subject_id'] not in between+within+[m.get('outcome')],'model.subject_id','ID must differ from outcome and factors')
        need(m.get('ss_type') in ('II','III'),'model.ss_type')
        need(m.get('correction') in ('none','GG','HF'),'model.correction')
        need(m.get('aggregation') in ('none','mean'),'model.aggregation')
        need(m.get('covariates',[])==[],'model.covariates','use linear regression for ANCOVA')
        need(isinstance(factors,dict) and set(factors)==set(between+within),'model.factors','levels must cover design factors exactly')
        need((method!='factorial_anova' or (bool(between) and not within)) and
             (method!='repeated_anova' or (bool(within) and not between)) and
             (method!='mixed_anova' or (bool(between) and bool(within))),'model','method must match within/between design')
    elif method in ('cfa','sem'):
        latent=m.get('latent');need(isinstance(latent,dict) and bool(latent),'model.latent')
        latent=latent if isinstance(latent,dict) else {}
        for name,indicators in latent.items():
            need(_text(name) and name not in names,'model.latent','latent names must differ from observed variables')
            variables(indicators,'model.latent.'+name,True)
        allnames=names|set(latent)
        paths=m.get('paths');need(isinstance(paths,list),'model.paths')
        graph={}
        for p in paths if isinstance(paths,list) else []:
            if not isinstance(p,dict):need(False,'model.paths');continue
            need(set(p)=={'outcome','predictors'} and p.get('outcome') in allnames,'model.paths')
            x=variables(p.get('predictors'),'model.paths.predictors',True,allnames)
            need(p.get('outcome') not in x,'model.paths','self path not allowed')
            if p.get('outcome') in graph:need(False,'model.paths','combine predictors into one path per outcome')
            graph[p.get('outcome')]=x
        def cyclic(n,trail): return n in trail or any(cyclic(v,trail|{n}) for v in graph.get(n,[]))
        need(not any(cyclic(n,set()) for n in graph),'model.paths','recursive paths only')
        if method=='cfa':need(paths==[],'model.paths','CFA has no structural paths')
        cov=m.get('residual_covariances');need(isinstance(cov,list),'model.residual_covariances')
        for pair in cov if isinstance(cov,list) else []: variables(pair,'model.residual_covariances',True,allnames);need(isinstance(pair,list) and len(pair)==2,'model.residual_covariances')
        ordered=m.get('ordered');need(isinstance(ordered,dict),'model.ordered')
        for key,value in ordered.items() if isinstance(ordered,dict) else []: variable(key,'model.ordered');levels(value,'model.ordered.'+key)
        need(m.get('estimator') in ('ML','MLR','WLSMV'),'model.estimator')
        need(bool(ordered)==(m.get('estimator')=='WLSMV'),'model.ordered','WLSMV requires ordinal indicators; ML/MLR require continuous')
        need(sample.get('missing')!='fiml' or m.get('estimator') in ('ML','MLR'),'sample.missing','ordinal FIML is not supported')
        for k in ('std_lv','fixed_x'):need(type(m.get(k)) is bool,'model.'+k)
    elif method=='mediation':
        variable(m.get('exposure'),'model.exposure')
        mediators=variables(m.get('mediators'),'model.mediators',True)
        need(len(set(mediators+[m.get('exposure'),m.get('outcome')]))==len(mediators)+2,'model','X, M and Y must differ')
        need(m.get('estimator')=='ML','model.estimator')
        need(type(m.get('mediator_covariances')) is bool,'model.mediator_covariances')
        b=inf.get('bootstrap');need(isinstance(b,dict),'inference.bootstrap')
        if isinstance(b,dict):
            need(set(b)=={'replicates','seed','unit','ci_type'},'inference.bootstrap')
            need(type(b.get('replicates')) is int and b['replicates']>=2,'inference.bootstrap.replicates')
            need(type(b.get('seed')) is int and 0<=b['seed']<=2147483647,'inference.bootstrap.seed')
            need(b.get('unit')=='observation' and b.get('ci_type')=='percentile','inference.bootstrap','independent-observation percentile bootstrap only')
    else:
        predictors=variables(m.get('predictors'),'model.predictors')
        covariates=variables(m.get('covariates',[]),'model.covariates')
        universe=set(predictors+covariates)
        need(m.get('outcome') not in universe,'model.outcome','outcome must not predict itself')
        need(set(factors).issubset(universe) if isinstance(factors,dict) else False,'model.factors')
        interactions=m.get('interactions');need(isinstance(interactions,list),'model.interactions')
        for pair in interactions if isinstance(interactions,list) else []:
            variables(pair,'model.interactions',True,universe);need(isinstance(pair,list) and len(pair)>=2,'model.interactions')
        need(type(m.get('intercept')) is bool,'model.intercept')
        center=m.get('center');need(isinstance(center,dict),'model.center')
        if isinstance(center,dict):
            for k,v in center.items():need(k in universe and k not in factors and _number(v),'model.center','explicit numeric centers for continuous predictors')
        need(m.get('standard_error') in ('conventional','HC3'),'model.standard_error')
        linear=method=='linear_regression' or (method=='moderation' and m.get('family')=='linear')
        if not linear:need(m.get('standard_error')=='conventional','model.standard_error','HC3 only implemented for OLS')
        if method=='moderation': need(m.get('family') in ('linear','binomial','poisson'),'model.family');need(bool(interactions),'model.interactions','moderation requires interaction')
        if 'trials' in m:
            variable(m['trials'],'model.trials');need(method.startswith('binomial') or (method=='moderation' and m.get('family')=='binomial'),'model.trials')
        if 'offset' in m:
            variable(m['offset'],'model.offset');need(method.startswith('poisson') or (method=='moderation' and m.get('family')=='poisson'),'model.offset')
        if method.endswith('_mixed'):
            random=m.get('random');need(isinstance(random,list) and bool(random),'model.random')
            for r in random if isinstance(random,list) else []:
                if not isinstance(r,dict):need(False,'model.random');continue
                need(set(r)=={'group','slopes','correlated'},'model.random')
                variable(r.get('group'),'model.random.group');variables(r.get('slopes'),'model.random.slopes',False,universe)
                need(type(r.get('correlated')) is bool,'model.random.correlated')
            need(m.get('estimation') in (('ML','REML') if method=='linear_mixed' else ('ML',)),'model.estimation')
    if method not in ('cfa','sem'):need(sample.get('missing')!='fiml','sample.missing')
    if method!='mediation':need('bootstrap' not in inf,'inference.bootstrap','bootstrap only implemented for mediation')
    if 'nested_test' in inf:
        reduced=inf['nested_test']
        need(method.endswith('_mixed') and m.get('estimation')=='ML','inference.nested_test','nested fixed-effect tests require ML mixed models')
        need(isinstance(reduced,dict) and set(reduced)=={'predictors','interactions'},'inference.nested_test')
        if isinstance(reduced,dict):
            full_vars=set(m.get('predictors',[])+m.get('covariates',[]))
            reduced_vars=variables(reduced.get('predictors'),'inference.nested_test.predictors',False,full_vars)
            reduced_terms=reduced.get('interactions');need(isinstance(reduced_terms,list),'inference.nested_test.interactions')
            full_terms={frozenset(v) for v in m.get('interactions',[]) if isinstance(v,list) and all(isinstance(x,str) for x in v)}
            valid_terms=set()
            for term in reduced_terms if isinstance(reduced_terms,list) else []:
                v=variables(term,'inference.nested_test.interactions',True,set(reduced_vars))
                need(len(v)>=2 and frozenset(v) in full_terms,'inference.nested_test.interactions','only existing hierarchical terms may be retained')
                valid_terms.add(frozenset(v))
            need(set(reduced_vars)!=full_vars or valid_terms!=full_terms,'inference.nested_test','reduced model must be strictly smaller')
    need(inf.get('alternative')=='two-sided','inference.alternative','extended methods currently implement two-sided inference')
    comparisons=inf.get('comparisons',[]); adjustments=inf.get('adjustments',{})
    need(isinstance(comparisons,list) and isinstance(adjustments,dict),'inference.comparisons')
    ids=[];families=set()
    for c in comparisons if isinstance(comparisons,list) else []:
        if not isinstance(c,dict):need(False,'inference.comparisons');continue
        need(_text(c.get('id')) and _text(c.get('family_id')),'inference.comparisons')
        if _text(c.get('id')):ids.append(c['id'])
        if _text(c.get('family_id')):families.add(c['family_id'])
        if 'slope' in c:
            need(set(c)=={'id','family_id','slope','at'},'inference.comparisons')
            variable(c['slope'],'inference.comparisons.slope')
            need(isinstance(c.get('at'),dict) and all(k in names and _number(v) for k,v in c.get('at',{}).items()),'inference.comparisons.at')
        else:
            need(set(c)=={'id','family_id','factor','levels','by'},'inference.comparisons')
            factor=c.get('factor'); lv=c.get('levels')
            need(isinstance(factor,str) and factor in factors,'inference.comparisons.factor')
            need(isinstance(lv,list) and len(lv)==2 and lv[0]!=lv[1] and all(v in factors.get(factor,[]) for v in lv),'inference.comparisons.levels')
            by=c.get('by');need(isinstance(by,dict) and all(k in factors and v in factors[k] for k,v in by.items()),'inference.comparisons.by')
    need(len(ids)==len(set(ids)),'inference.comparisons','contrast IDs must be unique')
    if isinstance(adjustments,dict):need(set(adjustments)==families and all(v in ('holm','bonferroni','none') for v in adjustments.values()),'inference.adjustments','explicit adjustment for every requested family')
    if method in ('mediation','cfa','sem'):need(not comparisons,'inference.comparisons','use specified paths rather than marginal comparisons')


def validate_extended_result(run,fail):
    """Typed outputs, explicit missing statistics, and exact emitted inventory."""
    if run.get('schema_version')!=2:fail('schema_version','extended runs require v2')
    audit=run.get('sample_audit',{}); rows=run['results']; summary=run.get('model_summary',{})
    model=run['scientific_spec']['model'];method=model['method']
    if not isinstance(summary,dict):fail('model_summary','model summary object required');return
    if not isinstance(run.get('diagnostics'),dict):fail('diagnostics','diagnostic object required');return
    if any(not isinstance(row,dict) or not all(_text(row.get(k)) for k in ('outcome_id','term_id','contrast_id')) for row in rows):fail('results','typed result identities required');return
    n=audit.get('effective_n') if isinstance(audit,dict) else None
    if type(n) is not int or n<1:fail('sample_audit.effective_n','positive sample size required')
    if 'n' in run['scientific_spec']['sample'] and run['scientific_spec']['sample']['n']!=n:fail('sample_audit.effective_n','declared observation count differs from analyzed rows')
    if run.get('diagnostics',{}).get('converged') is not True:fail('diagnostics.converged','converged result required')
    if run.get('diagnostics',{}).get('admissible',True) is not True:fail('diagnostics.admissible','inadmissible result')
    actual=[]
    for i,row in enumerate(rows):
        if not isinstance(row,dict):fail('results','row object required');continue
        identity=[row.get(k) for k in ('outcome_id','term_id','contrast_id')]
        if not all(_text(v) for v in identity):fail('results.identity','nonempty row identity required')
        actual.append(identity)
        if row.get('kind') not in ('coefficient','omnibus','contrast','loading','variance','indirect','fit'):fail('results.kind','unknown row kind')
        kind=row.get('kind');required=[]
        if kind=='omnibus':required=['statistic','df_num','df','p']
        if method.endswith('_anova') and kind=='omnibus':required+=['partial_eta_squared']
        if kind=='coefficient' and method not in ('mediation','cfa','sem'):
            required=['estimate','se','statistic','p','ci']
            if method in ('linear_regression','linear_mixed') or (method=='moderation' and model['family']=='linear'):required+=['df']
        if kind=='contrast':required=['estimate','se','p','ci','p_adjusted']
        if method=='mediation' and kind in ('indirect','coefficient'):required=['estimate','se','ci']
        if method in ('cfa','sem'):
            if type(row.get('free')) is not bool:fail('results.free','SEM parameter freedom must be explicit')
            if row.get('free') is True:required=['estimate','se','p','ci']
        for k in required:
            if k not in row:fail('results.'+k,'required for this model and row kind')
        if row.get('n')!=n or type(row.get('n')) is not int:fail('results.n','sample count mismatch')
        if not any(_number(row.get(k)) for k in ('estimate','statistic')):fail('results','estimate or statistic required')
        for k in ('estimate','standardized_estimate','partial_eta_squared','se','df','df_num','statistic','p','p_adjusted'):
            if k in row and (not _number(row[k]) or (k in ('p','p_adjusted') and not 0<=row[k]<=1) or (k in ('df','df_num','se') and row[k]<0)):fail('results.'+k,'invalid finite statistic')
        if 'ci' in row:
            ci=row['ci']
            if not isinstance(ci,list) or len(ci)!=2 or not all(_number(v) for v in ci) or ci[0]>ci[1]:fail('results.ci','finite ordered interval required')
            if row.get('confidence_level')!=run['scientific_spec']['inference']['confidence_level'] or row.get('ci_alternative')!='two-sided':fail('results.ci','explicit confidence settings required')
    expected=summary.get('expected_result_ids') if isinstance(summary,dict) else None
    if not isinstance(expected,list) or not expected or expected!=actual or len({json.dumps(x) for x in actual})!=len(actual):fail('model_summary.expected_result_ids','complete unique ordered result inventory required')
    for c in run['scientific_spec']['inference'].get('comparisons',[]):
        matched=[r for r in rows if r.get('contrast_id')==c['id'] and r.get('kind')=='contrast']
        if len(matched)!=1 or 'p_adjusted' not in matched[0]:fail('results.comparisons','missing requested corrected comparison')
    terms={r.get('term_id') for r in rows if isinstance(r,dict)}
    if method.endswith('_anova'):
        factors=model['between']+model['within']
        expected={frozenset(c) for k in range(1,len(factors)+1) for c in itertools.combinations(factors,k)}
        observed={frozenset(r['term_id'].split(':')) for r in rows if r.get('kind')=='omnibus'}
        if observed!=expected:fail('results.omnibus','must cover all design terms')
    elif method.endswith(('_regression','_mixed')) or method=='moderation':
        factors=model['factors']
        predictors=list(dict.fromkeys(model['predictors']+model.get('covariates',[])))
        first_factor=next((v for v in predictors if v in factors),None) if not model['intercept'] else None
        def codes(v,main=False):return [v+str(level) for level in factors[v][0 if main and v==first_factor else 1:]] if v in factors else [v]
        expected={'(Intercept)'} if model['intercept'] else set()
        for v in predictors: expected.update(codes(v,main=True))
        for interaction in model['interactions']:
            expected.update(':'.join(c) for c in itertools.product(*(codes(v) for v in interaction)))
        observed={r['term_id'] for r in rows if r.get('kind')=='coefficient'}
        # Formula engines may reorder the components of an interaction.
        norm=lambda seq:{tuple(sorted(t.split(':'))) for t in seq}
        if norm(observed)!=norm(expected):fail('results.coefficients','must cover requested intercept, coded predictors and interactions')
        if method.endswith('_mixed'):
            for random in model['random']:
                if not any(r.get('kind')=='variance' and r['term_id'].startswith('random:'+random['group']+':') for r in rows):fail('results.variance','random structure variance missing')
            if not _number(summary.get('log_likelihood')):fail('model_summary.log_likelihood','likelihood required')
            if 'nested_test' in run['scientific_spec']['inference']:
                lrt=[r for r in rows if r.get('contrast_id')=='likelihood_ratio' and r.get('term_id')=='nested_model']
                if len(lrt)!=1 or any(not _number(lrt[0].get(k)) for k in ('statistic','df_num','p')):fail('results.nested_test','complete likelihood-ratio result required')
    elif method=='mediation':
        expected={model['outcome']+'~'+model['exposure'],'total','total_indirect'}
        for i,mediator in enumerate(model['mediators'],1):expected|={mediator+'~'+model['exposure'],model['outcome']+'~'+mediator,'indirect'+str(i)}
        for v in model['covariates']:
            expected.add(model['outcome']+'~'+v)
            for mediator in model['mediators']:expected.add(mediator+'~'+v)
        if not expected.issubset(terms):fail('results.paths','missing requested mediation paths/effects')
        boot=run['scientific_spec']['inference']['bootstrap']
        for key in ('replicates','seed','unit','ci_type'):
            if summary.get('bootstrap_'+key)!=boot[key]:fail('model_summary.bootstrap_'+key,'bootstrap settings mismatch')
        if type(run['diagnostics'].get('bootstrap_failed')) is not int:fail('diagnostics.bootstrap_failed','bootstrap failures required')
    elif method in ('cfa','sem'):
        expected={factor+'=~'+item for factor,items in model['latent'].items() for item in items}
        expected|={p['outcome']+'~'+v for p in model['paths'] for v in p['predictors']}
        if not expected.issubset(terms):fail('results.paths','missing requested loadings or structural paths')
        measures=summary.get('fit_measures',{})
        if not isinstance(measures,dict) or any(not _number(measures.get(k)) for k in ('chisq','df','srmr')):fail('model_summary.fit_measures','model test and residual fit required')
    provenance=run.get('execution_provenance',{})
    if provenance.get('software')!='R' or not _text(provenance.get('version')):fail('execution_provenance','actual R runtime version required')

def validate_spec(spec, for_execution=False, *, _scientific_only=False):
    errors=[]
    def need(ok, field, message='required or invalid', code='INVALID_SPEC'):
        if not ok: errors.append({'code':code, 'field':field, 'message':message})
    if not isinstance(spec, dict):
        return [{'code':'INVALID_SPEC','field':'spec','message':'must be an object'}]
    intent=spec.get('intent')
    if not _scientific_only:
        need(spec.get('schema_version') in (2,3), 'schema_version')
        need(_text(spec.get('analysis_id')), 'analysis_id')
        need(type(spec.get('revision')) is int and spec['revision'] > 0, 'revision')
        need(intent in INTENTS, 'intent')
    if intent == 'METHOD_REVIEW' and not _scientific_only: return errors
    if not _scientific_only and spec.get('schema_version') == 3:
        errors.extend(validate_context(spec.get('analysis_context')))
    design=spec.get('design', {})
    if not isinstance(design, dict): design={}
    for key in ('design_tags','observation_unit','research_question_type','variables'):
        need(bool(design.get(key)), 'design.'+key)
    need(isinstance(design.get('design_tags'),list) and all(_text(t) for t in design.get('design_tags',[])), 'design.design_tags')
    variables=design.get('variables', [])
    need(isinstance(variables,list) and all(isinstance(v,dict) and _text(v.get('name')) and _text(v.get('role')) for v in variables), 'design.variables')
    for variable in variables if isinstance(variables,list) else []:
        if isinstance(variable,dict): need(variable.get('role') in VARIABLE_ROLES, 'design.variables.role')
    data=spec.get('data', {}); data=data if isinstance(data,dict) else {}
    if not _scientific_only: need(_text(data.get('path')), 'data.path')
    digest=data.get('sha256',''); need(isinstance(digest,str) and len(digest)==64 and all(c in '0123456789abcdefABCDEF' for c in digest), 'data.sha256')
    need(data.get('format') in ('csv','xlsx'), 'data.format')
    opts=data.get('read_options'); need(isinstance(opts,dict), 'data.read_options')
    if isinstance(opts,dict):
        allowed={'encoding','delimiter','missing_values'} if data.get('format')=='csv' else {'sheet_name','formula_policy','missing_values'}
        need(not(set(opts)-allowed),'data.read_options','unsupported reading option')
        if data.get('format')=='csv':
            need(_text(opts.get('encoding')), 'data.read_options.encoding')
            need(isinstance(opts.get('delimiter'),str) and len(opts['delimiter'])==1, 'data.read_options.delimiter')
        elif data.get('format')=='xlsx': need(_text(opts.get('sheet_name')) or type(opts.get('sheet_name')) is int, 'data.read_options.sheet_name')
    fields=spec.get('field_map',[]); need(isinstance(fields,list) and bool(fields), 'field_map')
    fields=fields if isinstance(fields,list) else []
    names=[]
    for i,row in enumerate(fields):
        if not isinstance(row,dict): need(False,f'field_map.{i}'); continue
        names.append(row.get('variable') if isinstance(row.get('variable'),str) else None)
        for key in ('variable','column'): need(_text(row.get(key)),f'field_map.{i}.{key}')
        if not _scientific_only:
            need(_text(row.get('evidence_ref')),f'field_map.{i}.evidence_ref')
            need(row.get('confirmation_status') in ('USER_CONFIRMED','DOCUMENTED','CANDIDATE_INFERRED'),f'field_map.{i}.confirmation_status')
    need(len(names)==len(set(names)), 'field_map', 'duplicate variable mapping')
    for v in variables if isinstance(variables,list) else []:
        if isinstance(v,dict): need(v.get('name') in names, 'field_map', 'each design variable needs an evidenced column')
    for key in ('scoring','sample','model','inference') + (() if _scientific_only else ('authorization',)):
        need(isinstance(spec.get(key),dict),key)
    scoring, sample, model, inference, auth = [spec[k] if isinstance(spec.get(k),dict) else {} for k in ('scoring','sample','model','inference','authorization')]
    need(scoring.get('method') in ('none','scale'), 'scoring.method')
    need(sample.get('missing') in ('complete_case','error','fiml'), 'sample.missing')
    need(isinstance(sample.get('filters'),list), 'sample.filters')
    for rule in sample.get('filters',[]) if isinstance(sample.get('filters'),list) else []:
        if not isinstance(rule,dict): need(False,'sample.filters','filter object required'); continue
        op=rule.get('op')
        expected={'op','value' if op=='eq' else 'values','variable' if 'variable' in rule else 'column'}
        need(set(rule)==expected and op in ('eq','in','not_in'),'sample.filters','unsupported or conflicting filter fields')
        name=rule.get('variable',rule.get('column'))
        need(_text(name),'sample.filters','filter variable or column required')
        if op in ('in','not_in'): need(isinstance(rule.get('values'),list),'sample.filters.values')
        values=[rule.get('value')] if op=='eq' else rule.get('values',[])
        if isinstance(values,list): need(all(isinstance(v,(str,int,float)) and not isinstance(v,bool) and (not isinstance(v,(int,float)) or math.isfinite(v)) for v in values),'sample.filters','scalar filter values required')
    method=model.get('method'); method=method if isinstance(method,str) else ''; need(method in METHODS, 'model.method', 'method unsupported by controlled runner')
    extended = method in R_METHODS
    if extended:
        if not _scientific_only: need(spec.get('schema_version')==3,'schema_version','extended methods require v3')
        validate_extended_model(model,inference,sample,names,need)
    required=() if extended else MODEL_FIELDS.get(method,())
    if not extended:
        need(not(set(model)-set(required)-{'method','covariates'}),'model','unsupported model option')
        if 'covariates' in model: need(model['covariates']==[],'model.covariates','these methods do not adjust covariates')
        need(sample.get('missing')!='fiml','sample.missing','FIML only for supported continuous SEM')
    need(not(set(sample)-{'missing','filters','n'}),'sample','unsupported sampling option')
    if 'n' in sample: need(type(sample['n']) is int and sample['n']>0,'sample.n','positive integer required')
    allowed_inference={'alpha','confidence_level','alternative'} | ({'comparisons','adjustments','bootstrap','nested_test'} if extended else set())
    need(not(set(inference)-allowed_inference),'inference','unsupported inference option')
    allowed_scoring={'method'} if scoring.get('method')=='none' else {'method','items','reverse_items','minimum','maximum','aggregation','min_answered'}
    if extended: need(scoring.get('method')=='none','scoring.method','score separately before model fitting')
    need(not(set(scoring)-allowed_scoring),'scoring','unsupported scoring option')
    for key in required:
        value=model.get(key); need(bool(value), 'model.'+key)
        if key=='columns': need(isinstance(value,list) and bool(value), 'model.columns')
        elif key!='group_order': need(_text(value), 'model.'+key)
        if key=='group_order': need(isinstance(value,list) and len(value)==2 and value[0]!=value[1], 'model.group_order')
        else:
            for name in value if isinstance(value,list) else [value]: need(name in names, 'model.'+key, 'model variable must have an evidenced mapping')
    if method == 'scale_score':
        need(scoring.get('method') == 'scale' and scoring.get('items') == model.get('columns'), 'scoring', 'scale items must equal model columns')
    for key in ('alpha','confidence_level'): need(_number(inference.get(key)) and 0<inference[key]<1, 'inference.'+key)
    need(inference.get('alternative') in ('two-sided','less','greater'), 'inference.alternative')
    if _scientific_only: return errors
    for key in ('data_read','compute'): need(auth.get(key) is True, 'authorization.'+key, 'explicit scope authorization required')
    for key in ('output_dir','reference'): need(_text(auth.get(key)), 'authorization.'+key)
    sources=spec.get('sources',[]); need(isinstance(sources,list),'sources')
    sources=sources if isinstance(sources,list) else []
    source_ids=[]
    for i,s in enumerate(sources):
        need(isinstance(s,dict) and all(_text(s.get(k)) for k in ('source_id','role','software')), f'sources.{i}')
        if isinstance(s,dict):
            need(s.get('role') in ('AUTHORITATIVE','VERIFICATION','DATA_ONLY','CANDIDATE','DERIVED'), f'sources.{i}.role')
            if _text(s.get('source_id')): source_ids.append(s['source_id'])
    need(len(source_ids)==len(set(source_ids)), 'sources', 'duplicate source IDs')
    if intent in ('FORMAL_ANALYSIS','VERIFICATION'):
        need(sum(isinstance(s,dict) and s.get('role')=='AUTHORITATIVE' for s in sources)==1,'sources','exactly one authoritative source required')
        need(sum(isinstance(s,dict) and s.get('role')=='VERIFICATION' for s in sources)<=1,'sources','at most one verification source')
        try: confirmed=auth.get('formal_spec_hash')==spec_hash(spec)
        except (ValueError,TypeError): confirmed=False
        need(confirmed,'authorization.formal_spec_hash','author must confirm this scientific specification')
    return errors

def validate_result(run):
    errors=[]
    def fail(field,message): errors.append({'code':'INVALID_RESULT','field':field,'message':message})
    if not isinstance(run,dict): return [{'code':'INVALID_RESULT','field':'run','message':'must be an object'}]
    for key in ('analysis_id','run_id','spec_hash','input_hash'):
        if not _text(run.get(key)): fail(key,'nonempty identity required')
    if run.get('schema_version') not in (1,2): fail('schema_version','must be 1 or 2')
    if run.get('schema_version')==2:
        if validate_context(run.get('analysis_context')): fail('analysis_context','invalid analysis origin')
        if run.get('context_hash')!=context_hash(run.get('analysis_context')): fail('context_hash','analysis origin changed')
    if type(run.get('revision')) is not int or run['revision']<1: fail('revision','positive integer required')
    if run.get('intent') not in INTENTS[1:]: fail('intent','computational intent required')
    if run.get('status')!='COMPLETED' or run.get('result_complete') is not True: fail('status','complete run required')
    if run.get('adoption_status')!='CANDIDATE': fail('adoption_status','computation never adopts findings')
    for key in ('scientific_spec','sample_audit','execution_provenance','artifact_refs'):
        if not run.get(key): fail(key,'nonempty record required')
    scientific=run.get('scientific_spec')
    if not isinstance(scientific,dict):
        fail('scientific_spec','scientific specification object required')
        return errors
    scientific_errors=validate_spec(scientific,_scientific_only=True)
    if scientific_errors:
        fail('scientific_spec','invalid scientific specification: '+json.dumps(scientific_errors))
        return errors
    if isinstance(scientific,dict):
        try:
            expected=hashlib.sha256(json.dumps(scientific,sort_keys=True,separators=(',', ':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
        except (ValueError,TypeError): expected=None
        if run.get('spec_hash') != expected: fail('spec_hash','scientific specification hash mismatch')
        data=scientific.get('data')
        if not isinstance(data,dict) or run.get('input_hash') != data.get('sha256'): fail('input_hash','input content hash mismatch')
    for key in ('spec_hash','input_hash'):
        digest=run.get(key)
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest): fail(key,'SHA256 required')
    rows=run.get('results')
    if not isinstance(rows,list) or not rows: fail('results','nonempty results required'); return errors
    model=scientific['model']; method=model['method']
    if run.get('method_id')!=method: fail('method_id','run method must match scientific specification')
    if method in R_METHODS:
        validate_extended_result(run,fail)
        return errors
    if method=='descriptive': expected={(v,'mean','overall') for v in model['columns']}
    elif method=='scale_score': expected={('score','mean','overall')}
    elif method in ('welch_t','student_t'): expected={(model['outcome'],'group',str(model['group_order'][0])+' - '+str(model['group_order'][1]))}
    elif method=='paired_t': expected={(model['x'],'paired_difference',model['x']+' - '+model['y'])}
    else: expected={(model['x'],'correlation',model['x']+' ~ '+model['y'])}
    actual=[tuple(row.get(k) for k in ('outcome_id','term_id','contrast_id')) for row in rows if isinstance(row,dict)]
    try:
        if len(actual)!=len(rows) or len(set(actual))!=len(rows) or set(actual)!=expected: fail('results','results must exactly cover requested identities')
    except TypeError: fail('results','invalid result identity type')
    audit=run.get('sample_audit')
    if not isinstance(audit,dict): fail('sample_audit','sample audit object required')
    for i,row in enumerate(rows):
        if not isinstance(row,dict): fail(f'results.{i}','object required'); continue
        for key in ('outcome_id','term_id','contrast_id'):
            if not _text(row.get(key)): fail(f'results.{i}.{key}','identity required')
        model = scientific.get('model', {}) if isinstance(scientific,dict) else {}
        method = model.get('method') if isinstance(model,dict) else None
        required = ['estimate','n']
        if method in ('descriptive','scale_score'): required += ['sd','se','df','ci']
        if method in ('welch_t','student_t','paired_t','pearson'): required += ['df','statistic','p','ci','statistic_name']
        if method in ('welch_t','student_t','paired_t'): required += ['se']
        if method in ('welch_t','student_t'): required += ['n_by_group']
        for key in required:
            if key not in row: fail(f'results.{i}.{key}','required for method')
        if 'n' in row and (type(row['n']) is not int or row['n']<1): fail(f'results.{i}.n','positive sample size required')
        if isinstance(audit,dict) and row.get('n')!=audit.get('effective_n'): fail(f'results.{i}.n','sample audit does not match result')
        if 'n' in scientific['sample'] and row.get('n')!=scientific['sample']['n']: fail(f'results.{i}.n','declared sample size does not match effective sample')
        if 'df' in row and _number(row['df']) and row['df']<=0: fail(f'results.{i}.df','positive degrees of freedom required')
        if method in ('descriptive','scale_score'):
            if type(row.get('n')) is not int or row['n']<2 or row.get('df')!=row['n']-1: fail(f'results.{i}.df','summary interval requires n>=2 and df=n-1')
        if method in ('welch_t','student_t'):
            counts=row.get('n_by_group')
            if not isinstance(counts,list) or len(counts)!=2 or any(type(v) is not int or v<1 for v in counts) or sum(counts)!=row.get('n'): fail(f'results.{i}.n_by_group','two positive integer group counts summing to n required')
        if method in ('welch_t','student_t','paired_t','pearson') and 'test_alternative' in row and row['test_alternative']!=scientific['inference']['alternative']: fail(f'results.{i}.test_alternative','test direction must match scientific specification')
        if method in ('welch_t','student_t','paired_t') and row.get('statistic_name')!='t': fail(f'results.{i}.statistic_name','t statistic required')
        if method=='pearson':
            if row.get('statistic_name')!='r': fail(f'results.{i}.statistic_name','r statistic required')
            if not _number(row.get('estimate')) or not -1<=row['estimate']<=1 or row.get('statistic')!=row.get('estimate'): fail(f'results.{i}.estimate','correlation must be between -1 and 1')
            if type(row.get('n')) is not int or row['n']<4 or row.get('df')!=row['n']-2: fail(f'results.{i}.df','Pearson interval requires n>=4 and df=n-2')
            if isinstance(row.get('ci'),list) and any(not _number(v) or not -1<=v<=1 for v in row['ci']): fail(f'results.{i}.ci','correlation interval out of range')
        if 'ci' in row and (row.get('confidence_level')!=scientific['inference']['confidence_level'] or row.get('ci_alternative')!='two-sided'): fail(f'results.{i}.ci','confidence level and interval direction must be explicit')
        if 'se' in row and _number(row['se']) and row['se']<0: fail(f'results.{i}.se','nonnegative standard error required')
        if 'sd' in row and _number(row['sd']) and row['sd']<0: fail(f'results.{i}.sd','nonnegative standard deviation required')
        if not any(_number(row.get(k)) for k in ('estimate','statistic')): fail(f'results.{i}','numeric estimate or statistic required')
        for key in ('estimate','sd','se','df','statistic','p','n'):
            if key in row and (not _number(row[key]) or (key=='p' and not 0<=row[key]<=1)):
                fail(f'results.{i}.{key}','finite valid number required')
        if 'ci' in row and (not isinstance(row['ci'],list) or len(row['ci'])!=2 or not all(_number(v) for v in row['ci']) or row['ci'][0]>row['ci'][1]): fail(f'results.{i}.ci','ordered finite interval required')
    return errors
